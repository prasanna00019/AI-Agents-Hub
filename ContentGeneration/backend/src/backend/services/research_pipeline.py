"""
ContentPilot Research Pipeline — V3

Handles web scraping (trafilatura), SearXNG search, parent-child chunking,
hybrid retrieval (BM25 + Semantic), cross-encoder re-ranking, and
multi-query support.
"""

from __future__ import annotations

import hashlib
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


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

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
    """Truncate text at a paragraph boundary near max_len."""
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


# ---------------------------------------------------------------------------
# Web scraping — trafilatura-based
# ---------------------------------------------------------------------------

async def scrape_url(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrape a URL using trafilatura for clean content extraction."""
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

        # Extract metadata (title, date, author, sitename)
        metadata = trafilatura.extract_metadata(raw_html)
        title = ""
        date_published = ""
        author = ""
        sitename = ""

        if metadata:
            title = metadata.title or ""
            date_published = str(metadata.date) if metadata.date else ""
            author = metadata.author or ""
            sitename = metadata.sitename or ""

        if not title:
            title = urlparse(str(response.url)).netloc

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


# ---------------------------------------------------------------------------
# SearXNG search
# ---------------------------------------------------------------------------

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
        response = await client.get(
            f"{searx_url.rstrip('/')}/search",
            params=params,
        )
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


# ---------------------------------------------------------------------------
# Research material collector
# ---------------------------------------------------------------------------

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
    should_search = (mode != "source_dump") and search_additional and searx_url.strip() and topic.strip()
    if should_search:
        if log_cb:
            await log_cb("running", f"Searching SearXNG for: {topic}")
        try:
            search_results = await search_searxng(
                searx_url, topic,
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
                filtered_urls = [u for u in new_search_urls if u]
                await log_cb(
                    "running",
                    f"SearXNG returned {len(search_results)} result(s): "
                    f"{', '.join(r['url'] for r in search_results if r.get('url'))}",
                )
                if filtered_urls:
                    await log_cb(
                        "running",
                        f"Filtered to {len(filtered_urls)} new URL(s) (excluding provided sources).",
                    )
        except Exception as exc:
            if log_cb:
                await log_cb("warning", f"SearXNG search failed: {exc}")

    # Candidate scrape list
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
        _format_document_for_context(doc)
        for doc in documents if doc.get("content")
    )
    return {
        "documents": [doc for doc in documents if doc.get("content")],
        "combined_text": combined_text,
        "search_results": search_results,
        "provided_urls": provided_urls,
        "search_urls": _dedupe_strings(search_urls),
        "new_search_urls": _dedupe_strings(new_search_urls),
        "scraped_urls": [
            doc.get("url", "") for doc in documents
            if doc.get("kind") == "scraped_page" and doc.get("url")
        ],
    }


# ---------------------------------------------------------------------------
# RAG context builder — Parent-Child Chunking + Re-ranking + Multi-query
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


async def build_rag_context(
    *,
    documents: Sequence[Dict[str, Any]],
    queries: List[str],
    max_final_chunks: int = 6,
) -> Dict[str, Any]:
    """Build RAG context using parent-child chunking, hybrid retrieval, and re-ranking.

    Args:
        documents: List of document dicts with 'content', 'title', 'url', etc.
        queries: List of query strings (from query expansion). At least one required.
        max_final_chunks: Number of final parent chunks to return after re-ranking.
    """
    cleaned_documents = [doc for doc in documents if doc.get("content")]
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
        from langchain.retrievers import EnsembleRetriever

        # Build LangChain Document objects
        source_documents = [
            Document(
                page_content=_format_document_for_context(doc),
                metadata={
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "kind": doc.get("kind", ""),
                    "date_published": doc.get("date_published", ""),
                    "author": doc.get("author", ""),
                },
            )
            for doc in cleaned_documents
        ]

        # ── Parent-Child Chunking ──
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

        # Build child chunks and map them back to parents
        child_to_parent: Dict[str, Document] = {}
        all_child_chunks: List[Document] = []

        for parent_idx, parent_doc in enumerate(parent_chunks):
            children = child_splitter.split_documents([parent_doc])
            for child_doc in children:
                child_doc.metadata["parent_idx"] = parent_idx
                child_to_parent[_content_hash(child_doc.page_content)] = parent_doc
                all_child_chunks.append(child_doc)

        if not all_child_chunks:
            all_child_chunks = parent_chunks
            for doc in all_child_chunks:
                child_to_parent[_content_hash(doc.page_content)] = doc

        # ── Hybrid Retrieval on child chunks ──
        fetch_k = min(max(len(all_child_chunks), 30), 50)
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents=all_child_chunks, embedding=embeddings)
        semantic_retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": fetch_k,
                "fetch_k": min(len(all_child_chunks), fetch_k * 2),
            },
        )

        bm25_retriever = BM25Retriever.from_documents(all_child_chunks)
        bm25_retriever.k = fetch_k

        ensemble_retriever = EnsembleRetriever(
            retrievers=[semantic_retriever, bm25_retriever],
            weights=[0.5, 0.5],
        )

        # ── Multi-query retrieval: pool results from all queries ──
        all_retrieved: List[Document] = []
        seen_hashes: set[str] = set()

        for q in queries:
            try:
                results = ensemble_retriever.invoke(q)
                for doc in results:
                    h = _content_hash(doc.page_content)
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_retrieved.append(doc)
            except Exception:
                pass

        if not all_retrieved:
            all_retrieved = ensemble_retriever.invoke(primary_query)

        # ── Cross-Encoder Re-Ranking ──
        reranked = False
        try:
            from langchain.retrievers.document_compressors import CrossEncoderReranker
            from langchain_community.cross_encoders import HuggingFaceCrossEncoder

            reranker_model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
            compressor = CrossEncoderReranker(model=reranker_model, top_n=max_final_chunks * 2)

            # Re-rank the pooled child chunks
            reranked_children = compressor.compress_documents(all_retrieved, primary_query)
            all_retrieved = list(reranked_children)[:max_final_chunks * 2]
            reranked = True
        except Exception:
            # Fallback: just truncate
            all_retrieved = all_retrieved[:max_final_chunks * 2]

        # ── Map child chunks → parent chunks (deduplicated) ──
        selected_parents: List[Document] = []
        seen_parent_hashes: set[str] = set()

        for child_doc in all_retrieved:
            child_hash = _content_hash(child_doc.page_content)
            parent_doc = child_to_parent.get(child_hash, child_doc)
            parent_hash = _content_hash(parent_doc.page_content)
            if parent_hash not in seen_parent_hashes:
                seen_parent_hashes.add(parent_hash)
                selected_parents.append(parent_doc)
            if len(selected_parents) >= max_final_chunks:
                break

        retrieval_mode = "parent_child_hybrid_reranked" if reranked else "parent_child_hybrid"

        try:
            vectorstore.delete_collection()
        except Exception:
            pass

        selected = selected_parents

    except Exception:
        # Fallback: BM25-only retrieval (no parent-child, no re-ranking)
        try:
            from langchain_community.retrievers import BM25Retriever
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            source_documents = [
                Document(
                    page_content=_format_document_for_context(doc),
                    metadata={
                        "title": doc.get("title", ""),
                        "url": doc.get("url", ""),
                        "kind": doc.get("kind", ""),
                    },
                )
                for doc in cleaned_documents
            ]
            splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=180)
            splits = splitter.split_documents(source_documents)

            bm25_retriever = BM25Retriever.from_documents(splits)
            bm25_retriever.k = max_final_chunks
            selected = bm25_retriever.invoke(primary_query)
            retrieval_mode = "bm25_fallback"
            all_child_chunks = splits
            parent_chunks = splits
            reranked = False
        except Exception:
            # Ultimate fallback: simple keyword scoring
            from dataclasses import dataclass

            @dataclass
            class _FallbackDocument:
                page_content: str
                metadata: Dict[str, Any]

            base_docs = [
                _FallbackDocument(
                    page_content=_format_document_for_context(doc),
                    metadata={
                        "title": doc.get("title", ""),
                        "url": doc.get("url", ""),
                        "kind": doc.get("kind", ""),
                    },
                )
                for doc in cleaned_documents
            ]
            terms = {t for t in re.findall(r"[a-zA-Z0-9]{3,}", primary_query.lower())}
            if terms:
                scored = sorted(
                    base_docs,
                    key=lambda d: sum(d.page_content.lower().count(t) for t in terms),
                    reverse=True,
                )
                selected = scored[:max_final_chunks]
            else:
                selected = base_docs[:max_final_chunks]
            all_child_chunks = base_docs
            parent_chunks = base_docs
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
        "selected_sources": [s for s in selected_sources if s],
        "document_count": len(cleaned_documents),
        "chunk_count": len(all_child_chunks) if 'all_child_chunks' in dir() else 0,
        "parent_chunk_count": len(parent_chunks) if 'parent_chunks' in dir() else 0,
        "child_chunk_count": len(all_child_chunks) if 'all_child_chunks' in dir() else 0,
        "reranked": reranked if 'reranked' in dir() else False,
    }
