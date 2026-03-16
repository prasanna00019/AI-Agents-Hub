from fastapi import APIRouter

from .v1.phase1 import router as phase1_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(phase1_router)