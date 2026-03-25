# Video2Notes Agent

Video2Notes turns long videos, uploaded media files, and selected playlist items into structured notes, searchable saved entries, and optional study material.

It can run as a fully local and privacy-friendly workflow when you use Ollama, local Whisper, and FFmpeg on your own machine.

That means you can keep transcription, note generation, and media processing on your system without sending your content to external cloud APIs.

![Home page](images/home_page_2.PNG)

## What It Does

Video2Notes processes a source through extraction, transcription, chunk analysis, structuring, synthesis, optional study-asset generation, persistence, and RAG indexing.

Major capabilities:
- Fully local/private workflow with Ollama + local Whisper + FFmpeg
- Unified intake for URL, Google Drive shared video files, upload, and playlists
- Playlist preview before execution, with per-video selection
- Playlist processing in parallel or one-by-one
- Multiple note styles:
  `study_notes`, `executive_summary`, `meeting_notes`, `tutorial_breakdown`, `actionable_checklist`, `revision_notes`
- Custom prompt template layered on top of the selected note style
- Optional study assets:
  flashcards, quiz, glossary, revision sheet
- Saved-note browser with collections and grouped playlist runs
- Hybrid saved-note search:
  BM25 + vector similarity fallback-aware ranking
- Hierarchical RAG retrieval with reranking for chat over saved notes
- Selective exports:
  notes only by default, with optional description and study assets
- App-wide theme switching

## It Now Supports

- Single video URLs
- Google Drive shared video-file links
- Local audio/video uploads
- YouTube playlist preview plus `all` or `selected` processing
- Parallel or sequential playlist execution with configurable workers
- Note styles plus custom prompt templates
- Optional study-asset generation
- Saved notes, collections, grouped playlist runs, and hybrid library search
- Transcript reuse, live task streaming, exports, themes, and RAG chat on reopened notes

## Screens

### Source Intake
Use a video URL, playlist URL, Google Drive shared video link, or local upload.

![Source input](images/source.PNG)

### Runtime Settings
Choose provider, Whisper settings, detail level, note style, custom prompt, study-asset toggle, database connection, and playlist execution mode.

![Settings modal](images/settings.PNG)

### Library
Saved notes live in the Library with collections, grouped playlist runs, and modal-based browsing.

![Library](images/library.PNG)

### Saved Notes Browser
The saved-notes list opens in a dedicated modal with hybrid search and filtering.

![Saved notes browser](images/saved_notes_2.PNG)

## Architecture Overview

```text
Source
  -> Extraction / Download
  -> Whisper transcription
  -> Chunk analysis
  -> Section structuring + deduplication
  -> Final note synthesis
  -> Optional study-asset generation
  -> Transcript + note caching
  -> Saved-note indexing
  -> Hierarchical RAG chat
```

Backend:
- FastAPI
- SQLAlchemy
- Postgres for saved notes and collections
- ChromaDB for retrieval storage

Frontend:
- React
- React Router
- Tailwind CSS v4
- Theme-aware UI with modal workflows

Models and providers:
- Gemini / Anthropic / Ollama for note synthesis and analysis
- Local Whisper or Groq Whisper for transcription
- Sentence Transformers for hybrid search and reranking when available

## Requirements

- Python `>= 3.13`
- Node.js `>= 20` recommended
- `uv`
- `npm`
- `ffmpeg`

Optional but recommended:
- Postgres
- Ollama
- Hugging Face token for smoother local model downloads

## Install FFmpeg

Video2Notes needs `ffmpeg` for extraction and media conversion.

### Windows

Using `winget`:

```powershell
winget install Gyan.FFmpeg
```

Using Chocolatey:

```powershell
choco install ffmpeg
```

### macOS

```bash
brew install ffmpeg
```

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

Verify:

```bash
ffmpeg -version
```

## Install the Project

### 1. Install Python Dependencies

```bash
uv sync
```

This installs the backend dependencies, including:
- FastAPI
- faster-whisper
- openai-whisper
- litellm
- chromadb
- psycopg2-binary
- sentence-transformers
- yt-dlp

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Local Whisper and Hugging Face Setup

If you choose `Local Whisper` in the UI, the selected Whisper model is downloaded on first use.

You do not need a separate manual Whisper install beyond:

```bash
uv sync
```

Optional environment variable:

```bash
HF_TOKEN=hf_...
```

Why it helps:
- faster access to Hugging Face-hosted model downloads
- useful when rate limits or gated downloads apply

### Optional: Pre-download a Whisper Model

Example for `base`:

```bash
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu')"
```

Example for `tiny`:

```bash
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu')"
```

If you want faster first-run behavior, pre-download the model you plan to use most often.

## Optional Service Setup

### Gemini

```bash
GEMINI_API_KEY=AIza...
```

### Anthropic

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Groq Whisper

```bash
GROQ_API_KEY=gsk_...
```

### Ollama

