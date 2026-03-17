"""
ContentPilot LangGraph — Multi-Agent Pipeline

Agents:
  1. Research     — Search SearXNG / scrape sources (skipped in source_dump mode)
  2. Summarize    — Condense raw material into structured context
  3. Writer       — Generate polished post draft using Ollama
  4. Formatter    — Apply platform-specific formatting rules
  5. Quality      — Tone check, length check, repetition guard

Graph routing:
  - pre_generated → research → summarize → writer → formatter → quality → END
  - source_dump   → summarize → writer → formatter → quality → END
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END
import httpx

from src.backend.utils.formatting import format_for_platform


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """State passed across all nodes."""
    channel: Dict[str, Any]
    item_date: str
    pillar: str
    topic: str
    special_instructions: str
    mode: str  # pre_generated | source_dump
    raw_sources: List[str]
    scraped_data: str
    summarized_context: str
    draft: str
    formatted_content: str
    quality_report: str
    error: str
    # Dynamic settings
    model: Optional[str]
    ollama_base_url: Optional[str]
    searx_url: Optional[str]
    # Agent step logs (appended by each node)
    agent_logs: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(state: AgentState, step: str, status: str, message: str = "") -> List[Dict[str, Any]]:
    logs = list(state.get("agent_logs") or [])
    logs.append({
        "step": step,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    })
    return logs


def _ollama_url(state: AgentState) -> str:
    return (state.get("ollama_base_url") or "").rstrip("/")


def _model_name(state: AgentState) -> str:
    return state.get("model") or ""


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
# Router
# ---------------------------------------------------------------------------

def route_by_mode(state: AgentState) -> str:
    """Skip research for source_dump mode."""
    if state.get("mode") == "source_dump":
        return "summarize"
    return "research"


# ---------------------------------------------------------------------------
# Node 1 — Research
# ---------------------------------------------------------------------------

async def research_node(state: AgentState) -> Dict[str, Any]:
    logs = _log(state, "research", "running", "Searching sources via SearXNG…")
    scraped_data = ""
    searx_url = (state.get("searx_url") or "").rstrip("/")
    queries = state.get("raw_sources") or [state.get("topic", "")]
    logs = _log({**state, "agent_logs": logs}, "research", "running", f"Searching URLs for queries: {', '.join(queries[:3])}...")

    scraped_chunks: list[str] = []
    if searx_url:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for query in queries[:5]:
                try:
                    resp = await client.get(
                        f"{searx_url}/search",
                        params={"q": query, "format": "json"},
                    )
                    if resp.status_code == 200:
                        results = resp.json().get("results", [])
                        for r in results[:4]:
                            title = r.get("title", "")
                            snippet = r.get("content") or r.get("snippet", "")
                            url = r.get("url", "")
                            scraped_chunks.append(
                                f"**{title}**\n{snippet}\nSource: {url}"
                            )
                except Exception as e:
                    logs = _log(
                        {**state, "agent_logs": logs},
                        "research", "warning", f"Query failed: {e}",
                    )

    scraped_data = "\n\n---\n\n".join(scraped_chunks) if scraped_chunks else ""
    
    # Extract just the URLs for the log message
    found_urls = []
    for chunk in scraped_chunks:
        lines = chunk.split("\n")
        if lines and lines[-1].startswith("Source: "):
            found_urls.append(lines[-1].replace("Source: ", ""))

    logs = _log(
        {**state, "agent_logs": logs},
        "research", "done",
        f"Found {len(scraped_chunks)} results. Sources: {', '.join(found_urls)}" if found_urls else "No results found."
    )
    return {"scraped_data": scraped_data, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Node 2 — Summarization
# ---------------------------------------------------------------------------

async def summarize_node(state: AgentState) -> Dict[str, Any]:
    logs = _log(state, "summarize", "running", "Condensing raw material…")

    # Gather raw text
    if state.get("mode") == "source_dump":
        raw = "\n\n---\n\n".join(state.get("raw_sources") or [])
    else:
        raw = state.get("scraped_data", "")

    if not raw.strip():
        logs = _log(
            {**state, "agent_logs": logs},
            "summarize", "done", "No source material — passing topic directly.",
        )
        return {
            "summarized_context": f"Topic: {state.get('topic', '')}",
            "agent_logs": logs,
        }

    # Apply RAG if text is large
    if len(raw) > 4000:
        logs = _log({**state, "agent_logs": logs}, "summarize", "running", f"Text too large ({len(raw)} chars). Applying RAG extraction…")
        try:
            import asyncio
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_chroma import Chroma
            from langchain_core.documents import Document

            def _run_rag() -> str:
                # Split text
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                docs = [Document(page_content=raw)]
                splits = text_splitter.split_documents(docs)
                
                # Create ephemeral vector store
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
                
                # Retrieve relevant chunks
                retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
                query = state.get("topic") or state.get("pillar") or "Main points"
                retrieved_docs = retriever.invoke(query)
                
                return "\n\n".join(d.page_content for d in retrieved_docs)

            raw_to_summarize = await asyncio.to_thread(_run_rag)
            logs = _log({**state, "agent_logs": logs}, "summarize", "running", "RAG extraction complete. Summarizing relevant chunks…")
        except Exception as e:
            logs = _log({**state, "agent_logs": logs}, "summarize", "warning", f"RAG failed: {e}. Falling back to truncation.")
            raw_to_summarize = raw
    else:
        raw_to_summarize = raw

    prompt = (
        "You are a research summarizer. Condense the following raw material into "
        "a structured, concise brief that a content writer can use.\n"
        "Keep key facts, statistics, and quotes. Remove redundancy.\n\n"
        f"--- RAW MATERIAL ---\n{raw_to_summarize[:8000]}\n\n"
        "Output a structured summary with bullet points."
    )

    try:
        summary = await _ollama_generate(_ollama_url(state), _model_name(state), prompt)
    except Exception as e:
        summary = f"Summarization failed: {e}. Using raw material."
        logs = _log({**state, "agent_logs": logs}, "summarize", "warning", str(e))

    logs = _log(
        {**state, "agent_logs": logs},
        "summarize", "done",
        f"Produced {len(summary)} char summary",
    )
    return {"summarized_context": summary, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Node 3 — Writer
# ---------------------------------------------------------------------------

async def writer_node(state: AgentState) -> Dict[str, Any]:
    logs = _log(state, "writer", "running", "Generating draft with Ollama…")

    channel = state.get("channel", {})
    context = state.get("summarized_context") or state.get("scraped_data", "")

    prompt = (
        f"You are an expert content writer for the channel '{channel.get('name')}'.\n"
        f"Platform: {channel.get('platform')}\n"
        f"Target audience: {channel.get('audience')}\n"
        f"Tone \u0026 voice: {channel.get('tone')}\n"
        f"Content pillar: {state.get('pillar')}\n"
        f"Topic: {state.get('topic')}\n\n"
        f"--- RESEARCH CONTEXT ---\n{context[:5000]}\n\n"
    )
    if state.get("special_instructions"):
        prompt += f"Special instructions: {state['special_instructions']}\n"
    if channel.get("prompt_template"):
        prompt += f"Channel prompt template: {channel['prompt_template']}\n"
    prompt += (
        "\nWrite ONE polished, highly engaging post ready for copy-paste publishing. "
        "Do NOT include any meta-commentary.\n\n"
        "IMPORTANT ANTI-HALLUCINATION RULES:\n"
        "1. Do NOT invent or make up any sources, facts, or URLs.\n"
        "2. ONLY use the information explicitly provided in the RESEARCH CONTEXT above.\n"
        "3. If the context contains real source URLs, you MUST cite them at the end "
        "of the post in a 'Sources:' section. If NO URLs are provided, DO NOT include "
        "a sources section at all."
    )

    try:
        draft = await _ollama_generate(_ollama_url(state), _model_name(state), prompt)
    except Exception as e:
        draft = f"Error generating content: {e}"

    logs = _log(
        {**state, "agent_logs": logs},
        "writer", "done",
        f"Draft generated ({len(draft)} chars)",
    )
    return {"draft": draft, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Node 4 — Formatter
# ---------------------------------------------------------------------------

async def formatter_node(state: AgentState) -> Dict[str, Any]:
    logs = _log(state, "formatter", "running", "Applying platform formatting…")
    draft = state.get("draft", "")
    platform = state.get("channel", {}).get("platform", "whatsapp")

    if draft.startswith("Error"):
        return {"formatted_content": draft, "agent_logs": _log(
            {**state, "agent_logs": logs}, "formatter", "done", "Skipped (error in draft)"
        )}

    formatted = format_for_platform(draft, platform)
    logs = _log(
        {**state, "agent_logs": logs},
        "formatter", "done",
        f"Formatted for {platform} ({len(formatted)} chars)",
    )
    return {"formatted_content": formatted, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Node 5 — Quality Check
# ---------------------------------------------------------------------------

async def quality_node(state: AgentState) -> Dict[str, Any]:
    logs = _log(state, "quality", "running", "Running quality checks…")
    formatted = state.get("formatted_content", "")
    channel = state.get("channel", {})
    platform = channel.get("platform", "whatsapp")

    issues: list[str] = []

    # Length checks
    limits = {
        "whatsapp": 4000,
        "twitter": 280,
        "linkedin": 3000,
        "telegram": 4096,
    }
    limit = limits.get(platform, 5000)
    if len(formatted) > limit:
        issues.append(f"Content exceeds {platform} limit: {len(formatted)}/{limit} chars")

    # Tone check (basic heuristic)
    tone = channel.get("tone", "").lower()
    if tone == "professional" and formatted.count("!") > 5:
        issues.append("Too many exclamation marks for professional tone")

    report = "; ".join(issues) if issues else "All checks passed"
    logs = _log(
        {**state, "agent_logs": logs},
        "quality", "done", report,
    )
    return {"quality_report": report, "agent_logs": logs}


# ---------------------------------------------------------------------------
# Build Graph
# ---------------------------------------------------------------------------

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("research", research_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("formatter", formatter_node)
    workflow.add_node("quality", quality_node)

    # Entry: conditional routing based on mode
    workflow.set_conditional_entry_point(route_by_mode, {
        "research": "research",
        "summarize": "summarize",
    })

    workflow.add_edge("research", "summarize")
    workflow.add_edge("summarize", "writer")
    workflow.add_edge("writer", "formatter")
    workflow.add_edge("formatter", "quality")
    workflow.add_edge("quality", END)

    return workflow.compile()


content_graph = build_graph()
