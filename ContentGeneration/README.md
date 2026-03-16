# ContentPilot

ContentPilot is a local-first content generation platform. The full product vision is documented in `IDEA.md`.

This repository is currently configured for a **simple prototype flow**:
- FastAPI backend
- React + Vite frontend
- PostgreSQL running on your machine (no Postgres Docker service)
- No Redis and no Alembic migration workflow for now

## Quick Start (Prototype Mode)

## 1. Start PostgreSQL locally
Use your local Postgres instance (for example via pgAdmin).

Make sure this database exists:
- `contentpilot`

## 2. Run backend

```bash
cd backend
pip install -r requirements.txt
set DATABASE_URL=postgresql://postgres:password@localhost:5432/contentpilot
uvicorn src.backend.main:app --reload --port 8000
```

## 3. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open the frontend URL shown by Vite (usually `http://localhost:5173`).

The homepage will call `GET /health` from the backend and show live connection status.

## Optional Docker (Backend + Frontend + SearXNG)

If you want, you can still run these services through Docker Compose:

```bash
docker-compose up --build
```

In this mode, backend uses:
- `DATABASE_URL=postgresql://postgres:password@host.docker.internal:5432/contentpilot`

## Notes

- Keep this branch simple while validating the UI/API prototype.
- Redis, Celery, and Alembic can be added back later when async jobs and migration workflows are needed.