from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import api_router
from core.config import settings
from services.content_service import content_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for ContentPilot - Agentic Content Generation Platform",
    version="0.1.0",
)

DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    content_service.initialize_storage()

@app.get("/")
async def root():
    return {"message": "Welcome to ContentPilot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
