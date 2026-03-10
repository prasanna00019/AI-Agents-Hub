import os
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
from database import SessionLocal, VideoNoteCache, init_db

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

class ProcessRequest(BaseModel):
    url: str
    provider: str = "gemini"  # anthropic, gemini, ollama
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    whisper_provider: str = "local" # local, groq
    groq_api_key: Optional[str] = None

class ChatRequest(BaseModel):
    task_id: str
    question: str

def process_video_task(task_id: str, request: ProcessRequest):
    """Background task to process the video."""
    try:
        tasks[task_id]["progress"] = "Initializing config..."
        
        # Override config based on request
        config = Config()
        config.llm_provider = request.provider
        config.start_time = request.start_time
        config.end_time = request.end_time
        config.whisper_provider = request.whisper_provider
        
        if request.groq_api_key:
            config.groq_api_key = request.groq_api_key
            
        if request.whisper_provider == "groq":
            config.whisper_model = "whisper-large-v3-turbo" # Ensure Groq model is used
        
        # 1. Extract
        tasks[task_id]["progress"] = "Extracting audio and metadata..."
        extractor = AudioExtractor(config)
        audio_path, video_title, video_description = extractor.extract(url=request.url)
        
        tasks[task_id]["video_title"] = video_title
        tasks[task_id]["video_description"] = video_description

        # 2. Transcribe
        tasks[task_id]["progress"] = f"Transcribing audio..."
        transcriber = WhisperTranscriber(config)
        chunks = transcriber.transcribe(audio_path)
        total_duration = chunks[-1].end_time if chunks else 0

        # 3. Analyze
        tasks[task_id]["progress"] = f"Analyzing chunks intelligently..."
        analyzer = ChunkAnalyzer(config)
        analyzed_chunks = analyzer.analyze_all(chunks, video_title, video_description)

        # 4. Synthesize
        tasks[task_id]["progress"] = f"Synthesizing final notes..."
        synthesizer = NotesSynthesizer(config)
        notes = synthesizer.synthesize(analyzed_chunks, video_title, total_duration)

        # 5. Populate RAG Engine
        tasks[task_id]["progress"] = f"Populating knowledge base for Q&A..."
        rag = VideoRAGEngine(config, video_id=task_id)
        rag.populate_database(analyzed_chunks, video_description)
        rag_engines[task_id] = rag

        # 6. Cache into DB
        if SessionLocal:
            try:
                db = SessionLocal()
                new_cache = VideoNoteCache(
                    url=request.url,
                    provider=request.provider,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    title=video_title,
                    description=video_description,
                    notes=notes
                )
                db.add(new_cache)
                db.commit()
                db.close()
            except Exception as e:
                print(f"Warning: Failed to cache notes in DB: {e}")

        tasks[task_id]["notes"] = notes
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = "Done"
        
        extractor.cleanup()

    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["progress"] = f"Error: {str(e)}"
        import traceback
        traceback.print_exc()

@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    # Check cache first
    if SessionLocal:
        try:
            db = SessionLocal()
            # Simple match by signature
            cached = db.query(VideoNoteCache).filter_by(
                url=request.url,
                provider=request.provider,
                start_time=request.start_time,
                end_time=request.end_time
            ).first()
            if cached:
                task_id = str(uuid.uuid4())
                tasks[task_id] = {
                    "status": "completed",
                    "progress": "Loaded from cache",
                    "notes": cached.notes,
                    "video_title": cached.title,
                    "video_description": cached.description
                }
                # To support RAG on cached responses, we'd need to re-embed or save the vector DB persistence token.
                # For this iteration, we recreate empty RAG engine context or advise user.
                # Here we just initialize a blank RAG so it doesn't 500 later, but RAG may lack chunk context unless re-analyzed.
                config = Config()
                config.llm_provider = cached.provider
                rag = VideoRAGEngine(config, video_id=task_id)
                rag.populate_from_cache(cached.notes, cached.description)
                rag_engines[task_id] = rag
                db.close()
                return {"task_id": task_id}
            db.close()
        except:
            pass

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "processing",
        "progress": "Queued",
        "notes": None,
        "video_title": "",
        "video_description": ""
    }
    
    background_tasks.add_task(process_video_task, task_id, request)
    return {"task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

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
