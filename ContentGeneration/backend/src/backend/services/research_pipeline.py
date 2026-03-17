from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any, Awaitable, Callable, Dict, List, Sequence
from urllib.parse import urlparse

import httpx


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+")

LogCallback = Callable[[str, str], Awaitable[None]]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._title_parts: List[str] = []
        self._text_parts: List[str] = []
        self._capture_break = False

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._capture_break = True
        if tag in {"p", "article", "section", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._capture_break = False
        if tag in {"p", "article", "section", "div", "li"}:
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


def _query_terms(query: str) -> set[str]:
    return {term for term in re.findall(r"[a-zA-Z0-9]{3,}", query.lower())}


def _fallback_rank_documents(documents: Sequence[Any], query: str, limit: int) -> List[Any]:
    terms = _query_terms(query)
    if not terms:
        return list(documents[:limit])

    def _score(document: Any) -> tuple[int, int]:
        content = (document.page_content if hasattr(document, "page_content") else str(document)).lower()
        hits = sum(content.count(term) for term in terms)
        return hits, len(content)

    ranked = sorted(documents, key=_score, reverse=True)
    return list(ranked[:limit])


async def search_searxng(searx_url: str, query: str, limit: int = 4) -> List[Dict[str, Any]]:
    if not searx_url.strip() or not query.strip():
        return []

    async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(
            f"{searx_url.rstrip('/')}/search",
            params={"q": query, "format": "json"},
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
            "content": content[:18000],
        }
    except Exception as exc:
        return {"ok": False, "url": normalize_url(url), "title": url, "content": "", "error": str(exc)}


async def collect_research_material(
    *,
    topic: str,
    raw_sources: Sequence[str],
    searx_url: str = "",
    mode: str = "pre_generated",
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
    if provided_urls and log_cb:
        await log_cb("running", f"Found {len(provided_urls)} provided source URL(s) to scrape.")

    search_results: List[Dict[str, Any]] = []
    search_urls: List[str] = []
    if mode != "source_dump" and searx_url.strip() and topic.strip():
        if log_cb:
            await log_cb("running", f"Searching SearXNG for: {topic}")
        try:
            search_results = await search_searxng(searx_url, topic)
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
                    search_urls.append(result["url"])
            if log_cb:
                await log_cb(
                    "running",
                    f"SearXNG returned {len(search_results)} result(s): {', '.join(result['url'] for result in search_results if result.get('url'))}",
                )
        except Exception as exc:
            if log_cb:
                await log_cb("warning", f"SearXNG search failed: {exc}")

    candidate_urls = _dedupe_strings([*provided_urls, *search_urls])[:10]
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
                        await log_cb(
                            "running",
                            f"Scraped {scraped['url']} ({len(scraped['content'])} chars)",
                        )
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
        "scraped_urls": [document.get("url", "") for document in documents if document.get("kind") == "scraped_page" and document.get("url")],
    }


async def build_rag_context(
    *,
    documents: Sequence[Dict[str, Any]],
    query: str,
    max_chunks: int = 6,
) -> Dict[str, Any]:
    cleaned_documents = [document for document in documents if document.get("content")]
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
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": min(max_chunks, len(splits)), "fetch_k": min(max(len(splits), max_chunks * 3), 20)},
        )
        retrieved = retriever.invoke(query or "Main ideas and supporting evidence")
        selected = retrieved[:max_chunks]
        retrieval_mode = "semantic_mmr"
        try:
            vectorstore.delete_collection()
        except Exception:
            pass
    except Exception:
        from dataclasses import dataclass

        @dataclass
        class _FallbackDocument:
            page_content: str
            metadata: Dict[str, Any]

        base_documents = [
            _FallbackDocument(
                page_content=_format_document_for_context(document),
                metadata={
                    "title": document.get("title", ""),
                    "url": document.get("url", ""),
                    "kind": document.get("kind", ""),
                },
            )
            for document in cleaned_documents
        ]
        selected = _fallback_rank_documents(base_documents, query, max_chunks)
        splits = base_documents
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
