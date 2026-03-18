# ContentPilot

ContentPilot is a local-first, agentic content generation platform for planning, generating, formatting, and reviewing social content across multiple channels.

## Overview

- Multi-agent pipeline using LangGraph (Research, Summarize, Writer, Formatter, Quality).
- Weekly planning with calendar-level date overrides.
- Two generation modes:
  - Pre-generated research mode (web research through SearXNG).
  - Source dump mode (user-provided URLs/notes).
- Platform-aware output formatting (LinkedIn, Twitter/X, WhatsApp, Telegram).
- Real-time generation progress via SSE streams.
- Review queue with edit and refinement workflow.

## Current Tech Stack

- Backend: FastAPI, LangGraph, SQLAlchemy, Pydantic, PostgreSQL, httpx.
- Frontend: React + Vite.
- AI runtime: Ollama (local model serving).
- Search: SearXNG (Docker).

## Repository Layout

- `backend/`: FastAPI app, LangGraph agents, services, data models.
- `frontend/`: React app and UI components.
- `docker-compose.yml`: Local multi-service setup.
- `init-scripts/`: startup scripts (including pgvector init helper).

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (database: `contentpilot`)
- Ollama running locally
- Docker (for SearXNG)

### 2. Start Backend

```bash
cd backend
uv sync
uvicorn src.backend.main:app --reload --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Optional: Start SearXNG Manually

```bash
docker-compose up -d searxng
```

Open the frontend on the URL printed by Vite (typically `http://localhost:5173`).

## How the Flow Works

1. Configure runtime settings from the app.
2. Create or select a channel profile.
3. Plan content in weekly templates and date-level overrides.
4. Generate content for a day or week.
5. Review, refine, and export platform-ready output.

## IDE Memory MCP

This project can be used with IDE Memory MCP to persist task context, decisions, and progress across coding sessions.

- Initialize project memory before work with `init_project`.
- Read focused sections like `overview`, `decisions`, and `active_context` to restore context quickly.
- Write important updates (architecture changes, feature decisions, migration notes) as you progress.

For more details, refer to IDE Memory MCP docs and your workspace memory sections under `/memories`.

## Notes

- Backend and frontend include their own focused READMEs in `backend/README.md` and `frontend/README.md`.
- Keep root README high-level; place service-specific operational details in subfolder docs.