import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse


SUPPORTED_UPLOAD_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac",
}


@dataclass
class SourceDetails:
    source_type: str
    normalized_url: str
    source_key: str
    is_playlist: bool = False
    title_hint: Optional[str] = None


def validate_upload_filename(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Upload mp4, mov, mkv, mp3, wav, m4a, ogg, flac, or aac."
        )
    return ext


def extract_google_drive_file_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "drive.google.com" not in host:
        return None

    path_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", parsed.path)
    if path_match:
        return path_match.group(1)

    query = parse_qs(parsed.query)
    if query.get("id"):
        return query["id"][0]

    return None


def is_google_drive_folder_or_doc(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "docs.google.com" in host:
        return True
    if "drive.google.com" not in host:
        return False
    return "/drive/folders/" in parsed.path or "/folders/" in parsed.path


def is_youtube_playlist(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not any(domain in host for domain in ("youtube.com", "youtu.be")):
        return False
    query = parse_qs(parsed.query)
    return bool(query.get("list")) and "/watch" in parsed.path


def canonicalize_url(url: str) -> SourceDetails:
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("A video URL is required.")

    if is_google_drive_folder_or_doc(cleaned):
        raise ValueError("Google Drive folders and docs are not supported. Use a shared video file link.")

    file_id = extract_google_drive_file_id(cleaned)
    if file_id:
        return SourceDetails(
            source_type="google_drive",
            normalized_url=f"https://drive.google.com/file/d/{file_id}/view",
            source_key=f"gdrive:{file_id}",
        )

    if is_youtube_playlist(cleaned):
        parsed = urlparse(cleaned)
        query = parse_qs(parsed.query)
        playlist_id = query.get("list", [""])[0]
        return SourceDetails(
            source_type="youtube_playlist",
            normalized_url=cleaned,
            source_key=f"youtube_playlist:{playlist_id}",
            is_playlist=True,
        )

    return SourceDetails(
        source_type="url",
        normalized_url=cleaned,
        source_key=f"url:{cleaned}",
    )


def preview_youtube_playlist(url: str) -> dict:
    result = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--dump-single-json", url],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout or "{}")
    entries = []
    for entry in payload.get("entries", []):
        video_id = entry.get("id")
        if not video_id:
            continue
        entries.append(
            {
                "id": video_id,
                "title": entry.get("title") or "Untitled video",
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "source_key": f"youtube:{video_id}",
            }
        )
    if not entries:
        raise ValueError("No playable videos were found in that playlist.")
    return {
        "title": payload.get("title") or "Playlist batch",
        "entries": entries,
        "source_key": f"youtube_playlist:{payload.get('id') or payload.get('playlist_id') or ''}",
    }


def expand_youtube_playlist(url: str) -> list[dict]:
    return preview_youtube_playlist(url)["entries"]
