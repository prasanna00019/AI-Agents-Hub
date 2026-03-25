"""
ContentPilot LangGraph generation pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import httpx
from langgraph.graph import END, StateGraph

from services.research_pipeline import build_rag_context, collect_research_material
from services.run_events import emit_run_event
from utils.formatting import format_for_platform


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
        response = await client.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()


async def _expand_query(base_url: str, model: str, topic: str, pillar: str) -> List[str]:
    queries = [f"{topic} | {pillar}" if pillar else topic]
    try:
        prompt = (
            "Generate 3 diverse search queries for retrieving reliable information about this topic.\n"
            "Each query should represent a different angle, such as definition, practical example, or current update.\n\n"
            f"Topic: {topic}\n"
        )
        if pillar:
            prompt += f"Content pillar: {pillar}\n"
        prompt += "\nReturn only the queries, one per line."
        expanded = await _ollama_generate(base_url, model, prompt, timeout=30.0)
        queries.extend([line.strip() for line in expanded.splitlines() if line.strip()][:3])
    except Exception:
        pass
    return queries


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
    source_urls: List[str] = []
    seen: set[str] = set()
    for url in [*(material.get("provided_urls") or []), *(material.get("new_search_urls") or [])]:
        normalized = (url or "").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            source_urls.append(normalized)

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


async def summarize_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(state, "summarize", "running", "Building the retrieval corpus.")
    research_documents = state.get("research_documents") or []
    if not research_documents and not (state.get("scraped_data") or "").strip():
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "summarize",
            "done",
            "No source material found. Falling back to the topic only.",
        )
        return {"summarized_context": f"Topic: {state.get('topic', '')}", "agent_logs": logs}

    queries = await _expand_query(_ollama_url(state), _model_name(state), state.get("topic", ""), state.get("pillar", ""))
    logs = await _append_log(
        {**state, "agent_logs": logs},
        "summarize",
        "running",
        f"Expanded to {len(queries)} query variant(s).",
    )

    rag_result = await build_rag_context(
        documents=research_documents,
        queries=queries,
    )
    logs = await _append_log(
        {**state, "agent_logs": logs},
        "summarize",
        "running",
        f"RAG: {rag_result['document_count']} doc(s), mode={rag_result['retrieval_mode']}, reranked={rag_result.get('reranked', False)}.",
    )

    context = rag_result.get("context") or state.get("scraped_data", "") or f"Topic: {state.get('topic', '')}"
    prompt = (
        "You are a research summarizer. Turn the retrieved evidence into a concise brief for a content writer.\n"
        "Preserve strong facts, practical examples, and source-backed claims. Keep URLs associated with the relevant points.\n\n"
        f"--- RETRIEVED CONTEXT ---\n{context[:12000]}\n\n"
        "Return a structured summary with sections for key ideas, evidence, and content angles."
    )

    try:
        summary = await _ollama_generate(_ollama_url(state), _model_name(state), prompt)
    except Exception as exc:
        summary = context
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "summarize",
            "warning",
            f"Summarization failed: {exc}. Using retrieved context directly.",
        )

    logs = await _append_log(
        {**state, "agent_logs": logs},
        "summarize",
        "done",
        f"Prepared a {len(summary)} character writing brief.",
    )
    return {"summarized_context": summary, "agent_logs": logs}


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

    if source_urls:
        prompt += "--- SOURCES (cite by number) ---\n"
        for index, url in enumerate(source_urls, start=1):
            prompt += f"[{index}] {url}\n"
        prompt += "\n"

    if memory_context:
        prompt += f"--- CHANNEL MEMORY & CONTEXT ---\n{memory_context}\n\n"
    if state.get("special_instructions"):
        prompt += f"Special instructions: {state['special_instructions']}\n"
    if channel.get("prompt_template"):
        prompt += f"Channel prompt template: {channel['prompt_template']}\n"

    prompt += (
        "\nWrite one polished post ready for publication.\n"
        "Do not add meta commentary.\n\n"
        "Hard rules:\n"
        "1. Do not invent facts, sources, or URLs.\n"
        "2. Only use information present in the research context.\n"
        "3. Cite sources using [1], [2], etc. where relevant.\n"
        "4. End with a 'Sources:' section listing only the URLs you actually cited.\n"
        "5. If no source list exists, do not invent a sources section."
    )

    try:
        draft = await _ollama_generate(_ollama_url(state), _model_name(state), prompt)
    except Exception as exc:
        draft = f"Error generating content: {exc}"
        logs = await _append_log({**state, "agent_logs": logs}, "writer", "error", str(exc))

    logs = await _append_log(
        {**state, "agent_logs": logs},
        "writer",
        "done",
        f"Draft generated ({len(draft)} chars).",
    )
    return {"draft": draft, "agent_logs": logs}


async def formatter_node(state: AgentState) -> Dict[str, Any]:
    logs = await _append_log(state, "formatter", "running", "Applying channel formatting rules.")
    draft = state.get("draft", "")
    platform = state.get("channel", {}).get("platform", "whatsapp")

    if draft.startswith("Error"):
        logs = await _append_log(
            {**state, "agent_logs": logs},
            "formatter",
            "done",
            "Skipped because draft generation failed.",
        )
        return {"formatted_content": draft, "agent_logs": logs}

    formatted = format_for_platform(draft, platform)
    urls = state.get("source_urls") or []
    if urls and "sources:" not in formatted.lower():
        formatted = formatted.rstrip() + "\n\nSources:\n" + "\n".join(f"- {url}" for url in urls)

    logs = await _append_log(
        {**state, "agent_logs": logs},
        "formatter",
        "done",
        f"Formatted output for {platform} ({len(formatted)} chars).",
    )
    return {"formatted_content": formatted, "agent_logs": logs}


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

    if channel.get("tone", "").lower() == "professional" and formatted.count("!") > 5:
        issues.append("Too many exclamation marks for a professional tone")

    report = "; ".join(issues) if issues else "All checks passed."
    logs = await _append_log({**state, "agent_logs": logs}, "quality", "done", report)
    return {"quality_report": report, "agent_logs": logs}


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
