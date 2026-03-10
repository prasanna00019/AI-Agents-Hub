"""
Configuration for VideoNotes pipeline.
"""
import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # Chunking
    chunk_size_minutes: int = 2          # Minutes per analysis chunk
    overlap_seconds: int = 20            # Overlap between chunks to preserve context

    # Boundaries
    start_time: Optional[str] = None     # Optional start time e.g., "01:00"
    end_time: Optional[str] = None       # Optional end time e.g., "05:00"

    # Transcription
    whisper_provider: str = "local"      # local / groq
    whisper_model: str = "tiny"          # local: tiny/base/small/medium/large-v2/large-v3, groq: whisper-large-v3-turbo / whisper-large-v3
    groq_api_key: Optional[str] = os.environ.get("GROQ_API_KEY")
    language: Optional[str] = None       # None = auto-detect

    # Intelligence
    detail_level: str = "medium"         # low / medium / high
    keep_qa: bool = False                # Include Q&A sections
    keep_examples: bool = True           # Keep examples and analogies
    include_timestamps: bool = True      # Add [MM:SS] timestamps to notes

    # Output
    output_format: str = "markdown"      # markdown / json
    verbose: bool = False

    # LLM settings
    llm_provider: str = os.environ.get("DEFAULT_LLM_PROVIDER", "anthropic")
    anthropic_model: str = "claude-3-5-sonnet-latest"
    gemini_model: str = "gemini-2.5-flash"
    ollama_model: str = "gpt-oss:120b-cloud"
    
    max_tokens_per_chunk: int = 800
    max_tokens_synthesis: int = 4000

    # Internal
    temp_dir: str = os.path.join(tempfile.gettempdir(), "video_notes")

    @property
    def current_model(self) -> str:
        """Return the litellm model string for the active provider."""
        if self.llm_provider == "anthropic":
            return self.anthropic_model  # litellm expects just the model name for anthropic mostly, but actually we should use "anthropic/claude-..." or just let litellm map it it mapped automatically based on key? By default litellm uses claude-... directly, but it's safer to use gemini/... or ollama/...
        elif self.llm_provider == "gemini":
            return f"gemini/{self.gemini_model}"
        elif self.llm_provider == "ollama":
            return f"ollama/{self.ollama_model}"
        return self.anthropic_model


    @property
    def chunk_size_seconds(self) -> int:
        return self.chunk_size_minutes * 60

    @property
    def detail_instruction(self) -> str:
        instructions = {
            "low": "Be very concise. Only the absolute key points, no elaboration.",
            "medium": "Balance conciseness with completeness. Capture key concepts with brief context.",
            "high": "Be thorough. Capture all important concepts, sub-points, and relevant context.",
        }
        return instructions.get(self.detail_level, instructions["medium"])
