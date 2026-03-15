import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/contentpilot"

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_OLLAMA_MODEL: str = "llama3.1:8b"

    # Redis settings for Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # SearXNG settings
    SEARXNG_URL: str = "http://localhost:8080"

    # Application settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ContentPilot"

    class Config:
        case_sensitive = True


settings = Settings()