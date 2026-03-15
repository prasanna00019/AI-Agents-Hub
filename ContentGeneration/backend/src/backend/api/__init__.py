from fastapi import APIRouter

from .v1.channels import router as channels_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(channels_router)