# ContentPilot

ContentPilot is an agentic AI content generation platform that automates research, drafting, and formatting for multiple social channels via a LangGraph multi-agent pipeline.

## 🚀 Features

- **Multi-Agent Pipeline**: 5 specialized AI agents (Research, Summarization, Writer, Formatter, Quality) working in a conditional graph.
- **Dynamic Content Calendar**: Plan full weeks of content using Weekly Templates, with the ability to override specific per-day pillars and topics.
- **Generation Modes**:
  - **Pre-Generated**: AI automatically researches the topic via a local SearXNG engine and drafts the content.
  - **Source Dump**: Skip AI research by providing your own URLs or text notes.
- **Smart Formatting**: Platform-specific formatting engines for Twitter/X (threads), LinkedIn (3000 chars), WhatsApp (markdown conversion), and Telegram (MarkdownV2).
- **Real-Time Progress**: Live SSE (Server-Sent Events) streaming of AI thought processes and pipeline steps.
- **SearXNG Docker Automation**: Start and stop a local, private search engine container directly from the UI.
- **Review Queue**: Edit drafts, refine with AI using a built-in chat interface, and copy-paste ready content.

## 🛠 Tech Stack

- **Backend**: FastAPI, LangGraph, SQLAlchemy, Pydantic, PostgreSQL, httpx, Docker SDK.
- **Frontend**: React, Vite, Tailwind CSS v4.
- **AI Models**: Local LLMs via Ollama.
- **Search Engine**: Local SearXNG via Docker.

## 📦 Quick Start

### 1. Prerequisites

- **PostgreSQL**: Running locally or via Docker. Create a database named `contentpilot`.
- **Ollama**: Running locally (`localhost:11434`) with at least one model pulled (e.g., `llama3` or `mistral`).
- **Docker**: Required to run the SearXNG container for web research.

### 2. Backend Setup

```bash
cd backend
# Create virtal environment and install dependencies
uv venv
uv pip install -r pyproject.toml # or use your preferred package manager
```

Start the backend server (ensure your Postgres DB is accessible):
```bash
uv run uvicorn src.backend.main:app --reload --port 8000
```
*Note: Database configuration and Model selection are now handled dynamically via the Frontend Settings UI.*

### 3. SearXNG Setup
SearXNG is managed automatically by the backend via Docker. You can start/stop it from the Frontend Dashboard or Settings tab. Alternatively, run it manually:
```bash
docker-compose up -d searxng
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (or the port Vite provides) in your browser.

## 📖 How It Works

1. **Configure Settings**: Go to the Settings tab to enter your Postgres URL, select an Ollama model, and ensure the SearXNG container is running.
2. **Create a Channel**: Define your audience, tone, and platform (LinkedIn, Twitter, WhatsApp, etc.).
3. **Set a Weekly Template**: In the Planner tab, set default content pillars (e.g., "Mondays = Concept Deep Dive", "Tuesdays = Tool Spotlight").
4. **Plan & Override**: Use the Calendar to set **Overrides** for specific dates. An Override lets you replace the default weekly pillar with a custom topic or change the generation mode (e.g., to "Source Dump" if you have specific articles to use).
5. **Generate**: Click "Generate Week" to let the LangGraph pipeline process 7 days of content, or generate a single day from the Calendar.
6. **Review**: Check the Review Queue to refine drafts with AI and copy them for publishing.

## 🚧 Development Notes

- **Architecture**: The project uses a layered architecture.
  - `src/backend/api`: FastAPI routes.
  - `src/backend/services`: Core business logic (`content_service.py`, `docker_service.py`).
  - `src/backend/agents`: LangGraph pipeline (`graph.py`).
  - `src/backend/models`: SQLAlchemy definitions.
  - `src/backend/utils`: Formatting engines.
- **Configuration**: Runtime settings are stored in `.contentpilot/settings.json` within the backend directory.

---
*Built with React, FastAPI, and LangGraph.*