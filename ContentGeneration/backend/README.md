# ContentPilot Backend

This is the backend for ContentPilot, an agentic content generation platform that runs 100% locally.

## Structure

- `api/` - FastAPI routers and endpoints
- `core/` - Core configurations and settings
- `models/` - Database models and schemas
- `services/` - Business logic services
- `utils/` - Utility functions
- `agents/` - AI agent implementations
- `db/` - Database connection and setup

## Development

Install dependencies with uv:

```bash
uv sync
```

Run the development server:

```bash
uv run uvicorn src.backend.main:app --reload
```