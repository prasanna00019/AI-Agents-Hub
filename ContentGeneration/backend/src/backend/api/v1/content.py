"""
Content API — all REST endpoints for ContentPilot.

Includes: settings, channels, source dumps, generation, review queue,
SearXNG Docker control, and SSE streaming.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.backend.services.content_service import content_service, get_run_queue, cleanup_run_queue
from src.backend.services.docker_service import (
    check_searxng_status,
    start_searxng,
    stop_searxng,
)

import json

router = APIRouter(tags=["content"])


# ── Pydantic models ──────────────────────────────────────────────────────

class AppSettingsUpdate(BaseModel):
    database_url: Optional[str] = None
    ollama_base_url: Optional[str] = None
    default_ollama_model: Optional[str] = None
    searxng_url: Optional[str] = None


class ChannelCreateRequest(BaseModel):
    name: str
    description: str = ""
    audience: str = ""
    tone: str = "Educational"
    platform: str = "whatsapp"
    language: str = "en"
    timezone: str = "UTC"
    sources: List[str] = Field(default_factory=list)
    prompt_template: str = ""
    weekly_template: Dict[str, str] = Field(default_factory=dict)
    overrides: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class ChannelUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    platform: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    sources: Optional[List[str]] = None
    prompt_template: Optional[str] = None


class WeeklyTemplateRequest(BaseModel):
    weekly_template: Dict[str, str]


class OverrideRequest(BaseModel):
    date: str
    pillar: str = ""
    topic: str = ""
    special_instructions: str = ""
    mode: str = "pre_generated"


class SourceDumpRequest(BaseModel):
    type: str = "text"
    label: str = ""
    raw_content: str
    scraped_content: str = ""


class GenerateDayRequest(BaseModel):
    date: str
    model: Optional[str] = None


class GenerateWeekRequest(BaseModel):
    start_date: str
    model: Optional[str] = None


class ReviewItemUpdateRequest(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None


class RefineItemRequest(BaseModel):
    instruction: str
    model: Optional[str] = None


# ── Settings ──────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings():
    return content_service.get_settings()


@router.put("/settings")
async def update_settings(payload: AppSettingsUpdate):
    return content_service.update_settings(payload.model_dump(exclude_none=True))


@router.get("/settings/test-db")
async def test_database_connection(database_url: Optional[str] = Query(default=None)):
    target = database_url or content_service.get_settings()["database_url"]
    return content_service.test_database_url(target)


# ── Ollama ────────────────────────────────────────────────────────────────

@router.get("/ollama/models")
async def list_ollama_models(base_url: Optional[str] = Query(default=None)):
    return await content_service.list_ollama_models(base_url)


# ── Channels ──────────────────────────────────────────────────────────────

@router.get("/channels")
async def list_channels():
    return content_service.list_channels()


@router.post("/channels")
async def create_channel(payload: ChannelCreateRequest):
    return content_service.create_channel(payload.model_dump())


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str):
    ch = content_service.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ch


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, payload: ChannelUpdateRequest):
    ch = content_service.update_channel(channel_id, payload.model_dump(exclude_none=True))
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ch


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    ok = content_service.delete_channel(channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"ok": True}


@router.post("/channels/{channel_id}/weekly-template")
async def set_weekly_template(channel_id: str, payload: WeeklyTemplateRequest):
    return content_service.set_weekly_template(channel_id, payload.weekly_template)


@router.post("/channels/{channel_id}/overrides")
async def set_channel_override(channel_id: str, payload: OverrideRequest):
    return content_service.set_override(channel_id, payload.date, payload.model_dump())


# ── Source Dumps ──────────────────────────────────────────────────────────

@router.post("/channels/{channel_id}/source-dumps")
async def add_source_dump(channel_id: str, date: str, payload: SourceDumpRequest):
    return content_service.add_source_dump(channel_id, date, payload.model_dump())


@router.get("/channels/{channel_id}/source-dumps")
async def list_source_dumps(channel_id: str, date: str):
    return content_service.list_source_dumps(channel_id, date)


@router.delete("/channels/{channel_id}/source-dumps/{dump_id}")
async def delete_source_dump(channel_id: str, dump_id: str):
    ok = content_service.delete_source_dump(dump_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Source dump not found")
    return {"ok": True}


# ── Generation ────────────────────────────────────────────────────────────

@router.post("/channels/{channel_id}/generate-day")
async def generate_day(channel_id: str, payload: GenerateDayRequest):
    """Synchronous single-day generation (returns when complete)."""
    try:
        return await content_service.generate_day(channel_id, payload.date, payload.model)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/channels/{channel_id}/generate-week")
async def generate_week(channel_id: str, payload: GenerateWeekRequest):
    """Async week generation — returns immediately with run_id."""
    return await content_service.generate_week(channel_id, payload.start_date, payload.model)


@router.get("/generation/status/{run_id}")
async def get_generation_status(run_id: str):
    """Poll the status of a generation run."""
    run = content_service.get_generation_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ── SSE Streaming ─────────────────────────────────────────────────────────

@router.get("/generation/stream/{run_id}")
async def stream_generation(run_id: str):
    """Server-Sent Events stream for real-time generation progress."""

    async def event_generator():
        q = get_run_queue(run_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'step': 'timeout', 'status': 'done', 'message': 'Stream timed out'})}\n\n"
                    break

                if event is None:  # End of stream signal
                    yield f"data: {json.dumps({'step': 'pipeline', 'status': 'done', 'message': 'Generation complete'})}\n\n"
                    break

                yield f"data: {json.dumps(event)}\n\n"
        finally:
            cleanup_run_queue(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Review Queue ──────────────────────────────────────────────────────────

@router.get("/review-queue")
async def list_review_queue(channel_id: Optional[str] = Query(default=None)):
    return content_service.list_review_items(channel_id)


@router.put("/review-queue/{item_id}")
async def update_review_item(item_id: str, payload: ReviewItemUpdateRequest):
    return content_service.update_review_item(item_id, payload.model_dump(exclude_none=True))


@router.delete("/review-queue/{item_id}")
async def delete_review_item(item_id: str):
    ok = content_service.delete_review_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Review item not found")
    return {"ok": True}


@router.post("/review-queue/{item_id}/refine")
async def refine_review_item(item_id: str, payload: RefineItemRequest):
    result = await content_service.refine_review_item(item_id, payload.instruction, payload.model)
    if not result:
        raise HTTPException(status_code=500, detail="Refinement failed")
    return result


# ── SearXNG Docker Control ───────────────────────────────────────────────

@router.get("/searxng/status")
async def searxng_status():
    return await check_searxng_status()


@router.post("/searxng/start")
async def searxng_start():
    return await start_searxng()


@router.post("/searxng/stop")
async def searxng_stop():
    return await stop_searxng()
