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
    overlap_seconds: int = 15            # Overlap between chunks to preserve context

    # Transcription
    whisper_model: str = "base"          # tiny/base/small/medium/large-v2/large-v3
    language: Optional[str] = None       # None = auto-detect

    # Intelligence
    detail_level: str = "medium"         # low / medium / high
    keep_qa: bool = False                # Include Q&A sections
    keep_examples: bool = True           # Keep examples and analogies
    include_timestamps: bool = True      # Add [MM:SS] timestamps to notes

    # Output
    output_format: str = "markdown"      # markdown / json
    verbose: bool = False

    # Claude settings
    claude_model: str = "claude-sonnet-4-20250514"
    max_tokens_per_chunk: int = 800
    max_tokens_synthesis: int = 4000

    # Internal
    temp_dir: str = os.path.join(tempfile.gettempdir(), "video_notes")

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
