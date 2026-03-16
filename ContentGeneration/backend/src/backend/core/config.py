from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:radha@localhost:6739/CONTENT"

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_OLLAMA_MODEL: str = "llama3.1:8b"

    # SearXNG settings
    SEARXNG_URL: str = "http://localhost:8080"

    # Application settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ContentPilot"

    class Config:
        case_sensitive = True


settings = Settings()