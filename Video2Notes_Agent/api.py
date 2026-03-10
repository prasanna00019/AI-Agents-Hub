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

dotenv.load_dotenv()

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
    if request.task_id not in rag_engines:
        raise HTTPException(status_code=404, detail="Knowledge base not ready or task not found")
    
    engine = rag_engines[request.task_id]
    answer = engine.ask_question(request.question)
    
    return {"answer": answer}
