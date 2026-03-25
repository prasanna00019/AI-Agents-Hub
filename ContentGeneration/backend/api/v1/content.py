"""
Content API routes for ContentPilot.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from services.content_service import content_service
from services.docker_service import check_services_status, start_services, stop_services
from services.image_service import ImageGenerationError
from services.run_events import cleanup_run_queue, get_run_queue

router = APIRouter(tags=["content"])


class AppSettingsUpdate(BaseModel):
    database_url: Optional[str] = None
    ollama_base_url: Optional[str] = None
    default_ollama_model: Optional[str] = None
    searxng_url: Optional[str] = None
    searxng_categories: Optional[str] = None
    searxng_max_results: Optional[int] = None
    searxng_time_range: Optional[str] = None
    gemini_api_key: Optional[str] = None


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
    context_notes: str = ""


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
    context_notes: Optional[str] = None


class WeeklyTemplateRequest(BaseModel):
    weekly_template: Dict[str, str]


class OverrideRequest(BaseModel):
    date: str
    pillar: str = ""
    topic: str = ""
    special_instructions: str = ""
    mode: str = "pre_generated"
    search_additional: bool = True
    suggest_new_topic: bool = False


class SourceDumpRequest(BaseModel):
    type: str = "text"
    label: str = ""
    raw_content: str
    scraped_content: str = ""


class GenerateDayRequest(BaseModel):
    date: str
    model: Optional[str] = None
    search_additional: bool = True
    suggest_new_topic: bool = False


class GenerateWeekRequest(BaseModel):
    start_date: str
    model: Optional[str] = None


class ReviewItemUpdateRequest(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None


class RefineItemRequest(BaseModel):
    instruction: str
    model: Optional[str] = None


class MemoryCreateRequest(BaseModel):
    type: str = "contextual"
    content: str


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


@router.get("/ollama/models")
async def list_ollama_models(base_url: Optional[str] = Query(default=None)):
    return await content_service.list_ollama_models(base_url)


@router.get("/channels")
async def list_channels():
    return content_service.list_channels()


@router.post("/channels")
async def create_channel(payload: ChannelCreateRequest):
    return content_service.create_channel(payload.model_dump())


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str):
    channel = content_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, payload: ChannelUpdateRequest):
    channel = content_service.update_channel(channel_id, payload.model_dump(exclude_none=True))
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


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


@router.post("/channels/{channel_id}/source-dumps")
async def add_source_dump(channel_id: str, date: str, payload: SourceDumpRequest):
    return content_service.add_source_dump(channel_id, date, payload.model_dump())


@router.get("/channels/{channel_id}/source-dumps")
async def list_source_dumps(channel_id: str, date: str):
    return content_service.list_source_dumps(channel_id, date)


@router.get("/channels/{channel_id}/source-dump-counts")
async def get_source_dump_counts(channel_id: str):
    return content_service.get_source_dump_counts(channel_id)


@router.delete("/channels/{channel_id}/source-dumps/{dump_id}")
async def delete_source_dump(channel_id: str, dump_id: str):
    ok = content_service.delete_source_dump(dump_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Source dump not found")
    return {"ok": True}


@router.post("/channels/{channel_id}/generate-day")
async def generate_day(channel_id: str, payload: GenerateDayRequest):
    try:
        return await content_service.start_day_generation(
            channel_id,
            payload.date,
            payload.model,
            payload.search_additional,
            payload.suggest_new_topic,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/channels/{channel_id}/generate-week")
async def generate_week(channel_id: str, payload: GenerateWeekRequest):
    try:
        return await content_service.generate_week(channel_id, payload.start_date, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/generation/status/{run_id}")
async def get_generation_status(run_id: str):
    run = content_service.get_generation_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/generation/stream/{run_id}")
async def stream_generation(run_id: str):
    async def event_generator():
        queue = get_run_queue(run_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'step': 'timeout', 'status': 'done', 'message': 'Stream timed out'})}\n\n"
                    break

                if event is None:
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
    try:
        result = await content_service.refine_review_item(item_id, payload.instruction, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=500, detail="Refinement failed")
    return result


@router.post("/review-queue/{item_id}/generate-image")
async def generate_review_image(item_id: str):
    try:
        return content_service.generate_review_image(item_id)
    except ImageGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/review-queue/{item_id}/image")
async def get_review_image(item_id: str):
    image = content_service.get_review_image(item_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@router.get("/review-queue/{item_id}/image/download")
async def download_review_image(item_id: str):
    file_info = content_service.get_review_image_file(item_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Image file not found")
    path, mime_type = file_info
    return FileResponse(path, media_type=mime_type, filename=path.name)


@router.get("/channels/{channel_id}/memory")
async def list_channel_memory(channel_id: str, type: Optional[str] = Query(default=None)):
    return content_service.list_memories(channel_id, type)


@router.post("/channels/{channel_id}/memory")
async def add_channel_memory(channel_id: str, payload: MemoryCreateRequest):
    return content_service.add_memory(channel_id, payload.type, payload.content)


@router.delete("/channels/{channel_id}/memory/{memory_id}")
async def delete_channel_memory(channel_id: str, memory_id: str):
    ok = content_service.delete_memory(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


@router.get("/services/status")
async def services_status():
    settings_payload = content_service.get_settings()
    return await check_services_status(settings_payload.get("searxng_url", ""))


@router.post("/services/start")
async def services_start():
    result = await start_services()
    status = await check_services_status(content_service.get_settings().get("searxng_url", ""))
    return {**result, **status}


@router.post("/services/stop")
async def services_stop():
    result = await stop_services()
    status = await check_services_status(content_service.get_settings().get("searxng_url", ""))
    return {**result, **status}
