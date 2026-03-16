from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.backend.services.phase1_service import phase1_service


router = APIRouter(tags=["phase1"])


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


class GenerateWeekRequest(BaseModel):
    start_date: str
    model: Optional[str] = None


class ReviewItemUpdateRequest(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None


class RefineRequest(BaseModel):
    instruction: str
    model: Optional[str] = None


@router.get("/settings")
async def get_settings():
    return phase1_service.get_settings()


@router.put("/settings")
async def update_settings(payload: AppSettingsUpdate):
    updated = phase1_service.update_settings(payload.model_dump(exclude_none=True))
    return updated


@router.get("/settings/test-db")
async def test_database_connection(database_url: Optional[str] = Query(default=None)):
    target_url = database_url or phase1_service.get_settings()["database_url"]
    return phase1_service.test_database_url(target_url)


@router.get("/ollama/models")
async def list_ollama_models(base_url: Optional[str] = Query(default=None)):
    return await phase1_service.list_ollama_models(base_url)


@router.post("/channels")
async def create_channel(payload: ChannelCreateRequest):
    return phase1_service.create_channel(payload.model_dump())


@router.get("/channels")
async def list_channels():
    return phase1_service.list_channels()


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str):
    channel = phase1_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, payload: ChannelUpdateRequest):
    channel = phase1_service.update_channel(channel_id, payload.model_dump(exclude_none=True))
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("/channels/{channel_id}/weekly-template")
async def set_weekly_template(channel_id: str, payload: WeeklyTemplateRequest):
    channel = phase1_service.set_weekly_template(channel_id, payload.weekly_template)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("/channels/{channel_id}/overrides")
async def set_channel_override(channel_id: str, payload: OverrideRequest):
    channel = phase1_service.set_override(
        channel_id,
        payload.date,
        {
            "pillar": payload.pillar,
            "topic": payload.topic,
            "special_instructions": payload.special_instructions,
        },
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("/channels/{channel_id}/generate-week")
async def generate_week(channel_id: str, payload: GenerateWeekRequest):
    generated = await phase1_service.generate_week(channel_id, payload.start_date, payload.model)
    if not generated:
        raise HTTPException(status_code=404, detail="Channel not found or no items generated")
    return generated


@router.get("/review-queue")
async def list_review_queue(channel_id: Optional[str] = Query(default=None)):
    return phase1_service.list_review_items(channel_id)


@router.put("/review-queue/{item_id}")
async def update_review_item(item_id: str, payload: ReviewItemUpdateRequest):
    item = phase1_service.update_review_item(item_id, payload.model_dump(exclude_none=True))
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item


@router.post("/review-queue/{item_id}/refine")
async def refine_review_item(item_id: str, payload: RefineRequest):
    item = await phase1_service.refine_review_item(item_id, payload.instruction, payload.model)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item
