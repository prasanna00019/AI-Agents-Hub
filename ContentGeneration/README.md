# ContentPilot

An agentic content generation platform that runs 100% locally, designed to automate content creation for your channels without sending any data to third-party clouds.

## Project Status

This project is currently under active development. Below is what has been implemented so far:

### ✅ Completed Components

#### Backend Infrastructure
- Docker Compose setup with PostgreSQL, Redis, and SearXNG services
- FastAPI backend with proper project structure
- Basic database models for core entities (Users, Channels, etc.)
- Alembic for database migrations
- Configuration management with environment variables

#### Backend Structure
```
backend/
├── src/
│   ├── backend/
│   │   ├── agents/          # AI agent implementations
│   │   ├── api/             # FastAPI routers and endpoints
│   │   ├── core/            # Core configurations and settings
│   │   ├── db/              # Database connection and setup
│   │   ├── models/          # Database models and Pydantic schemas
│   │   ├── services/        # Business logic services
│   │   ├── utils/           # Utility functions
│   │   └── main.py          # Main application entry point
├── alembic/                 # Database migrations
├── pyproject.toml           # Project dependencies and metadata
└── requirements.txt         # Alternative dependency management
```

#### Frontend
- Basic React/Vite setup with Tailwind CSS
- Placeholder UI components

#### Infrastructure
- Docker Compose configuration for local development
- PostgreSQL with pgvector extension support
- Redis for task queuing
- SearXNG for private search capabilities

### 🚧 In Progress

#### Backend Development
- LangGraph agent implementation for content generation pipeline
- Full database model implementation based on IDEA.md specifications
- API endpoints for channel management and content generation
- Integration with Ollama for local LLM processing

### 🔜 Planned Features

#### MVP Scope (Phase 1)
- [ ] Complete database models for all entities in IDEA.md
- [ ] LangGraph agent pipeline implementation:
  - Research Agent (searches SearXNG + configured sources)
  - Summarization Agent (condenses raw content)
  - Writer Agent (generates post drafts)
  - Formatter Agent (applies platform-specific formatting)
  - Quality Agent (checks tone consistency, repetition, length)
- [ ] Weekly template setup and per-day slot overrides
- [ ] Pre-generated content mode implementation
- [ ] WhatsApp formatter with copy-to-clipboard functionality
- [ ] Review queue with inline editing and refinement chat

#### Future Enhancements
- [ ] Source-dump generation pipeline for time-sensitive content
- [ ] Episodic memory via pgvector to avoid content repetition
- [ ] Preference memory from edit and refinement history
- [ ] Multi-channel support
- [ ] Additional platform formatters (Telegram, LinkedIn, Email)

## Technology Stack

### Backend
- **Runtime:** Python (FastAPI) with async support
- **Database:** PostgreSQL with pgvector extension
- **Task Queue:** Celery + Redis
- **LLM Orchestration:** LangGraph for stateful multi-agent pipelines
- **Search:** SearXNG (self-hosted metasearch)
- **Web Scraping:** Playwright (local headless browser)

### AI / LLM
- **LLM:** Ollama (runs models like Llama 3, Mistral, Gemma, Qwen locally)
- **Embeddings:** Ollama embedding models (nomic-embed-text, mxbai-embed-large)
- **Zero external AI calls** - all requests go to localhost

### Frontend
- **Framework:** Next.js (React) with TypeScript
- **UI Library:** shadcn/ui + Tailwind CSS
- **Real-time Agent Logs:** Server-Sent Events (SSE)

### Infrastructure
- **Containerization:** Docker Compose for easy setup
- **Authentication:** Local username + hashed password
- **Storage:** Docker volumes for persistent data

## Local Development Setup

1. Ensure you have Docker and Docker Compose installed
2. Run `docker-compose up` to start all services
3. The backend will be available at http://localhost:8000
4. The frontend will be available at http://localhost:3000

## Architecture Overview

ContentPilot implements two distinct content generation modes:

### Pre-Generated Mode (Evergreen Content)
```
[Trigger] → [Research Agent] → [Summarization Agent] → [Writer Agent] → [Formatter Agent] → [Quality Agent] → [Review Queue]
```

### Source-Dump Mode (Time-Sensitive Content)
```
[User builds source inbox over time] → [Trigger] → [Summarization Agent] → [Writer Agent] → [Formatter Agent] → [Review Queue]
```

For detailed information about the platform concepts, architecture, and features, see [IDEA.md](IDEA.md).