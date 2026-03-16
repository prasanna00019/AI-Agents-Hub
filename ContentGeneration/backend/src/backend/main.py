from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api import api_router
from src.backend.core.config import settings
from src.backend.services.content_service import content_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for ContentPilot - Agentic Content Generation Platform",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
      "*"
    ],
    allow_credentials=True,
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