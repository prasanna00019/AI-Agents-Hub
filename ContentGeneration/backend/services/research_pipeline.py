"""
ContentPilot research pipeline.
"""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence
from urllib.parse import urlparse

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
URL_PATTERN = re.compile(r"https?://[^\s<>()\"\\']+")

LogCallback = Callable[[str, str], Awaitable[None]]


def normalize_url(value: str) -> str:
    return value.strip().rstrip("/.,);]")


def is_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_urls(value: str) -> List[str]:
    seen: set[str] = set()
    urls: List[str] = []
    for match in URL_PATTERN.findall(value or ""):
        normalized = normalize_url(match)
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    return urls


def _dedupe_strings(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        normalized = normalize_url(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _text_without_urls(value: str) -> str:
    return " ".join(URL_PATTERN.sub(" ", value or "").split()).strip()


def _smart_truncate(text: str, max_len: int = 18000) -> str:
    if len(text) <= max_len:
        return text
    cut_point = text.rfind("\n\n", 0, max_len)
    if cut_point < max_len * 0.5:
        cut_point = text.rfind("\n", 0, max_len)
    if cut_point < max_len * 0.5:
        cut_point = max_len
    return text[:cut_point].rstrip()


def _document_payload(
    *,
    title: str,
    content: str,
    url: str = "",
    kind: str,
    label: str = "",
    date_published: str = "",
    author: str = "",
    sitename: str = "",
) -> Dict[str, Any]:
    return {
        "title": title.strip() or label.strip() or url or kind.replace("_", " ").title(),
        "content": content.strip(),
        "url": normalize_url(url) if url else "",
        "kind": kind,
        "label": label.strip(),
        "date_published": date_published,
        "author": author,
        "sitename": sitename,
    }


def _format_document_for_context(document: Dict[str, Any]) -> str:
    header_bits = [document.get("title", "").strip()]
    if document.get("url"):
        header_bits.append(f"URL: {document['url']}")
    if document.get("date_published"):
        header_bits.append(f"Published: {document['date_published']}")
    if document.get("author"):
        header_bits.append(f"Author: {document['author']}")
    header = "\n".join(bit for bit in header_bits if bit)
    return f"{header}\n{document.get('content', '').strip()}".strip()


async def scrape_url(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        raw_html = response.text

        import trafilatura

        content = trafilatura.extract(
            raw_html,
            include_comments=False,
            include_tables=True,
            include_links=True,
            output_format="txt",
        )
        metadata = trafilatura.extract_metadata(raw_html)

        title = metadata.title if metadata and metadata.title else urlparse(str(response.url)).netloc
        date_published = str(metadata.date) if metadata and metadata.date else ""
        author = metadata.author if metadata and metadata.author else ""
        sitename = metadata.sitename if metadata and metadata.sitename else ""

        if not content:
            raise ValueError("No readable content found on the page.")

        return {
            "ok": True,
            "url": normalize_url(str(response.url)),
            "title": title,
            "content": _smart_truncate(content),
            "date_published": date_published,
            "author": author,
            "sitename": sitename,
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": normalize_url(url),
            "title": url,
            "content": "",
            "error": str(exc),
        }


async def search_searxng(
    searx_url: str,
    query: str,
    limit: int = 4,
    categories: Optional[str] = None,
    time_range: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not searx_url.strip() or not query.strip():
        return []

    params: Dict[str, Any] = {"q": query, "format": "json"}
    if categories:
        params["categories"] = categories
    if time_range and time_range != "any":
        params["time_range"] = time_range

    async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(f"{searx_url.rstrip('/')}/search", params=params)
        response.raise_for_status()
        payload = response.json()

    results: List[Dict[str, Any]] = []
    for result in payload.get("results", [])[:limit]:
        results.append(
            {
                "title": (result.get("title") or "").strip(),
                "url": normalize_url(result.get("url") or ""),
                "snippet": (result.get("content") or result.get("snippet") or "").strip(),
            }
        )
    return results


async def collect_research_material(
    *,
    topic: str,
    raw_sources: Sequence[str],
    searx_url: str = "",
    mode: str = "pre_generated",
    search_additional: bool = True,
    searxng_categories: str = "",
    searxng_time_range: str = "",
    searxng_max_results: int = 4,
    log_cb: LogCallback | None = None,
) -> Dict[str, Any]:
    documents: List[Dict[str, Any]] = []
    provided_urls: List[str] = []

    for raw_source in raw_sources:
        source = (raw_source or "").strip()
        if not source:
            continue
        if is_url(source):
            provided_urls.append(normalize_url(source))
            continue

        extracted_urls = extract_urls(source)
        if extracted_urls:
            provided_urls.extend(extracted_urls)

        remaining_text = _text_without_urls(source)
        if remaining_text:
            documents.append(
                _document_payload(
                    title="Provided Notes",
                    content=remaining_text,
                    kind="provided_text",
                )
            )

    provided_urls = _dedupe_strings(provided_urls)
    provided_url_set = set(provided_urls)
    if provided_urls and log_cb:
        await log_cb("running", f"Found {len(provided_urls)} provided source URL(s) to scrape.")

    search_results: List[Dict[str, Any]] = []
    search_urls: List[str] = []
    new_search_urls: List[str] = []
    should_search = mode != "source_dump" and search_additional and searx_url.strip() and topic.strip()
    if should_search:
        if log_cb:
            await log_cb("running", f"Searching SearXNG for: {topic}")
        try:
            search_results = await search_searxng(
                searx_url,
                topic,
                limit=searxng_max_results,
                categories=searxng_categories or None,
                time_range=searxng_time_range or None,
            )
            for result in search_results:
                if result.get("snippet"):
                    documents.append(
                        _document_payload(
                            title=result.get("title") or result.get("url") or "Search Result",
                            content=result["snippet"],
                            url=result.get("url", ""),
                            kind="search_result",
                        )
                    )
                if result.get("url"):
                    url = normalize_url(result["url"])
                    search_urls.append(url)
                    if url and url not in provided_url_set:
                        new_search_urls.append(url)
            if log_cb:
                await log_cb("running", f"SearXNG returned {len(search_results)} result(s).")
        except Exception as exc:
            if log_cb:
                await log_cb("warning", f"SearXNG search failed: {exc}")

    candidate_urls = _dedupe_strings([*provided_urls, *new_search_urls])[:10]
    if candidate_urls:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            for candidate_url in candidate_urls:
                if log_cb:
                    await log_cb("running", f"Scraping {candidate_url}")
                scraped = await scrape_url(candidate_url, client)
                if scraped["ok"]:
                    documents.append(
                        _document_payload(
                            title=scraped["title"],
                            content=scraped["content"],
                            url=scraped["url"],
                            kind="scraped_page",
                            date_published=scraped.get("date_published", ""),
                            author=scraped.get("author", ""),
                            sitename=scraped.get("sitename", ""),
                        )
                    )
                    if log_cb:
                        await log_cb("running", f"Scraped {scraped['url']} ({len(scraped['content'])} chars)")
                elif log_cb:
                    await log_cb("warning", f"Failed to scrape {scraped['url']}: {scraped.get('error', 'Unknown error')}")

    combined_text = "\n\n---\n\n".join(
        _format_document_for_context(document)
        for document in documents
        if document.get("content")
    )
    return {
        "documents": [document for document in documents if document.get("content")],
        "combined_text": combined_text,
        "search_results": search_results,
        "provided_urls": provided_urls,
        "search_urls": _dedupe_strings(search_urls),
        "new_search_urls": _dedupe_strings(new_search_urls),
        "scraped_urls": [
            document.get("url", "")
            for document in documents
            if document.get("kind") == "scraped_page" and document.get("url")
        ],
    }


def _content_hash(text: str) -> str:
    return str(hash(text))


async def build_rag_context(
    *,
    documents: Sequence[Dict[str, Any]],
    queries: List[str],
    max_final_chunks: int = 6,
) -> Dict[str, Any]:
    cleaned_documents = [document for document in documents if document.get("content")]
    if not cleaned_documents:
        return {
            "context": "",
            "retrieval_mode": "none",
            "selected_sources": [],
            "document_count": 0,
            "chunk_count": 0,
            "parent_chunk_count": 0,
            "child_chunk_count": 0,
            "reranked": False,
        }

    primary_query = queries[0] if queries else "Main ideas and supporting evidence"

    try:
        from langchain_chroma import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.retrievers import BM25Retriever
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        source_documents = [
            Document(
                page_content=_format_document_for_context(document),
                metadata={
                    "title": document.get("title", ""),
                    "url": document.get("url", ""),
                    "kind": document.get("kind", ""),
                    "date_published": document.get("date_published", ""),
                    "author": document.get("author", ""),
                },
            )
            for document in cleaned_documents
        ]

        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1600, chunk_overlap=200)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
        parent_chunks = parent_splitter.split_documents(source_documents)
        if not parent_chunks:
            return {
                "context": "",
                "retrieval_mode": "no_splits",
                "selected_sources": [],
                "document_count": len(cleaned_documents),
                "chunk_count": 0,
                "parent_chunk_count": 0,
                "child_chunk_count": 0,
                "reranked": False,
            }

        child_to_parent: Dict[str, Document] = {}
        all_child_chunks: List[Document] = []
        for parent_index, parent_doc in enumerate(parent_chunks):
            children = child_splitter.split_documents([parent_doc])
            for child_doc in children:
                child_doc.metadata["parent_idx"] = parent_index
                child_to_parent[_content_hash(child_doc.page_content)] = parent_doc
                all_child_chunks.append(child_doc)

        if not all_child_chunks:
            all_child_chunks = parent_chunks
            for document in all_child_chunks:
                child_to_parent[_content_hash(document.page_content)] = document

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        fetch_k = min(max(len(all_child_chunks), 30), 50)
        vectorstore = Chroma.from_documents(documents=all_child_chunks, embedding=embeddings)
        semantic_retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": fetch_k, "fetch_k": min(len(all_child_chunks), fetch_k * 2)},
        )

        bm25_retriever = BM25Retriever.from_documents(all_child_chunks)
        bm25_retriever.k = fetch_k

        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        for query in queries:
            try:
                sem_docs = semantic_retriever.invoke(query)
                bm25_docs = bm25_retriever.invoke(query)
                for rank, doc in enumerate(sem_docs):
                    key = _content_hash(doc.page_content)
                    doc_scores[key] = doc_scores.get(key, 0.0) + 1.0 / (60 + rank)
                    doc_map[key] = doc
                for rank, doc in enumerate(bm25_docs):
                    key = _content_hash(doc.page_content)
                    doc_scores[key] = doc_scores.get(key, 0.0) + (1.0 / (60 + rank)) * 0.5
                    doc_map[key] = doc
            except Exception as exc:
                print(f"[RAG] Warning: retrieval for query '{query}' failed: {exc}")

        all_retrieved = [doc_map[key] for key, _ in sorted(doc_scores.items(), key=lambda item: item[1], reverse=True)]
        if not all_retrieved:
            all_retrieved = all_child_chunks[: max_final_chunks * 2]

        reranked = False
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            scores = model.predict([[primary_query, doc.page_content] for doc in all_retrieved])
            scored = list(zip(all_retrieved, scores))
            scored.sort(key=lambda item: item[1], reverse=True)
            all_retrieved = [doc for doc, _ in scored][: max_final_chunks * 2]
            reranked = True
        except Exception as exc:
            print(f"[RAG] Warning: Cross-Encoder reranking failed: {exc}")
            all_retrieved = all_retrieved[: max_final_chunks * 2]

        selected_parents: List[Document] = []
        seen_parent_hashes: set[str] = set()
        for child_doc in all_retrieved:
            parent_doc = child_to_parent.get(_content_hash(child_doc.page_content), child_doc)
            parent_hash = _content_hash(parent_doc.page_content)
            if parent_hash not in seen_parent_hashes:
                seen_parent_hashes.add(parent_hash)
                selected_parents.append(parent_doc)
            if len(selected_parents) >= max_final_chunks:
                break

        try:
            vectorstore.delete_collection()
        except Exception:
            pass

        selected = selected_parents
        retrieval_mode = "parent_child_hybrid_reranked" if reranked else "parent_child_hybrid"
    except Exception as outer_err:
        print(f"[RAG] Primary retrieval pipeline failed: {type(outer_err).__name__}: {outer_err}")
        try:
            from langchain_community.retrievers import BM25Retriever
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            source_documents = [
                Document(
                    page_content=_format_document_for_context(document),
                    metadata={
                        "title": document.get("title", ""),
                        "url": document.get("url", ""),
                        "kind": document.get("kind", ""),
                    },
                )
                for document in cleaned_documents
            ]
            splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=180)
            splits = splitter.split_documents(source_documents)
            bm25_retriever = BM25Retriever.from_documents(splits)
            bm25_retriever.k = max_final_chunks
            selected = bm25_retriever.invoke(primary_query)
            all_child_chunks = splits
            parent_chunks = splits
            retrieval_mode = "bm25_fallback"
            reranked = False
        except Exception:
            selected = []
            for document in cleaned_documents[:max_final_chunks]:
                from types import SimpleNamespace

                selected.append(
                    SimpleNamespace(
                        page_content=_format_document_for_context(document),
                        metadata={
                            "title": document.get("title", ""),
                            "url": document.get("url", ""),
                            "kind": document.get("kind", ""),
                        },
                    )
                )
            all_child_chunks = selected
            parent_chunks = selected
            retrieval_mode = "keyword_fallback"
            reranked = False

    context_parts: List[str] = []
    selected_sources: List[str] = []
    for index, document in enumerate(selected, start=1):
        title = document.metadata.get("title") or f"Source {index}"
        url = document.metadata.get("url") or ""
        header = f"[Source {index}] {title}"
        if url:
            header += f"\nURL: {url}"
        if document.metadata.get("date_published"):
            header += f"\nPublished: {document.metadata['date_published']}"
        selected_sources.append(url if url else title)
        context_parts.append(f"{header}\n{document.page_content.strip()}")

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "retrieval_mode": retrieval_mode,
        "selected_sources": [source for source in selected_sources if source],
        "document_count": len(cleaned_documents),
        "chunk_count": len(all_child_chunks),
        "parent_chunk_count": len(parent_chunks),
        "child_chunk_count": len(all_child_chunks),
        "reranked": reranked,
    }
