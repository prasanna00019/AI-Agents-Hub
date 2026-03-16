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

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your local database URL (PowerShell):

```bash
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/contentpilot"
```

Run the development server:

```bash
uvicorn src.backend.main:app --reload --port 8000
```

## Current Scope

- PostgreSQL connection only (local instance)
- No Redis/Celery runtime
- No Alembic migration workflow