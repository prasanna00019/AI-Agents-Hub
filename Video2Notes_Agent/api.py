import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Optional

import dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from analyzer import ChunkAnalyzer
from config import Config
from database import (
    Collection,
    PlaylistRun,
    TranscriptCache,
    VideoNoteCache,
    get_database_url,
    get_session_factory,
    init_db,
)
from export_service import export_payload
from extractor import AudioExtractor
from hybrid_search import HybridSearchRanker
from note_structuring import structure_analyzed_chunks, summarize_search_fields
from rag_engine import VideoRAGEngine
from source_utils import (
    SourceDetails,
    canonicalize_url,
    preview_youtube_playlist,
    validate_upload_filename,
)
from study_assets import StudyAssetsGenerator
from synthesizer import NotesSynthesizer
from transcriber import WhisperTranscriber, deserialize_chunks, serialize_chunks

dotenv.load_dotenv()
init_db()

app = FastAPI(title="VideoNotes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TASK_STEPS = [
    "extraction",
    "transcription",
    "analysis",
    "structuring",
    "synthesis",
    "assets",
    "rag",
    "export",
]
TERMINAL_STATUSES = {"completed", "error"}

tasks: dict[str, dict] = {}
batches: dict[str, dict] = {}
rag_engines: dict[str, VideoRAGEngine] = {}
batch_execution_limits: dict[str, threading.Semaphore] = {}
task_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="video2notes")


def get_db_session(database_url: Optional[str] = None):
    session_factory = get_session_factory(database_url)
    if not session_factory:
        return None
    init_db(database_url)
    return session_factory()


def _base_steps() -> dict[str, str]:
    return {step: "pending" for step in TASK_STEPS}


def _serialize_state(state: dict) -> dict:
    return {
        key: value
        for key, value in state.items()
        if key not in {"event_log", "request_payload"}
    }


def _emit(store: dict[str, dict], entity_id: str, event_name: str, payload: dict):
    state = store[entity_id]
    state.setdefault("event_log", []).append({"event": event_name, "data": payload})


def _sync_batch_child(batch_id: str, task_id: str):
    batch = batches.get(batch_id)
    task = tasks.get(task_id)
    if not batch or not task:
        return

    for child in batch["children"]:
        if child["task_id"] != task_id:
            continue
        child.update(
            {
                "status": task["status"],
                "progress": task["progress"],
                "video_title": task.get("video_title") or child.get("video_title"),
                "source_note_id": task.get("source_note_id"),
                "error": task.get("error"),
            }
        )
        break

    statuses = [child["status"] for child in batch["children"]]
    if statuses and all(status == "completed" for status in statuses):
        batch["status"] = "completed"
        batch["progress"] = "Playlist completed"
    elif any(status == "processing" for status in statuses):
        batch["status"] = "processing"
        batch["progress"] = "Processing playlist videos"
    elif any(status == "error" for status in statuses):
        batch["status"] = "partial"
        batch["progress"] = "Playlist completed with some failures"

    _emit(batches, batch_id, "update", _serialize_state(batch))


def _update_task(task_id: str, **changes):
    tasks[task_id].update(changes)
    _emit(tasks, task_id, "update", _serialize_state(tasks[task_id]))
    batch_id = tasks[task_id].get("batch_id")
    if batch_id:
        _sync_batch_child(batch_id, task_id)


def _update_step(task_id: str, step_id: str, status: str, message: Optional[str] = None):
    tasks[task_id]["steps"][step_id] = status
    if message:
        tasks[task_id]["progress"] = message
    _update_task(task_id)


class ProcessRequest(BaseModel):
    url: str
    provider: str = "gemini"
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    hf_token: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    whisper_provider: str = "local"
    whisper_model: Optional[str] = None
    language: Optional[str] = None
    detail_level: str = "medium"
    keep_qa: bool = False
    keep_examples: bool = True
    include_timestamps: bool = True
    groq_api_key: Optional[str] = None
    database_url: Optional[str] = None
    note_style: str = "study_notes"
    custom_prompt_template: Optional[str] = None
    generate_study_assets: bool = False
    collection_id: Optional[int] = None
    selected_video_ids: Optional[list[str]] = None
    playlist_processing_mode: str = "parallel"
    playlist_worker_count: int = 3


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