Make sure Ollama is installed and running:

```bash
ollama serve
```

Then pull a model you want to use:

```bash
ollama pull gpt-oss:120b-cloud
```

The UI also lets you enter a different model name and base URL.

### Postgres

Postgres is optional for generation, but required for:
- saved notes
- collections
- transcript reuse across runs
- reopening notes
- library search

Example connection string:

```bash
postgresql://user:password@host:5432/database
```

You can paste the database URL directly into the settings UI.

## Run the App

### Backend

```bash
uv run uvicorn api:app --reload
```

Backend default:
- `http://localhost:8000`

### Frontend

```bash
cd frontend
npm run dev
```

Frontend default:
- `http://localhost:5173`

## Current Workflow

### 1. Choose a Source

Supported source types:
- YouTube video URL
- YouTube playlist URL
- Google Drive shared video file
- Local upload

Notes:
- Google Drive support is for shared video files only
- Playlist support is for YouTube playlists

### 2. Configure Runtime Settings

Available settings include:
- provider
- whisper provider and model
- language
- detail level
- note style
- custom prompt template
- timestamps
- keep QA
- keep examples
- generate study assets
- Postgres database URL
- playlist execution mode
- playlist worker count

### 3. Generate

The app streams progress across:
- extraction
- transcription
- analysis
- structuring
- synthesis
- optional study assets
- RAG
- export-ready completion

### 4. Review the Result

Result pages include:
- final notes
- applied settings
- optional study-asset modal
- export controls
- chat with saved-note context

### 5. Save and Reopen

With Postgres configured, the app stores:
- notes
- transcript cache
- note metadata
- optional study assets
- playlist grouping metadata
- collections

## Library and Search

The Library now supports:
- saved-note browser modal
- grouped playlist runs
- collections
- reopen note into a full workspace
- hybrid search

Hybrid search uses:
- BM25-style keyword scoring
- vector similarity when sentence-transformers is available

If the vector model cannot load in the local environment, the app falls back gracefully to BM25-only ranking.

## RAG Chat

Saved notes can be reopened into a note workspace with chat enabled.

RAG behavior:
- parent-child hierarchical retrieval
- vector retrieval over structured sections and note chunks
- Hugging Face cross-encoder reranking when available
- fallback behavior when reranker dependencies are unavailable

## Exports

Supported formats:
- `pdf`
- `docx`
- `html`
- `markdown_notion`
- `markdown_obsidian`

Supported templates:
- `default`
- `academic`

Selectable export content:
- notes
- video description
- study assets

Default export behavior:
- notes only

## Themes

The UI includes multiple built-in themes and persists the user’s theme selection locally.

## API Overview

Main endpoints:
- `POST /api/process`
- `POST /api/process/upload`
- `POST /api/process/playlist/preview`
- `POST /api/process/playlist`
- `GET /api/status/{task_id}`
- `GET /api/tasks/{task_id}/events`
- `GET /api/batches/{batch_id}`
- `GET /api/batches/{batch_id}/events`
- `POST /api/batches/{batch_id}/tasks/{task_id}/retry`
- `GET /api/notes`
- `POST /api/notes/{note_id}/open`
- `PATCH /api/notes/{note_id}`
- `GET /api/collections`
- `POST /api/collections`
- `PATCH /api/collections/{collection_id}`
- `DELETE /api/collections/{collection_id}`
- `POST /api/export`
- `GET /api/ollama/models`
- `POST /api/chat`

## Testing

Backend checks:

```bash
python -m unittest test_enhancements.py
python -m py_compile api.py config.py synthesizer.py hybrid_search.py
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Manual test checklist:
- see [testing_suite.md](testing_suite.md)

## Troubleshooting

### FFmpeg Not Found

Symptom:
- extraction or media conversion fails

Fix:
- install FFmpeg
- make sure it is on your `PATH`
- verify with `ffmpeg -version`

### Local Whisper Download Problems

Symptom:
- first local transcription run hangs or fails while downloading

Fix:
- set `HF_TOKEN`
- pre-download the model with the `WhisperModel(...)` command above
- retry with a smaller model like `tiny` or `base`

### No Saved Notes / Collections

Symptom:
- generation works but library features do not

Fix:
- supply a valid Postgres connection string in settings

### Frontend Build Issue on Some Windows Setups

Symptom:
- `npm run build` fails around Tailwind native dependencies such as `@tailwindcss/oxide` or `lightningcss`

Fix:
- reinstall frontend dependencies
- clear `node_modules` and lockfiles if needed
- ensure your local Node environment is healthy

This is an environment/setup issue, not part of the core Video2Notes workflow.

## Notes

- Study assets are optional and only generated when enabled
- Playlist items are stored per video and shown as grouped playlist runs in the Library
- Prompt settings are logged in the terminal so you can verify the applied synthesis prompt
- Playlist execution settings are also logged, including mode and worker count
