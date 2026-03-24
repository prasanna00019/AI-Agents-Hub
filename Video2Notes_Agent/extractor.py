"""
Audio Extractor - handles YouTube URLs and local video files.
Uses yt-dlp for URLs and FFmpeg for local files.
"""

import os
import re
import subprocess
import tempfile
import json
import uuid
from pathlib import Path
from typing import Optional, Tuple

import shutil
from config import Config


class AudioExtractor:
    """Extracts audio from video URLs or local files."""

    def __init__(self, config: Config):
        self.config = config
        self._temp_files = []
        os.makedirs(config.temp_dir, exist_ok=True)

    def extract(
        self, url: Optional[str] = None, file_path: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Extract audio and return (audio_path, video_title, description).
        """
        if url:
            return self._extract_from_url(url)
        elif file_path:
            return self._extract_from_file(file_path)
        else:
            raise ValueError("Either url or file_path must be provided")

    def _extract_from_url(self, url: str) -> Tuple[str, str, str]:
        """Download audio from YouTube/URL using yt-dlp."""
        self._check_dependency("yt-dlp", "pip install yt-dlp")

        # Get metadata (title, description)
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", url],
            capture_output=True, text=True, check=True
        )
        try:
            metadata = json.loads(result.stdout.strip().split('\n')[0])
            title = metadata.get("title", "video")
            description = metadata.get("description", "")
        except:
            title = "video"
            description = ""

        # Download audio only as mp3
        audio_path = os.path.join(self.config.temp_dir, f"audio_{uuid.uuid4().hex}.mp3")
        ytdlp_args = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", audio_path,
            "--no-playlist",
        ]

        if self.config.start_time and self.config.end_time:
            ytdlp_args.extend(["--download-sections", f"*{self.config.start_time}-{self.config.end_time}"])

        ytdlp_args.append(url)

        subprocess.run(
            ytdlp_args,
            check=True,
            capture_output=not self.config.verbose,
        )

        if not os.path.exists(audio_path):
            # yt-dlp might add suffix, find the file
            files = list(Path(self.config.temp_dir).glob("*.mp3"))
            if not files:
                raise RuntimeError("Audio download failed - no mp3 found")
            audio_path = str(files[0])

        self._temp_files.append(audio_path)
        return audio_path, title, description

    def _extract_from_file(self, file_path: str) -> Tuple[str, str, str]:
        """Extract audio from a local video file using FFmpeg."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        title = Path(file_path).stem
        ext = Path(file_path).suffix.lower()

        # If it's already audio, return as-is
        audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
        if ext in audio_extensions and not (self.config.start_time or self.config.end_time):
            if str(file_path).startswith(self.config.temp_dir):
                self._temp_files.append(file_path)
            return file_path, title, ""

        # Extract audio with FFmpeg
        self._check_dependency("ffmpeg", "brew install ffmpeg  OR  apt install ffmpeg")
        audio_path = os.path.join(self.config.temp_dir, f"{title}_{uuid.uuid4().hex}_audio.mp3")

        ffmpeg_args = [
            "ffmpeg", "-i", file_path,
            "-vn",                    # No video
            "-acodec", "libmp3lame",  # MP3 codec
            "-ar", "16000",           # 16kHz sample rate (optimal for Whisper)
            "-ac", "1",              # Mono
            "-ab", "64k",            # 64kbps (sufficient for speech)
        ]

        if self.config.start_time:
            ffmpeg_args.extend(["-ss", self.config.start_time])
        if self.config.end_time:
            ffmpeg_args.extend(["-to", self.config.end_time])
            
        ffmpeg_args.extend(["-y", audio_path])

        subprocess.run(
            ffmpeg_args,
            check=True,
            capture_output=not self.config.verbose,
        )

        self._temp_files.append(audio_path)
        return audio_path, title, ""

    def _check_dependency(self, tool: str, install_hint: str):
        """Check if a CLI tool is available."""
        if shutil.which(tool):
            return

        # Fallback for Windows: check Python's Scripts directory
        if os.name == 'nt':
            import sys
            import site
            
            # Check system scripts
            python_dir = os.path.dirname(sys.executable)
            scripts_dir = os.path.join(python_dir, "Scripts")
            
            # Check user scripts
            try:
                user_base = site.getuserbase()
                v = sys.version_info
                # On Windows, user scripts are often in %APPDATA%\Python\PythonXX\Scripts
                user_scripts_specific = os.path.join(user_base, f"Python{v.major}{v.minor}", "Scripts")
                user_scripts_generic = os.path.join(user_base, "Scripts")
            except:
                user_scripts_specific = None
                user_scripts_generic = None
                
            for p in [scripts_dir, user_scripts_specific, user_scripts_generic]:
                if p and os.path.exists(p) and shutil.which(tool, path=p):
                    # Add it to PATH for the current process
                    os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
                    return

        raise RuntimeError(
            f"'{tool}' not found. Install it with: {install_hint}"
        )

    def cleanup(self):
        """Remove temp audio files."""
        for f in self._temp_files:
            try:
                os.remove(f)
            except OSError:
                pass
        self._temp_files = []
