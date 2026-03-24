"""
WhisperTranscriber - Transcribes audio using OpenAI Whisper with word-level timestamps.
Groups segments into analysis-ready chunks with overlap.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import math
import json

from config import Config


@dataclass
class TranscriptSegment:
    """A single Whisper-detected segment (usually a sentence or phrase)."""
    text: str
    start: float   # seconds
    end: float     # seconds


@dataclass
class TranscriptChunk:
    """A group of segments forming one analysis unit (~2 min)."""
    index: int
    segments: List[TranscriptSegment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)

    @property
    def start_time(self) -> float:
        return self.segments[0].start if self.segments else 0.0

    @property
    def end_time(self) -> float:
        return self.segments[-1].end if self.segments else 0.0

    @property
    def start_timestamp(self) -> str:
        return _format_timestamp(self.start_time)

    @property
    def end_timestamp(self) -> str:
        return _format_timestamp(self.end_time)

    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS string."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class WhisperTranscriber:
    """
    Transcribes audio with Whisper and groups segments into analysis chunks.
    
    Uses faster-whisper (CTranslate2) for speed if available,
    falls back to openai-whisper.
    """

    def __init__(self, config: Config):
        self.config = config
        self._whisper_backend = None

    def transcribe(self, audio_path: str) -> List[TranscriptChunk]:
        """
        Transcribe audio and return list of TranscriptChunks.
        """
        segments = self._run_whisper(audio_path)
        chunks = self._group_into_chunks(segments)
        return chunks

    def _run_whisper(self, audio_path: str) -> List[TranscriptSegment]:
        """Run Whisper and return raw segments with timestamps."""
        if self.config.whisper_provider == "groq":
            return self._run_groq_whisper(audio_path)
        
        try:
            return self._run_faster_whisper(audio_path)
        except ImportError:
            if self.config.verbose:
                print("   (faster-whisper not found, using openai-whisper)")
            return self._run_openai_whisper(audio_path)
            
    def _run_groq_whisper(self, audio_path: str) -> List[TranscriptSegment]:
        """Use Groq's high-speed Whisper API with built-in chunking for large files."""
        from groq import Groq
        import os
        
        if not self.config.groq_api_key:
            raise ValueError("Groq API key is missing. Cannot use Groq for transcription.")
            
        client = Groq(api_key=self.config.groq_api_key)
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        
        # If the file is > 24MB, we must chunk it with pydub before sending
        if file_size_mb > 24:
            if self.config.verbose:
                print(f"   Audio file is {file_size_mb:.1f}MB (over Groq 25MB limit). Chunking audio...")
            return self._run_groq_whisper_chunked(client, audio_path)
            
        if self.config.verbose:
            print(f"   Sending to Groq API ({self.config.whisper_model})...")
            
        transcription = self._execute_groq_api_with_retry(client, audio_path)
            
        return self._parse_groq_segments(transcription)

    def _run_groq_whisper_chunked(self, client, audio_path: str) -> List[TranscriptSegment]:
        import os
        import subprocess
        import math
        
        # Get total duration in seconds using ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, check=True
        )
        total_duration = float(result.stdout.strip())
        
        # Groq limit is 25MB. At 64kbps, 20 minutes is ~10MB.
        chunk_length_seconds = 20 * 60 # 20 minutes
        num_chunks = math.ceil(total_duration / chunk_length_seconds)
        
        all_segments = []
        for i in range(num_chunks):
            chunk_file = f"{audio_path}_chunk_{i}.mp3"
            start_time = i * chunk_length_seconds
            
            if self.config.verbose:
                print(f"   Splitting chunk {i+1}/{num_chunks} with FFmpeg...")
                
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-ss", str(start_time),
                "-t", str(chunk_length_seconds),
                "-acodec", "copy",
                chunk_file
            ], capture_output=not self.config.verbose, check=True)
            
            if self.config.verbose:
                print(f"   Sending chunk {i+1}/{num_chunks} to Groq API...")
                
            transcription = self._execute_groq_api_with_retry(client, chunk_file)
            
            segments = self._parse_groq_segments(transcription, offset=float(start_time))
            all_segments.extend(segments)
            
            os.remove(chunk_file)
            
        return all_segments

    def _execute_groq_api_with_retry(self, client, file_path: str):
        import time
        import re
        import os
        
        retry_count = 0
        while True:
            try:
                with open(file_path, "rb") as file:
                    return client.audio.transcriptions.create(
                      file=(os.path.basename(file_path), file.read()),
                      model=self.config.whisper_model if "groq" in self.config.whisper_provider else "whisper-large-v3-turbo", 
                      response_format="verbose_json",
                      timestamp_granularities=["segment"],
                      language=self.config.language,
                      temperature=0.0
                    )
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "rate limit" in err_msg:
                    wait_time = 60 # Default fallback
                    # Try to parse "Please try again in 2m35.5s"
                    match = re.search(r'in\s+(?:(\d+)m)?(?:([\d.]+)s)?', err_msg)
                    if match:
                        m = float(match.group(1)) if match.group(1) else 0.0
                        s = float(match.group(2)) if match.group(2) else 0.0
                        if m > 0 or s > 0:
                            wait_time = m * 60 + s + 2.0  # Buffer
                    else:
                        wait_time = min(300, 30 * (2 ** retry_count)) # Exponential
                    
                    print(f"   [Groq Rate Limit] Hitting API limit. Waiting {wait_time:.1f}s before retrying...")
                        
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    raise e

    def _parse_groq_segments(self, transcription, offset: float = 0.0) -> List[TranscriptSegment]:
        result = []
        segments = getattr(transcription, "segments", None)
        if segments is None and isinstance(transcription, dict):
            segments = transcription.get("segments", [])
            
        for seg in segments:
            text = getattr(seg, "text", None) or seg.get("text", "")
            start = getattr(seg, "start", None) or seg.get("start", 0.0)
            end = getattr(seg, "end", None) or seg.get("end", 0.0)
            
            result.append(TranscriptSegment(
                text=text.strip(),
                start=start + offset,
                end=end + offset,
            ))
        return result

    def _run_faster_whisper(self, audio_path: str) -> List[TranscriptSegment]:
        """Use faster-whisper (CTranslate2 backend - 4x faster, less memory)."""
        from faster_whisper import WhisperModel

        model = WhisperModel(
            self.config.whisper_model,
            device="auto",
            compute_type="auto",
        )

        segments_iter, info = model.transcribe(
            audio_path,
            language=self.config.language,
            word_timestamps=True,
            vad_filter=True,          # Voice Activity Detection - skip silence
            vad_parameters={
                "min_silence_duration_ms": 500,
            },
            beam_size=5,
        )

        if self.config.verbose:
            print(f"   Detected language: {info.language} ({info.language_probability:.0%})")

        result = []
        for seg in segments_iter:
            result.append(TranscriptSegment(
                text=seg.text,
                start=seg.start,
                end=seg.end,
            ))

        return result

    def _run_openai_whisper(self, audio_path: str) -> List[TranscriptSegment]:
        """Use openai-whisper (original)."""
        import whisper

        model = whisper.load_model(self.config.whisper_model)
        result = model.transcribe(
            audio_path,
            language=self.config.language,
            verbose=self.config.verbose,
            word_timestamps=False,
            condition_on_previous_text=True,  # Better coherence
        )

        return [
            TranscriptSegment(
                text=seg["text"],
                start=seg["start"],
                end=seg["end"],
            )
            for seg in result["segments"]
        ]

    def _group_into_chunks(
        self, segments: List[TranscriptSegment]
    ) -> List[TranscriptChunk]:
        """
        Group segments into analysis chunks of ~chunk_size_minutes each.
        
        Overlap strategy: the last N seconds of chunk K are included at the
        start of chunk K+1. This prevents context loss at boundaries.
        """
        if not segments:
            return []

        chunks = []
        chunk_size = self.config.chunk_size_seconds
        overlap = self.config.overlap_seconds

        current_chunk_segments = []
        chunk_start_time = segments[0].start
        chunk_index = 0

        for seg in segments:
            current_chunk_segments.append(seg)

            # Check if we've filled a chunk
            chunk_duration = seg.end - chunk_start_time
            if chunk_duration >= chunk_size:
                # Finalize this chunk
                chunk = TranscriptChunk(
                    index=chunk_index,
                    segments=list(current_chunk_segments),
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start next chunk with overlap: keep segments from the last `overlap` seconds
                overlap_cutoff = seg.end - overlap
                current_chunk_segments = [
                    s for s in current_chunk_segments if s.start >= overlap_cutoff
                ]
                chunk_start_time = current_chunk_segments[0].start if current_chunk_segments else seg.end

        # Don't forget the last partial chunk
        if current_chunk_segments:
            # Only add if it has meaningful content (>15 seconds)
            duration = current_chunk_segments[-1].end - current_chunk_segments[0].start
            if duration > 15:
                chunks.append(TranscriptChunk(
                    index=chunk_index,
                    segments=current_chunk_segments,
                ))

        return chunks


def serialize_chunks(chunks: List[TranscriptChunk]) -> str:
    payload = []
    for chunk in chunks:
        payload.append(
            {
                "index": chunk.index,
                "segments": [
                    {
                        "text": segment.text,
                        "start": segment.start,
                        "end": segment.end,
                    }
                    for segment in chunk.segments
                ],
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def deserialize_chunks(payload: str) -> List[TranscriptChunk]:
    raw_chunks = json.loads(payload or "[]")
    chunks: List[TranscriptChunk] = []
    for raw_chunk in raw_chunks:
        segments = [
            TranscriptSegment(
                text=segment.get("text", ""),
                start=float(segment.get("start", 0.0)),
                end=float(segment.get("end", 0.0)),
            )
            for segment in raw_chunk.get("segments", [])
        ]
        chunks.append(
            TranscriptChunk(
                index=int(raw_chunk.get("index", len(chunks))),
                segments=segments,
            )
        )
    return chunks
