from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api import api_router
from src.backend.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for ContentPilot - Agentic Content Generation Platform",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to ContentPilot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}