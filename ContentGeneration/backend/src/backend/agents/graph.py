"""
ContentPilot LangGraph multi-step generation pipeline — V3.

Features: query expansion, async parallel source-dump summarization,
explicit source citations, and parent-child RAG integration.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import httpx
from langgraph.graph import END, StateGraph

from src.backend.services.research_pipeline import build_rag_context, collect_research_material
from src.backend.services.run_events import emit_run_event
from src.backend.utils.formatting import format_for_platform


class AgentState(TypedDict):
    channel: Dict[str, Any]
    item_date: str
    pillar: str
    topic: str
    special_instructions: str
    mode: str
    raw_sources: List[str]
    research_documents: List[Dict[str, Any]]
    scraped_data: str
    summarized_context: str
    draft: str
    formatted_content: str
    quality_report: str
    error: str
    model: Optional[str]
    ollama_base_url: Optional[str]
    searx_url: Optional[str]
    search_additional: bool
    searxng_categories: str
    searxng_time_range: str
    searxng_max_results: int
    memory_context: str
    source_urls: List[str]
    run_id: Optional[str]
    db_url: str
    agent_logs: List[Dict[str, Any]]


async def _append_log(
    state: AgentState,
    step: str,
    status: str,
    message: str = "",
    **extra: Any,
) -> List[Dict[str, Any]]:
    logs = list(state.get("agent_logs") or [])
    event = {
        "step": step,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if extra:
        event.update(extra)
    logs.append(event)
    await emit_run_event(state.get("run_id"), event)
    return logs


def _ollama_url(state: AgentState) -> str:
    return (state.get("ollama_base_url") or "").rstrip("/")


def _model_name(state: AgentState) -> str:
    return (state.get("model") or "").strip()


async def _ollama_generate(base_url: str, model: str, prompt: str, timeout: float = 120.0) -> str:
    if not base_url:
        raise ValueError("Ollama Base URL is not configured.")
    if not model:
        raise ValueError("Ollama model is not configured.")

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


# ---------------------------------------------------------------------------
# Query Expansion — generate multiple search variants from the topic
# ---------------------------------------------------------------------------

async def _expand_query(base_url: str, model: str, topic: str, pillar: str) -> List[str]:
    """Use the LLM to generate 3 diverse search queries for better retrieval coverage."""
    original_query = f"{topic} | {pillar}" if pillar else topic
    queries = [original_query]

    try:
        prompt = (
            "Generate 3 diverse search queries for retrieving information about the following topic.\n"
            "Each query should approach the topic from a different angle (e.g., definition, examples, recent news).\n\n"
            f"Topic: {topic}\n"
        )
        if pillar:
            prompt += f"Content pillar: {pillar}\n"
        prompt += "\nReturn ONLY the queries, one per line. No numbering, no explanation."

        result = await _ollama_generate(base_url, model, prompt, timeout=30.0)
        expanded = [line.strip() for line in result.strip().splitlines() if line.strip()]
        if expanded:
            queries.extend(expanded[:3])
    except Exception:
        pass  # Fallback: just use the original query

    return queries


# ---------------------------------------------------------------------------
# Research Node
# ---------------------------------------------------------------------------

async def research_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(
        state,
        "research",
        "running",
        "Collecting provided sources, search results, and scraped pages.",
    )

    async def _research_log(status: str, message: str) -> None:
        nonlocal logs
        logs = await _append_log({**state, "agent_logs": logs}, "research", status, message)

    material = await collect_research_material(
        topic=state.get("topic", ""),
        raw_sources=state.get("raw_sources") or [],
        searx_url=state.get("searx_url") or "",
        mode=state.get("mode") or "pre_generated",
        search_additional=state.get("search_additional", True),
        searxng_categories=state.get("searxng_categories", ""),
        searxng_time_range=state.get("searxng_time_range", ""),
        searxng_max_results=state.get("searxng_max_results", 4),
        log_cb=_research_log,
    )

    documents = material.get("documents", [])
    provided_urls = material.get("provided_urls", []) or []
    new_search_urls = material.get("new_search_urls", []) or []
    source_urls: List[str] = []
    seen: set[str] = set()
    for url in [*provided_urls, *new_search_urls]:
        u = (url or "").strip()
        if u and u not in seen:
            seen.add(u)
            source_urls.append(u)
    logs = await _append_log(
        {**state, "agent_logs": logs},
        "research",
        "done",
        f"Prepared {len(documents)} research document(s) for retrieval.",
    )
    return {
        "research_documents": documents,
        "scraped_data": material.get("combined_text", ""),
        "source_urls": source_urls,
        "agent_logs": logs,
    }


# ---------------------------------------------------------------------------
# Source Dump: Async Parallel Map-Reduce Summarization
# ---------------------------------------------------------------------------

async def _summarize_single_source(
    doc: Dict[str, Any],
    idx: int,
    total: int,
    topic: str,
    pillar: str,
    special: str,
    base_url: str,
    model: str,
) -> Dict[str, Any]:
    """Summarize a single source document. Returns a dict with summary or error."""
    content = doc.get("content", "")
    title = doc.get("title", "") or f"Source {idx}"
    url = doc.get("url", "")

    prompt = (
        f"You are a research assistant. Extract the most important facts, updates, and key points "
        f"from the following source text. Focus on anything relevant to the topic: '{topic}' and pillar: '{pillar}'.\n"
    )
    if special:
        prompt += f"Keep in mind the special instructions: {special}\n"
    prompt += (
        "Summarize the key information cleanly. Use bullet points for facts. Do not add meta-commentary.\n\n"
        f"--- SOURCE TEXT ---\n{content[:12000]}\n"
    )

    try:
        summary = await _ollama_generate(base_url, model, prompt)
        header = f"[Source {idx}] {title}"
        if url:
            header += f"\nURL: {url}"
        return {"ok": True, "idx": idx, "title": title, "summary": f"{header}\n{summary.strip()}"}
    except Exception as exc:
        header = f"[Source {idx}] {title}"
        if url:
            header += f"\nURL: {url}"
        return {
            "ok": False,
            "idx": idx,
            "title": title,
            "summary": f"{header}\n{content[:2000].strip()}",
            "error": str(exc),
        }


async def _summarize_source_dump_mode(
    state: AgentState, documents: List[Dict[str, Any]], logs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Async parallel Map-Reduce summarization for source dump generation mode."""
    topic = state.get("topic", "")
    pillar = state.get("pillar", "")
    special = state.get("special_instructions", "")
    base_url = _ollama_url(state)
    model = _model_name(state)

    filtered_docs = [d for d in documents if d.get("content")]
    if not filtered_docs:
        logs = await _append_log(
            {**state, "agent_logs": logs}, "summarize", "warning",
            "No readable content found in dumped sources.",
        )
        return {"summarized_context": f"Topic: {topic}", "agent_logs": logs}

    logs = await _append_log(
        {**state, "agent_logs": logs}, "summarize", "running",
        f"Launching parallel summarization of {len(filtered_docs)} source(s)...",
    )

    # Launch all summarizations in parallel
    tasks = [
        _summarize_single_source(doc, idx, len(filtered_docs), topic, pillar, special, base_url, model)
        for idx, doc in enumerate(filtered_docs, start=1)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect summaries and log results
    summaries: List[str] = []
    for result in results:
        if isinstance(result, Exception):
            logs = await _append_log(
                {**state, "agent_logs": logs}, "summarize", "warning",
                f"Summarization task failed: {result}",
            )
            continue

        if result.get("ok"):
            summaries.append(result["summary"])
            logs = await _append_log(
                {**state, "agent_logs": logs}, "summarize", "running",
                f"✓ Summarized source {result['idx']}/{len(filtered_docs)}: {result['title']}",
            )
        else:
            summaries.append(result["summary"])
            logs = await _append_log(
                {**state, "agent_logs": logs}, "summarize", "warning",
                f"Failed to summarize source {result['idx']}: {result.get('error', '')}. Using raw snippet.",
            )

    final_context = "\n\n---\n\n".join(summaries)

    # ── Store source dump chunks to pgvector ──
    db_url = state.get("db_url", "")
    channel_id = state["channel"].get("id", "")
    if db_url and channel_id and filtered_docs:
        try:
            from src.backend.services.embedding_service import EmbeddingService
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            import hashlib

            embedding_service = EmbeddingService(lambda: db_url)
            parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1600, chunk_overlap=200)
            child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)

            chunks_to_store = []
            for doc in filtered_docs:
                content = doc.get("content", "")
                if not content.strip():
                    continue

                parent_texts = parent_splitter.split_text(content)
                for parent_text in parent_texts:
                    child_texts = child_splitter.split_text(parent_text)
                    for child_text in child_texts:
                        chunks_to_store.append({
                            "chunk_text": child_text,
                            "parent_chunk_text": parent_text,
                            "source_url": doc.get("url", ""),
                            "source_title": doc.get("title", ""),
                            "kind": doc.get("kind", "source_dump"),
                            "metadata": {
                                "date_published": doc.get("date_published", ""),
                                "author": doc.get("author", ""),
                            }
                        })

            if chunks_to_store:
                print(f"[pgvector] Storing {len(chunks_to_store)} source dump chunks for channel {channel_id}")
                result = embedding_service.store_chunks(channel_id, chunks_to_store)
                print(f"[pgvector] ✅ Store result: {result}")
        except Exception as e:
            print(f"[pgvector] ❌ Source dump embedding failed: {type(e).__name__}: {e}")

    logs = await _append_log(
        {**state, "agent_logs": logs}, "summarize", "done",
        f"Completed parallel map-reduce summarization of {len(filtered_docs)} source(s).",
    )
    return {"summarized_context": final_context, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Summarize Node — with Query Expansion + Parent-Child RAG
# ---------------------------------------------------------------------------

async def summarize_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(state, "summarize", "running", "Building the retrieval corpus.")
    research_documents = state.get("research_documents") or []

    if not research_documents and not (state.get("scraped_data") or "").strip():
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "summarize", "done",
            "No source material found. Falling back to the topic only.",
        )
        return {"summarized_context": f"Topic: {state.get('topic', '')}", "agent_logs": logs}

    if state.get("mode") == "source_dump":
        return await _summarize_source_dump_mode(state, research_documents, logs)

    # ── Query Expansion ──
    topic = state.get("topic", "")
    pillar = state.get("pillar", "")
    special = state.get("special_instructions", "")
    base_url = _ollama_url(state)
    model = _model_name(state)

    logs = await _append_log(
        {**state, "agent_logs": logs}, "summarize", "running",
        "Expanding query into multiple search variants...",
    )

    queries = await _expand_query(base_url, model, topic, pillar)
    logs = await _append_log(
        {**state, "agent_logs": logs}, "summarize", "running",
        f"Expanded to {len(queries)} query variant(s): {' | '.join(q[:60] for q in queries)}",
    )

    # ── Initialize Embedding Service ──
    from src.backend.services.embedding_service import EmbeddingService
    db_url = state.get("db_url", "")
    print(f"[pgvector-debug] db_url from state: '{db_url[:40]}...' " if db_url else "[pgvector-debug] db_url is EMPTY!")
    embedding_service = EmbeddingService(lambda: db_url) if db_url else None
    channel_id = state["channel"].get("id", "")
    print(f"[pgvector-debug] embedding_service={'initialized' if embedding_service else 'None'}, channel_id='{channel_id}'")

    # ── RAG with parent-child chunking + re-ranking + multi-query ──
    rag_result = await build_rag_context(
        documents=research_documents,
        queries=queries,
        embedding_service=embedding_service,
        channel_id=channel_id,
    )
    logs = await _append_log(
        {**state, "agent_logs": logs},
        "summarize", "running",
        f"RAG: {rag_result['document_count']} doc(s), "
        f"{rag_result.get('parent_chunk_count', 0)} parent chunks, "
        f"{rag_result.get('child_chunk_count', 0)} child chunks, "
        f"mode={rag_result['retrieval_mode']}, "
        f"reranked={rag_result.get('reranked', False)}.",
    )
    if rag_result.get("selected_sources"):
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "summarize", "running",
            f"Retrieved supporting sources: {', '.join(rag_result['selected_sources'][:5])}",
        )

    context = rag_result.get("context") or state.get("scraped_data", "") or f"Topic: {topic}"
    prompt = (
        "You are a research summarizer. Turn the retrieved evidence into a concise brief for a content writer.\n"
        "Preserve the strongest facts, useful examples, and source-backed claims.\n"
        "If URLs are present, keep them associated with the relevant points.\n\n"
        f"--- RETRIEVED CONTEXT ---\n{context[:12000]}\n\n"
        "Return a structured summary with sections for key ideas, evidence, and usable angles."
    )

    try:
        summary = await _ollama_generate(base_url, model, prompt)
    except Exception as exc:
        summary = context
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "summarize", "warning",
            f"Summarization failed: {exc}. Using retrieved context directly.",
        )

    logs = await _append_log(
        {**state, "agent_logs": logs},
        "summarize", "done",
        f"Prepared a {len(summary)} character writing brief.",
    )
    return {"summarized_context": summary, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Writer Node — with Explicit Source Citations
# ---------------------------------------------------------------------------

async def writer_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(state, "writer", "running", "Generating the draft from the retrieved brief.")

    channel = state.get("channel", {})
    context = state.get("summarized_context") or state.get("scraped_data", "")
    memory_context = state.get("memory_context", "")
    source_urls = state.get("source_urls") or []

    prompt = (
        f"You are an expert content writer for the channel '{channel.get('name')}'.\n"
        f"Platform: {channel.get('platform')}\n"
        f"Target audience: {channel.get('audience')}\n"
        f"Tone & voice: {channel.get('tone')}\n"
        f"Content pillar: {state.get('pillar')}\n"
        f"Topic: {state.get('topic')}\n\n"
        f"--- RESEARCH CONTEXT ---\n{context[:7000]}\n\n"
    )

    # Inject numbered source list for explicit citation
    if source_urls:
        prompt += "--- SOURCES (cite by number) ---\n"
        for i, url in enumerate(source_urls, start=1):
            prompt += f"[{i}] {url}\n"
        prompt += "\n"

    if memory_context:
        prompt += f"--- CHANNEL MEMORY & CONTEXT ---\n{memory_context}\n\n"
    if state.get("special_instructions"):
        prompt += f"Special instructions: {state['special_instructions']}\n"
    if channel.get("prompt_template"):
        prompt += f"Channel prompt template: {channel['prompt_template']}\n"

    prompt += (
        "\nWrite ONE polished, high-quality post that is ready for publication.\n"
        "Do not add meta commentary.\n\n"
        "Hard rules:\n"
        "1. Do not invent sources, facts, or URLs.\n"
        "2. Only use information that appears in the research context.\n"
        "3. Cite sources using [1], [2] etc. from the SOURCES list above where relevant.\n"
        "4. End the post with a 'Sources:' section listing the URLs you cited.\n"
        "5. If no SOURCES list was provided, do not invent a sources section."
    )

    try:
        draft = await _ollama_generate(_ollama_url(state), _model_name(state), prompt)
    except Exception as exc:
        draft = f"Error generating content: {exc}"
        logs = await _append_log(
            {**state, "agent_logs": logs}, "writer", "error", str(exc),
        )

    logs = await _append_log(
        {**state, "agent_logs": logs}, "writer", "done",
        f"Draft generated ({len(draft)} chars).",
    )
    return {"draft": draft, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Formatter Node
# ---------------------------------------------------------------------------

async def formatter_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(state, "formatter", "running", "Applying channel formatting rules.")
    draft = state.get("draft", "")
    platform = state.get("channel", {}).get("platform", "whatsapp")

    if draft.startswith("Error"):
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "formatter", "done",
            "Skipped because draft generation failed.",
        )
        return {"formatted_content": draft, "agent_logs": logs}

    formatted = format_for_platform(draft, platform)
    urls = state.get("source_urls") or []
    if urls and "sources:" not in formatted.lower():
        formatted = (
            formatted.rstrip()
            + "\n\nSources:\n"
            + "\n".join(f"- {u}" for u in urls)
        )
    logs = await _append_log(
        {**state, "agent_logs": logs},
        "formatter", "done",
        f"Formatted output for {platform} ({len(formatted)} chars).",
    )
    return {"formatted_content": formatted, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Quality Node
# ---------------------------------------------------------------------------

async def quality_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(state, "quality", "running", "Checking content quality and length.")
    formatted = state.get("formatted_content", "")
    channel = state.get("channel", {})
    platform = channel.get("platform", "whatsapp")

    issues: List[str] = []
    limits = {
        "whatsapp": 4000,
        "twitter": 280,
        "linkedin": 3000,
        "telegram": 4096,
    }
    limit = limits.get(platform, 5000)
    if len(formatted) > limit:
        issues.append(f"Content exceeds the {platform} limit: {len(formatted)}/{limit} chars")

    tone = channel.get("tone", "").lower()
    if tone == "professional" and formatted.count("!") > 5:
        issues.append("Too many exclamation marks for a professional tone")

    report = "; ".join(issues) if issues else "All checks passed."
    logs = await _append_log(
        {**state, "agent_logs": logs}, "quality", "done", report,
    )
    return {"quality_report": report, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("research", research_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("formatter", formatter_node)
    workflow.add_node("quality", quality_node)

    workflow.set_entry_point("research")
    workflow.add_edge("research", "summarize")
    workflow.add_edge("summarize", "writer")
    workflow.add_edge("writer", "formatter")
    workflow.add_edge("formatter", "quality")
    workflow.add_edge("quality", END)
    return workflow.compile()


content_graph = build_graph()
