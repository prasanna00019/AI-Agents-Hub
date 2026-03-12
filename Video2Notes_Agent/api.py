import os
import hashlib
import json
import uuid
from typing import Optional, Dict
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import dotenv

from config import Config
from extractor import AudioExtractor
from transcriber import WhisperTranscriber
from analyzer import ChunkAnalyzer
from synthesizer import NotesSynthesizer
from rag_engine import VideoRAGEngine
from database import VideoNoteCache, get_database_url, get_session_factory, init_db

dotenv.load_dotenv()
init_db()

app = FastAPI(title="VideoNotes API")

# Setup CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for task states (for simplicity in this phase)
# Format: { task_id: {"status": "processing/completed/error", "progress": "...", "notes": "...", "video_title": "", "video_description": ""} }
tasks: Dict[str, dict] = {}
rag_engines: Dict[str, VideoRAGEngine] = {}


def get_db_session(database_url: Optional[str] = None):
    session_factory = get_session_factory(database_url)
    if not session_factory:
        return None
    init_db(database_url)
    return session_factory()


def build_settings_signature(request) -> str:
    payload = {
        "provider": request.provider,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "whisper_provider": request.whisper_provider,
        "whisper_model": request.whisper_model,
        "language": request.language,
        "detail_level": request.detail_level,
        "keep_qa": request.keep_qa,
        "keep_examples": request.keep_examples,
        "include_timestamps": request.include_timestamps,
        "ollama_model": request.ollama_model,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_runtime_config(request) -> Config:
    config = Config()
    config.llm_provider = getattr(request, "provider", config.llm_provider)
    config.start_time = getattr(request, "start_time", config.start_time)
    config.end_time = getattr(request, "end_time", config.end_time)
    config.whisper_provider = getattr(request, "whisper_provider", config.whisper_provider)
    config.whisper_model = getattr(request, "whisper_model", config.whisper_model)
    config.language = getattr(request, "language", config.language)
    config.detail_level = getattr(request, "detail_level", config.detail_level)
    config.keep_qa = getattr(request, "keep_qa", config.keep_qa)
    config.keep_examples = getattr(request, "keep_examples", config.keep_examples)
    config.include_timestamps = getattr(request, "include_timestamps", config.include_timestamps)

    if getattr(request, "groq_api_key", None):
        config.groq_api_key = request.groq_api_key
        os.environ["GROQ_API_KEY"] = request.groq_api_key
    if getattr(request, "hf_token", None):
        config.hf_token = request.hf_token
        os.environ["HF_TOKEN"] = request.hf_token
    if getattr(request, "anthropic_api_key", None):
        os.environ["ANTHROPIC_API_KEY"] = request.anthropic_api_key
    if getattr(request, "gemini_api_key", None):
        os.environ["GEMINI_API_KEY"] = request.gemini_api_key
    if getattr(request, "ollama_model", None):
        config.ollama_model = request.ollama_model
    if getattr(request, "ollama_base_url", None):
        config.ollama_base_url = request.ollama_base_url
        os.environ["OLLAMA_API_BASE"] = request.ollama_base_url

    config.whisper_model = config.resolved_whisper_model()
    return config


def ensure_saved_note_rag(task_id: str, note: VideoNoteCache, config: Config):
    rag = VideoRAGEngine(config, video_id=task_id)
    rag.populate_from_cache(note.notes, note.description)
    rag_engines[task_id] = rag
    tasks[task_id] = {
        "status": "completed",
        "progress": "Loaded from saved notes",
        "notes": note.notes,
        "video_title": note.title,
        "video_description": note.description,
        "url": note.url,
        "steps": {
            "extraction": "completed",
            "transcription": "completed",
            "analysis": "completed",
            "synthesis": "completed",
            "rag": "completed"
        },
        "source_note_id": note.id,
    }
    return tasks[task_id]

class ProcessRequest(BaseModel):
    url: str
    provider: str = "gemini"  # anthropic, gemini, ollama
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    hf_token: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    whisper_provider: str = "local" # local, groq
    whisper_model: Optional[str] = None
    language: Optional[str] = None
    detail_level: str = "medium"
    keep_qa: bool = False
    keep_examples: bool = True
    include_timestamps: bool = True
    groq_api_key: Optional[str] = None
    database_url: Optional[str] = None


class OpenSavedNoteRequest(BaseModel):
    provider: str = "gemini"
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    database_url: Optional[str] = None

class ChatRequest(BaseModel):
    task_id: str
    question: str

def process_video_task(task_id: str, request: ProcessRequest):
    """Background task to process the video."""
    try:
        def update_step(step_id: str, status: str):
            if "steps" not in tasks[task_id]:
                tasks[task_id]["steps"] = {
                    "extraction": "pending",
                    "transcription": "pending",
                    "analysis": "pending",
                    "synthesis": "pending",
                    "rag": "pending"
                }
            tasks[task_id]["steps"][step_id] = status

        update_step("extraction", "pending")
        tasks[task_id]["progress"] = "Initializing config..."
        
        # Override config based on request
        config = build_runtime_config(request)
        
        # 1. Extract
        update_step("extraction", "active")
        tasks[task_id]["progress"] = "Extracting audio and metadata..."
        extractor = AudioExtractor(config)
        audio_path, video_title, video_description = extractor.extract(url=request.url)
        
        tasks[task_id]["video_title"] = video_title
        tasks[task_id]["video_description"] = video_description
        update_step("extraction", "completed")

        # 2. Transcribe
        update_step("transcription", "active")
        tasks[task_id]["progress"] = f"Transcribing audio..."
        transcriber = WhisperTranscriber(config)
        chunks = transcriber.transcribe(audio_path)
        total_duration = chunks[-1].end_time if chunks else 0
        update_step("transcription", "completed")

        # 3. Analyze
        update_step("analysis", "active")
        tasks[task_id]["progress"] = f"Analyzing chunks intelligently..."
        analyzer = ChunkAnalyzer(config)
        analyzed_chunks = analyzer.analyze_all(chunks, video_title, video_description)
        update_step("analysis", "completed")

        # 4. Synthesize
        update_step("synthesis", "active")
        tasks[task_id]["progress"] = f"Synthesizing final notes..."
        synthesizer = NotesSynthesizer(config)
        notes = synthesizer.synthesize(analyzed_chunks, video_title, total_duration)
        update_step("synthesis", "completed")

        # 5. Populate RAG Engine
        update_step("rag", "active")
        tasks[task_id]["progress"] = f"Populating knowledge base for Q&A..."
        rag = VideoRAGEngine(config, video_id=task_id)
        rag.populate_database(analyzed_chunks, video_description)
        rag_engines[task_id] = rag
        update_step("rag", "completed")

        # 6. Cache into DB
        db = get_db_session(request.database_url)
        if db:
            try:
                settings_signature = build_settings_signature(request)
                new_cache = VideoNoteCache(
                    url=request.url,
                    provider=request.provider,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    title=video_title,
                    description=video_description,
                    notes=notes,
                    settings_signature=settings_signature,
                )
                db.add(new_cache)
                db.commit()
                db.close()
            except Exception as e:
                print(f"Warning: Failed to cache notes in DB: {e}")

        tasks[task_id]["notes"] = notes
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = "Done"
        tasks[task_id]["url"] = request.url
        
        extractor.cleanup()

    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["progress"] = f"Error: {str(e)}"
        import traceback
        traceback.print_exc()

@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    # Check cache first
    db = get_db_session(request.database_url)
    if db:
        try:
            # Simple match by signature
            settings_signature = build_settings_signature(request)
            cached = db.query(VideoNoteCache).filter_by(
                url=request.url,
                provider=request.provider,
                start_time=request.start_time,
                end_time=request.end_time,
                settings_signature=settings_signature,
            ).first()
            if cached:
                task_id = str(uuid.uuid4())
                ensure_saved_note_rag(task_id, cached, build_runtime_config(request))
                tasks[task_id]["progress"] = "Loaded from cache"
                db.close()
                return {"task_id": task_id}
            db.close()
        except Exception:
            pass

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "processing",
        "progress": "Queued",
        "notes": None,
        "video_title": "",
        "video_description": "",
        "url": request.url,
        "steps": {
             "extraction": "pending",
             "transcription": "pending",
             "analysis": "pending",
             "synthesis": "pending",
             "rag": "pending"
        }
    }
    
    background_tasks.add_task(process_video_task, task_id, request)
    return {"task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@app.get("/api/notes")
async def list_saved_notes(database_url: Optional[str] = None):
    resolved_url = get_database_url(database_url)
    if not resolved_url:
        return {"notes": []}

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        notes = (
            db.query(VideoNoteCache)
            .order_by(VideoNoteCache.id.desc())
            .all()
        )
        return {
            "notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "description": note.description,
                    "url": note.url,
                    "provider": note.provider,
                    "start_time": note.start_time,
                    "end_time": note.end_time,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                }
                for note in notes
            ]
        }
    finally:
        db.close()


@app.post("/api/notes/{note_id}/open")
async def open_saved_note(note_id: int, request: OpenSavedNoteRequest):
    resolved_url = get_database_url(request.database_url)
    if not resolved_url:
        raise HTTPException(status_code=400, detail="Database URL is required to open saved notes")

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        note = db.query(VideoNoteCache).filter_by(id=note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Saved note not found")

        config = build_runtime_config(request)
        task_id = str(uuid.uuid4())
        payload = ensure_saved_note_rag(task_id, note, config)
        payload["task_id"] = task_id
        return payload
    finally:
        db.close()

@app.get("/api/ollama/models")
async def get_ollama_models(base_url: str = "http://localhost:11434"):
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Ollama models: {str(e)}")

@app.post("/api/chat")
async def chat_with_video(request: ChatRequest):
    try:
        if request.task_id not in rag_engines:
            raise HTTPException(status_code=404, detail="Knowledge base not ready or task not found")
        
        engine = rag_engines[request.task_id]
        answer = engine.ask_question(request.question)
        
        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
