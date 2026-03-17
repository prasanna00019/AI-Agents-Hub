from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence
from urllib.parse import urlparse

import httpx


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+")

LogCallback = Callable[[str, str], Awaitable[None]]


# ---------------------------------------------------------------------------
# HTML text extraction — improved with article/main prioritization
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._title_parts: List[str] = []
        self._text_parts: List[str] = []
        self._capture_break = False

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._capture_break = True
        if tag in {"p", "article", "section", "div", "br", "li",
                    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._capture_break = False
        if tag in {"p", "article", "section", "div", "li", "blockquote"}:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._capture_break:
            self._title_parts.append(cleaned)
        self._text_parts.append(cleaned + " ")

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()

    @property
    def text(self) -> str:
        text = "".join(self._text_parts)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


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
) -> Dict[str, Any]:
    return {
        "title": title.strip() or label.strip() or url or kind.replace("_", " ").title(),
        "content": content.strip(),
        "url": normalize_url(url) if url else "",
        "kind": kind,
        "label": label.strip(),
    }


def _format_document_for_context(document: Dict[str, Any]) -> str:
    header_bits = [document.get("title", "").strip()]
    if document.get("url"):
        header_bits.append(f"URL: {document['url']}")
    header = "\n".join(bit for bit in header_bits if bit)
    return f"{header}\n{document.get('content', '').strip()}".strip()


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
# Web scraping
# ---------------------------------------------------------------------------

async def scrape_url(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        parser = _HTMLTextExtractor()
        parser.feed(response.text)
        content = parser.text
        title = parser.title or urlparse(str(response.url)).netloc
        if not content:
            raise ValueError("No readable content found on the page.")
        return {
            "ok": True,
            "url": normalize_url(str(response.url)),
            "title": title,
            "content": _smart_truncate(content),
        }
    except Exception as exc:
        return {"ok": False, "url": normalize_url(url), "title": url, "content": "", "error": str(exc)}


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

    # Candidate scrape list:
    # - always include user-provided URLs
    # - only include *new* search URLs (exclude anything the user already gave)
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
# RAG context builder — LangChain EnsembleRetriever (BM25 + Semantic MMR)
# ---------------------------------------------------------------------------

async def build_rag_context(
    *,
    documents: Sequence[Dict[str, Any]],
    query: str,
    max_chunks: int = 6,
) -> Dict[str, Any]:
    cleaned_documents = [doc for doc in documents if doc.get("content")]
    if not cleaned_documents:
        return {
            "context": "",
            "retrieval_mode": "none",
            "selected_sources": [],
            "document_count": 0,
            "chunk_count": 0,
        }

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
                },
            )
            for doc in cleaned_documents
        ]

        # Chunk for retrieval
        splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=180)
        splits = splitter.split_documents(source_documents)

        if not splits:
            return {
                "context": "",
                "retrieval_mode": "no_splits",
                "selected_sources": [],
                "document_count": len(cleaned_documents),
                "chunk_count": 0,
            }

        # Semantic retriever via Chroma + HuggingFace embeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
        semantic_retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": max_chunks,
                "fetch_k": min(max(len(splits), max_chunks * 3), 30),
            },
        )

        # BM25 keyword retriever (uses rank_bm25 under the hood)
        bm25_retriever = BM25Retriever.from_documents(splits)
        bm25_retriever.k = max_chunks

        # Hybrid retriever: combines both with Reciprocal Rank Fusion
        # weights: 0.5 semantic + 0.5 BM25 for balanced retrieval
        ensemble_retriever = EnsembleRetriever(
            retrievers=[semantic_retriever, bm25_retriever],
            weights=[0.5, 0.5],
        )

        selected = ensemble_retriever.invoke(query or "Main ideas and supporting evidence")
        selected = selected[:max_chunks]
        retrieval_mode = "hybrid_ensemble_bm25_semantic"

        try:
            vectorstore.delete_collection()
        except Exception:
            pass

    except Exception:
        # Fallback: basic BM25-only retrieval
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
            bm25_retriever.k = max_chunks
            selected = bm25_retriever.invoke(query or "Main ideas and supporting evidence")
            retrieval_mode = "bm25_fallback"
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
            terms = {t for t in re.findall(r"[a-zA-Z0-9]{3,}", query.lower())}
            if terms:
                scored = sorted(
                    base_docs,
                    key=lambda d: sum(d.page_content.lower().count(t) for t in terms),
                    reverse=True,
                )
                selected = scored[:max_chunks]
            else:
                selected = base_docs[:max_chunks]
            splits = base_docs
            retrieval_mode = "keyword_fallback"

    context_parts: List[str] = []
    selected_sources: List[str] = []
    for index, document in enumerate(selected, start=1):
        title = document.metadata.get("title") or f"Source {index}"
        url = document.metadata.get("url") or ""
        header = f"[Source {index}] {title}"
        if url:
            header += f"\nURL: {url}"
            selected_sources.append(url)
        context_parts.append(f"{header}\n{document.page_content.strip()}")

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "retrieval_mode": retrieval_mode,
        "selected_sources": selected_sources,
        "document_count": len(cleaned_documents),
        "chunk_count": len(splits),
    }
