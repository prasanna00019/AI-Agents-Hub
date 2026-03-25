from fastapi import APIRouter

from .v1.content import router as content_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(content_router)