class ExportRequest(BaseModel):
    title: str
    description: Optional[str] = None
    notes: str
    study_assets: Optional[dict] = None
    format: str = "markdown_notion"
    template: str = "default"
    include_notes: bool = True
    include_description: bool = False
    include_study_assets: bool = False


class CollectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    database_url: Optional[str] = None


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    database_url: Optional[str] = None


class NoteUpdateRequest(BaseModel):
    collection_id: Optional[int] = None
    database_url: Optional[str] = None


def _create_task(
    source_details: SourceDetails,
    request: ProcessRequest,
    batch_id: Optional[str] = None,
    playlist_run_id: Optional[str] = None,
    playlist_title: Optional[str] = None,
    title_hint: Optional[str] = None,
) -> str:
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": "Queued",
        "error": None,
        "notes": None,
        "study_assets": None,
        "video_title": title_hint or "",
        "video_description": "",
        "url": source_details.normalized_url,
        "source_type": source_details.source_type,
        "source_key": source_details.source_key,
        "note_style": request.note_style,
        "collection_id": request.collection_id,
        "playlist_run_id": playlist_run_id,
        "playlist_title": playlist_title,
        "applied_settings": build_applied_settings(request),
        "steps": _base_steps(),
        "batch_id": batch_id,
        "event_log": [],
        "request_payload": request.model_dump(),
        "saved_note_id": None,
        "source_note_id": None,
    }
    _emit(tasks, task_id, "created", _serialize_state(tasks[task_id]))
    return task_id


def _create_batch(url: str, title: str = "Playlist batch") -> str:
    batch_id = str(uuid.uuid4())
    batches[batch_id] = {
        "batch_id": batch_id,
        "url": url,
        "title": title,
        "status": "processing",
        "progress": "Expanding playlist",
        "children": [],
        "selected_video_ids": [],
        "applied_settings": {},
        "event_log": [],
    }
    _emit(batches, batch_id, "created", _serialize_state(batches[batch_id]))
    return batch_id


def build_runtime_config(request: ProcessRequest) -> Config:
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
    config.note_style = getattr(request, "note_style", config.note_style)
    config.custom_prompt_template = getattr(request, "custom_prompt_template", config.custom_prompt_template)
    config.generate_study_assets = getattr(request, "generate_study_assets", config.generate_study_assets)

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


