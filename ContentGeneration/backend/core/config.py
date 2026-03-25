from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = ""

    OLLAMA_BASE_URL: str = ""
    DEFAULT_OLLAMA_MODEL: str = ""

    SEARXNG_URL: str = ""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ContentPilot"

    class Config:
        case_sensitive = True


settings = Settings()