def build_transcription_signature(request: ProcessRequest, source_details: SourceDetails) -> str:
    payload = {
        "source_key": source_details.source_key,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "whisper_provider": request.whisper_provider,
        "whisper_model": request.whisper_model,
        "language": request.language,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_note_signature(request: ProcessRequest, source_details: SourceDetails) -> str:
    payload = {
        "source_key": source_details.source_key,
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
        "note_style": request.note_style,
        "custom_prompt_template": request.custom_prompt_template,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_applied_settings(request: ProcessRequest) -> dict:
    return {
        "provider": request.provider,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "whisper_provider": request.whisper_provider,
        "whisper_model": request.whisper_model,
        "language": request.language,
        "detail_level": request.detail_level,
        "note_style": request.note_style,
        "custom_prompt_template": request.custom_prompt_template,
        "generate_study_assets": request.generate_study_assets,
        "keep_qa": request.keep_qa,
        "keep_examples": request.keep_examples,
        "include_timestamps": request.include_timestamps,
        "ollama_model": request.ollama_model,
        "ollama_base_url": request.ollama_base_url,
        "database_enabled": bool((request.database_url or "").strip()),
        "collection_id": request.collection_id,
        "playlist_processing_mode": request.playlist_processing_mode,
        "playlist_worker_count": 1 if request.playlist_processing_mode == "sequential" else max(1, min(request.playlist_worker_count, 6)),
    }


def _parse_json_blob(value: Optional[str]) -> dict:
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _resolve_playlist_worker_count(request: ProcessRequest) -> int:
    if request.playlist_processing_mode == "sequential":
        return 1
    return max(1, min(request.playlist_worker_count, 6))


def _schedule_task(
    task_id: str,
    request: ProcessRequest,
    source_details: SourceDetails,
    file_path: Optional[str] = None,
):
    batch_id = tasks.get(task_id, {}).get("batch_id")

    def run_with_limit():
        semaphore = batch_execution_limits.get(batch_id) if batch_id else None
        if not semaphore:
            return _process_task(task_id, request, source_details, file_path)

        semaphore.acquire()
        try:
            return _process_task(task_id, request, source_details, file_path)
        finally:
            semaphore.release()

    return task_executor.submit(run_with_limit)


def _custom_prompt_signature(prompt: Optional[str]) -> Optional[str]:
    if not prompt:
        return None
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _find_cached_note(db, request: ProcessRequest, source_details: SourceDetails):
    note_signature = build_note_signature(request, source_details)
    return (
        db.query(VideoNoteCache)
        .filter_by(
            source_key=source_details.source_key,
            source_type=source_details.source_type,
            settings_signature=note_signature,
        )
        .first()
    )


def _load_study_assets(note: VideoNoteCache) -> Optional[dict]:
    try:
        if not note.study_assets_json:
            return None
        loaded = json.loads(note.study_assets_json)
        return loaded or None
    except Exception:
        return None


def _note_search_text(note: VideoNoteCache, playlist_title: Optional[str] = None) -> str:
    parts = [
        note.title or "",
        note.title or "",
        playlist_title or "",
        note.description or "",
        note.concepts_text or "",
        note.action_items_text or "",
        note.notes or "",
    ]
    return "\n".join(part for part in parts if part)


def ensure_saved_note_rag(task_id: str, note: VideoNoteCache, config: Config, include_study_assets: bool = True):
    rag = VideoRAGEngine(config, video_id=task_id)
    rag.populate_from_cache(note.notes, note.description)
    rag_engines[task_id] = rag
    tasks[task_id].update(
        {
            "status": "completed",
            "progress": "Loaded from saved notes",
            "notes": note.notes,
            "study_assets": _load_study_assets(note) if include_study_assets else None,
            "video_title": note.title,
            "video_description": note.description,
            "url": note.url,
            "note_style": note.note_style or config.note_style,
            "collection_id": note.collection_id,
            "playlist_run_id": note.playlist_run_id,
            "applied_settings": _parse_json_blob(note.applied_settings_json),
            "source_note_id": note.id,
            "saved_note_id": note.id,
            "steps": {step: "completed" for step in TASK_STEPS},
        }
    )
    _emit(tasks, task_id, "update", _serialize_state(tasks[task_id]))
    batch_id = tasks[task_id].get("batch_id")
    if batch_id:
        _sync_batch_child(batch_id, task_id)
    return tasks[task_id]


def _clone_cached_note_for_playlist(
    db,
    cached: VideoNoteCache,
    request: ProcessRequest,
    playlist_run_id: str,
) -> VideoNoteCache:
    clone = VideoNoteCache(
        url=cached.url,
        source_type=cached.source_type,
        source_key=cached.source_key,
        playlist_run_id=playlist_run_id,
        provider=request.provider,
        start_time=request.start_time,
        end_time=request.end_time,
        title=cached.title,
        description=cached.description,
        notes=cached.notes,
        note_style=request.note_style,
        custom_prompt_signature=_custom_prompt_signature(request.custom_prompt_template),
        concepts_text=cached.concepts_text,
        action_items_text=cached.action_items_text,
        study_assets_json=cached.study_assets_json if request.generate_study_assets else None,
        applied_settings_json=json.dumps(build_applied_settings(request), ensure_ascii=False),
        transcript_cache_id=cached.transcript_cache_id,
        collection_id=request.collection_id,
        settings_signature=build_note_signature(request, SourceDetails(
            source_type=cached.source_type or "url",
            normalized_url=cached.url,
            source_key=cached.source_key or f"url:{cached.url}",
        )),
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


def _store_uploaded_file(file: UploadFile) -> tuple[str, SourceDetails]:
    validate_upload_filename(file.filename or "")
    suffix = Path(file.filename or "").suffix.lower()
    temp_name = f"upload_{uuid.uuid4().hex}{suffix}"
    temp_path = os.path.join(tempfile.gettempdir(), "video_notes", temp_name)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    hasher = hashlib.sha256()
    total_size = 0
    max_size_bytes = 1024 * 1024 * 1024
    with open(temp_path, "wb") as handle:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size_bytes:
                handle.close()
                os.remove(temp_path)
                raise HTTPException(status_code=400, detail="Upload is too large. Keep files under 1 GB.")
            hasher.update(chunk)
            handle.write(chunk)

    source_key = f"upload:{hasher.hexdigest()}"
    source_details = SourceDetails(
        source_type="upload",
        normalized_url=f"upload://{file.filename or 'file'}",
        source_key=source_key,
        title_hint=Path(file.filename or "uploaded file").stem,
    )
    return temp_path, source_details


async def _event_stream(store: dict[str, dict], entity_id: str):
    position = 0
    while entity_id in store:
        state = store[entity_id]
        log = state.get("event_log", [])
        while position < len(log):
            event = log[position]
            position += 1
            payload = json.dumps(event["data"])
            yield f"event: {event['event']}\ndata: {payload}\n\n"
        if state.get("status") in TERMINAL_STATUSES or state.get("status") == "partial":
            break
        await asyncio.sleep(1)


def _process_task(
    task_id: str,
    request: ProcessRequest,
    source_details: SourceDetails,
    file_path: Optional[str] = None,
):
    extractor = None
    try:
        config = build_runtime_config(request)
        applied_settings = build_applied_settings(request)
        batch_id = tasks[task_id].get("batch_id")
        if batch_id:
            print("\n=== Playlist Task Start ===")
            print(f"batch_id={batch_id}")
            print(f"task_id={task_id}")
            print(f"title={tasks[task_id].get('video_title') or source_details.title_hint or source_details.normalized_url}")
            print(f"mode={batches.get(batch_id, {}).get('playlist_processing_mode')}")
            print(f"workers={batches.get(batch_id, {}).get('playlist_worker_count')}")
            print("=== End Playlist Task Start ===\n")
        print("\n=== VideoNotes Applied Settings ===")
        print(json.dumps(applied_settings, indent=2, ensure_ascii=False))
        print("=== End Applied Settings ===\n")
        db = get_db_session(request.database_url)
        transcript_cache = None
        chunks = []
        video_title = source_details.title_hint or "Video"
        video_description = ""

        _update_task(task_id, progress="Initializing pipeline...")

        if db:
            transcript_cache = (
                db.query(TranscriptCache)
                .filter_by(signature=build_transcription_signature(request, source_details))
                .first()
            )

        if transcript_cache:
            _update_step(task_id, "transcription", "completed", "Loaded transcript from cache")
            chunks = deserialize_chunks(transcript_cache.transcript_json)
            video_title = transcript_cache.title or video_title
            video_description = transcript_cache.description or ""
        else:
            _update_step(task_id, "extraction", "active", "Extracting audio and metadata...")
            extractor = AudioExtractor(config)
            audio_path, video_title, video_description = extractor.extract(
                url=source_details.normalized_url if source_details.source_type != "upload" else None,
                file_path=file_path,
            )
            _update_step(task_id, "extraction", "completed", "Audio ready")

            _update_step(task_id, "transcription", "active", "Transcribing audio...")
            transcriber = WhisperTranscriber(config)
            chunks = transcriber.transcribe(audio_path)
            _update_step(task_id, "transcription", "completed", "Transcription ready")

            if db and chunks:
                transcript_cache = TranscriptCache(
                    source_type=source_details.source_type,
                    source_key=source_details.source_key,
                    source_url=source_details.normalized_url,
                    title=video_title,
                    description=video_description,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    whisper_provider=request.whisper_provider,
                    whisper_model=config.whisper_model,
                    language=request.language,
                    signature=build_transcription_signature(request, source_details),
                    transcript_json=serialize_chunks(chunks),
                )
                db.add(transcript_cache)
                db.commit()
                db.refresh(transcript_cache)

        total_duration = chunks[-1].end_time if chunks else 0

        _update_step(task_id, "analysis", "active", "Analyzing transcript...")
        analyzer = ChunkAnalyzer(config)
        analyzed_chunks = analyzer.analyze_all(chunks, video_title, video_description)
        _update_step(task_id, "analysis", "completed", "Analysis complete")

        _update_step(task_id, "structuring", "active", "Structuring sections...")
        structured_sections = structure_analyzed_chunks(analyzed_chunks)
        concepts_text, action_items_text = summarize_search_fields(structured_sections)
        _update_step(task_id, "structuring", "completed", "Structured note outline ready")

        _update_step(task_id, "synthesis", "active", "Synthesizing notes...")
        synthesizer = NotesSynthesizer(config)
        notes = synthesizer.synthesize(structured_sections, video_title, total_duration)
        _update_step(task_id, "synthesis", "completed", "Notes generated")

        study_assets = None
        if config.generate_study_assets:
            _update_step(task_id, "assets", "active", "Generating study assets...")
            assets_generator = StudyAssetsGenerator(config)
            study_assets = assets_generator.generate(video_title, notes)
            _update_step(task_id, "assets", "completed", "Study assets generated")
        else:
            _update_step(task_id, "assets", "skipped", "Study assets skipped for this run")

        _update_step(task_id, "rag", "active", "Building Q&A knowledge base...")
        rag = VideoRAGEngine(config, video_id=task_id)
        rag.populate_database(analyzed_chunks, structured_sections, video_description)
        rag_engines[task_id] = rag
        _update_step(task_id, "rag", "completed", "RAG ready")

        saved_note_id = None
        if db:
            note = VideoNoteCache(
                url=source_details.normalized_url,
                source_type=source_details.source_type,
                source_key=source_details.source_key,
                playlist_run_id=tasks[task_id].get("playlist_run_id"),
                provider=request.provider,
                start_time=request.start_time,
                end_time=request.end_time,
                title=video_title,
                description=video_description,
                notes=notes,
                note_style=request.note_style,
                custom_prompt_signature=_custom_prompt_signature(request.custom_prompt_template),
                concepts_text=concepts_text,
                action_items_text=action_items_text,
                study_assets_json=json.dumps(study_assets, ensure_ascii=False) if study_assets else None,
                applied_settings_json=json.dumps(applied_settings, ensure_ascii=False),
                transcript_cache_id=transcript_cache.id if transcript_cache else None,
                collection_id=request.collection_id,
                settings_signature=build_note_signature(request, source_details),
            )
            db.add(note)
            db.commit()
            db.refresh(note)
            saved_note_id = note.id
            db.close()

        _update_step(task_id, "export", "completed", "Exports ready")
        _update_task(
            task_id,
            status="completed",
            progress="Done",
            notes=notes,
            study_assets=study_assets,
            video_title=video_title,
            video_description=video_description,
            applied_settings=applied_settings,
            saved_note_id=saved_note_id,
            source_note_id=saved_note_id,
        )
    except Exception as exc:
        _update_task(task_id, status="error", progress=f"Error: {exc}", error=str(exc))
    finally:
        if extractor:
            extractor.cleanup()
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    source_details = canonicalize_url(request.url)
    if source_details.is_playlist:
        raise HTTPException(status_code=400, detail="Use /api/process/playlist for playlist URLs.")

    task_id = _create_task(source_details, request)
    db = get_db_session(request.database_url)
    if db:
        cached = _find_cached_note(db, request, source_details)
        if cached:
            ensure_saved_note_rag(
                task_id,
                cached,
                build_runtime_config(request),
                include_study_assets=request.generate_study_assets,
            )
            db.close()
            return {"task_id": task_id}
        db.close()

    _schedule_task(task_id, request, source_details, None)
    return {"task_id": task_id}


@app.post("/api/process/upload")
async def process_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    payload_json: str = Form(...),
):
    try:
        payload = ProcessRequest(**json.loads(payload_json))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid upload payload: {exc}") from exc

    file_path, source_details = _store_uploaded_file(file)
    task_id = _create_task(source_details, payload, title_hint=source_details.title_hint)

    db = get_db_session(payload.database_url)
    if db:
        cached = _find_cached_note(db, payload, source_details)
        if cached:
            ensure_saved_note_rag(
                task_id,
                cached,
                build_runtime_config(payload),
                include_study_assets=payload.generate_study_assets,
            )
            db.close()
            try:
                os.remove(file_path)
            except OSError:
                pass
            return {"task_id": task_id}
        db.close()

    _schedule_task(task_id, payload, source_details, file_path)
    return {"task_id": task_id}


@app.post("/api/process/playlist/preview")
async def preview_playlist(request: ProcessRequest):
    source_details = canonicalize_url(request.url)
    if not source_details.is_playlist:
        raise HTTPException(status_code=400, detail="The provided URL is not a supported YouTube playlist.")
    preview = preview_youtube_playlist(request.url)
    return {
        "title": preview["title"],
        "source_key": source_details.source_key,
        "entries": preview["entries"],
    }


@app.post("/api/process/playlist")
async def process_playlist(request: ProcessRequest, background_tasks: BackgroundTasks):
    source_details = canonicalize_url(request.url)
    if not source_details.is_playlist:
        raise HTTPException(status_code=400, detail="The provided URL is not a supported YouTube playlist.")

    preview = preview_youtube_playlist(request.url)
    entries = preview["entries"]
    selected_ids = set(request.selected_video_ids or [])
    if selected_ids:
        entries = [entry for entry in entries if entry["id"] in selected_ids]
    if not entries:
        raise HTTPException(status_code=400, detail="No playlist videos were selected for processing.")

    batch_id = _create_batch(request.url, preview["title"])
    worker_count = _resolve_playlist_worker_count(request)
    batch_execution_limits[batch_id] = threading.Semaphore(worker_count)
    print("\n=== Playlist Execution Settings ===")
    print(f"batch_id={batch_id}")
    print(f"title={preview['title']}")
    print(f"mode={request.playlist_processing_mode}")
    print(f"workers={worker_count}")
    print(f"selected_videos={len(entries)}")
    print("=== End Playlist Execution Settings ===\n")
    batches[batch_id]["progress"] = f"Queued {len(entries)} playlist videos"
    batches[batch_id]["selected_video_ids"] = [entry["id"] for entry in entries]
    batches[batch_id]["applied_settings"] = build_applied_settings(request)
    batches[batch_id]["playlist_processing_mode"] = request.playlist_processing_mode
    batches[batch_id]["playlist_worker_count"] = worker_count

    db = get_db_session(request.database_url)
    if db:
        playlist_run = PlaylistRun(
            id=batch_id,
            title=preview["title"],
            url=request.url,
            source_key=source_details.source_key,
            selected_video_ids_json=json.dumps(batches[batch_id]["selected_video_ids"]),
            applied_settings_json=json.dumps(build_applied_settings(request), ensure_ascii=False),
        )
        db.merge(playlist_run)
        db.commit()

    for entry in entries:
        child_source = SourceDetails(
            source_type="url",
            normalized_url=entry["url"],
            source_key=entry["source_key"],
            title_hint=entry["title"],
        )
        child_request = request.model_copy(update={"url": entry["url"]})
        task_id = _create_task(
            child_source,
            child_request,
            batch_id=batch_id,
            playlist_run_id=batch_id,
            playlist_title=preview["title"],
            title_hint=entry["title"],
        )
        batches[batch_id]["children"].append(
            {
                "task_id": task_id,
                "video_id": entry["id"],
                "title": entry["title"],
                "url": entry["url"],
                "status": "processing",
                "progress": "Queued",
                "video_title": entry["title"],
                "source_note_id": None,
                "error": None,
            }
        )

        if db:
            cached = _find_cached_note(db, child_request, child_source)
            if cached:
                cloned = _clone_cached_note_for_playlist(db, cached, child_request, batch_id)
                ensure_saved_note_rag(
                    task_id,
                    cloned,
                    build_runtime_config(child_request),
                    include_study_assets=child_request.generate_study_assets,
                )
                continue

        _schedule_task(task_id, child_request, child_source, None)

    if db:
        db.close()

    _emit(batches, batch_id, "update", _serialize_state(batches[batch_id]))
    return {
        "batch_id": batch_id,
        "title": preview["title"],
        "children": batches[batch_id]["children"],
        "selected_video_ids": batches[batch_id]["selected_video_ids"],
        "playlist_processing_mode": request.playlist_processing_mode,
        "playlist_worker_count": worker_count,
    }


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_state(tasks[task_id])


@app.get("/api/tasks/{task_id}/events")
async def stream_task_events(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return StreamingResponse(_event_stream(tasks, task_id), media_type="text/event-stream")


@app.get("/api/batches/{batch_id}")
async def get_batch_status(batch_id: str):
    if batch_id not in batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _serialize_state(batches[batch_id])


@app.get("/api/batches/{batch_id}/events")
async def stream_batch_events(batch_id: str):
    if batch_id not in batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    return StreamingResponse(_event_stream(batches, batch_id), media_type="text/event-stream")


@app.post("/api/batches/{batch_id}/tasks/{task_id}/retry")
async def retry_batch_task(batch_id: str, task_id: str, background_tasks: BackgroundTasks):
    if batch_id not in batches or task_id not in tasks:
        raise HTTPException(status_code=404, detail="Batch task not found")

    task = tasks[task_id]
    request = ProcessRequest(**task.get("request_payload", {"url": task["url"]}))
    task["status"] = "processing"
    task["error"] = None
    task["progress"] = "Retry queued"
    task["steps"] = _base_steps()
    _emit(tasks, task_id, "update", _serialize_state(task))
    _sync_batch_child(batch_id, task_id)
    batch_execution_limits.setdefault(
        batch_id,
        threading.Semaphore(max(1, batches.get(batch_id, {}).get("playlist_worker_count", 1))),
    )

    source_details = SourceDetails(
        source_type=task["source_type"],
        normalized_url=task["url"],
        source_key=task["source_key"],
        title_hint=task.get("video_title"),
    )
    _schedule_task(task_id, request, source_details, None)
    return {"task_id": task_id}


@app.get("/api/notes")
async def list_saved_notes(
    database_url: Optional[str] = None,
    q: Optional[str] = None,
    collection_id: Optional[int] = None,
):
    resolved_url = get_database_url(database_url)
    if not resolved_url:
        return {"notes": [], "playlist_runs": []}

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        query = db.query(VideoNoteCache).filter(VideoNoteCache.playlist_run_id.is_(None))
        if collection_id:
            query = query.filter(VideoNoteCache.collection_id == collection_id)

        notes = query.order_by(VideoNoteCache.id.desc()).all()
        collections = {collection.id: collection.name for collection in db.query(Collection).all()}
        playlist_children_query = db.query(VideoNoteCache).filter(VideoNoteCache.playlist_run_id.is_not(None))
        if collection_id:
            playlist_children_query = playlist_children_query.filter(VideoNoteCache.collection_id == collection_id)

        playlist_children = playlist_children_query.order_by(VideoNoteCache.created_at.desc()).all()
        playlist_runs_by_id = {
            run.id: run
            for run in db.query(PlaylistRun).order_by(PlaylistRun.created_at.desc()).all()
        }
        if q and q.strip():
            notes = HybridSearchRanker.rank(q, notes, lambda note: _note_search_text(note))
            playlist_children = HybridSearchRanker.rank(
                q,
                playlist_children,
                lambda note: _note_search_text(note, playlist_runs_by_id.get(note.playlist_run_id).title if note.playlist_run_id in playlist_runs_by_id else None),
            )

        playlist_runs = {
            run.id: {
                "id": run.id,
                "title": run.title,
                "url": run.url,
                "source_key": run.source_key,
                "applied_settings": _parse_json_blob(run.applied_settings_json),
                "children": [],
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in playlist_runs_by_id.values()
        }
        for note in playlist_children:
            if note.playlist_run_id not in playlist_runs:
                continue
            playlist_runs[note.playlist_run_id]["children"].append(
                {
                    "id": note.id,
                    "title": note.title,
                    "description": note.description,
                    "url": note.url,
                    "provider": note.provider,
                    "source_type": note.source_type,
                    "note_style": note.note_style,
                    "collection_id": note.collection_id,
                    "collection_name": collections.get(note.collection_id),
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                }
            )
        playlist_run_list = [run for run in playlist_runs.values() if run["children"]]
        if q and q.strip():
            ranked_run_ids = []
            for note in playlist_children:
                if note.playlist_run_id and note.playlist_run_id not in ranked_run_ids:
                    ranked_run_ids.append(note.playlist_run_id)
            playlist_run_list.sort(
                key=lambda run: ranked_run_ids.index(run["id"]) if run["id"] in ranked_run_ids else len(ranked_run_ids)
            )
        return {
            "notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "description": note.description,
                    "url": note.url,
                    "provider": note.provider,
                    "source_type": note.source_type,
                    "note_style": note.note_style,
                    "collection_id": note.collection_id,
                    "collection_name": collections.get(note.collection_id),
                    "start_time": note.start_time,
                    "end_time": note.end_time,
                    "applied_settings": _parse_json_blob(note.applied_settings_json),
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                }
                for note in notes
            ],
            "playlist_runs": playlist_run_list,
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

        config = build_runtime_config(
            ProcessRequest(
                url=note.url or "",
                provider=request.provider,
                anthropic_api_key=request.anthropic_api_key,
                gemini_api_key=request.gemini_api_key,
                ollama_model=request.ollama_model,
                ollama_base_url=request.ollama_base_url,
                database_url=request.database_url,
                note_style=note.note_style or "study_notes",
            )
        )
        source_details = SourceDetails(
            source_type=note.source_type or "url",
            normalized_url=note.url or "",
            source_key=note.source_key or f"url:{note.url}",
        )
        task_id = _create_task(
            source_details,
            ProcessRequest(url=note.url or "", provider=request.provider, note_style=note.note_style or "study_notes"),
        )
        payload = ensure_saved_note_rag(task_id, note, config)
        payload["task_id"] = task_id
        payload["id"] = note.id
        payload["applied_settings"] = _parse_json_blob(note.applied_settings_json)
        return payload
    finally:
        db.close()


@app.patch("/api/notes/{note_id}")
async def update_saved_note(note_id: int, request: NoteUpdateRequest):
    resolved_url = get_database_url(request.database_url)
    if not resolved_url:
        raise HTTPException(status_code=400, detail="Database URL is required to update notes")

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        note = db.query(VideoNoteCache).filter_by(id=note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Saved note not found")
        note.collection_id = request.collection_id
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/collections")
async def list_collections(database_url: Optional[str] = None):
    resolved_url = get_database_url(database_url)
    if not resolved_url:
        return {"collections": []}

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        collections = db.query(Collection).order_by(Collection.name.asc()).all()
        return {
            "collections": [
                {
                    "id": collection.id,
                    "name": collection.name,
                    "description": collection.description,
                    "created_at": collection.created_at.isoformat() if collection.created_at else None,
                }
                for collection in collections
            ]
        }
    finally:
        db.close()


@app.post("/api/collections")
async def create_collection(request: CollectionCreateRequest):
    resolved_url = get_database_url(request.database_url)
    if not resolved_url:
        raise HTTPException(status_code=400, detail="Database URL is required to manage collections")

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        collection = Collection(name=request.name.strip(), description=request.description)
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return {"id": collection.id, "name": collection.name, "description": collection.description}
    finally:
        db.close()


@app.patch("/api/collections/{collection_id}")
async def update_collection(collection_id: int, request: CollectionUpdateRequest):
    resolved_url = get_database_url(request.database_url)
    if not resolved_url:
        raise HTTPException(status_code=400, detail="Database URL is required to manage collections")

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        collection = db.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        if request.name is not None:
            collection.name = request.name.strip()
        if request.description is not None:
            collection.description = request.description
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.delete("/api/collections/{collection_id}")
async def delete_collection(collection_id: int, database_url: Optional[str] = None):
    resolved_url = get_database_url(database_url)
    if not resolved_url:
        raise HTTPException(status_code=400, detail="Database URL is required to manage collections")

    db = get_db_session(resolved_url)
    if not db:
        raise HTTPException(status_code=400, detail="Unable to connect to the provided database URL")

    try:
        collection = db.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        db.query(VideoNoteCache).filter_by(collection_id=collection_id).update({"collection_id": None})
        db.delete(collection)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.post("/api/export")
async def export_note(request: ExportRequest):
    if not any([request.include_notes, request.include_description, request.include_study_assets]):
        raise HTTPException(status_code=400, detail="Select at least one section to export.")
    content, media_type, filename = export_payload(
        title=request.title,
        description=request.description or "",
        notes=request.notes,
        study_assets=request.study_assets or {},
        export_format=request.format,
        template=request.template,
        include_notes=request.include_notes,
        include_description=request.include_description,
        include_study_assets=request.include_study_assets,
    )
    payload = content.encode("utf-8") if isinstance(content, str) else content
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/ollama/models")
async def get_ollama_models(base_url: str = "http://localhost:11434"):
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags")
            return response.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Ollama models: {exc}") from exc


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}") from exc
