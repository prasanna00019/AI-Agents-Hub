"""
Optional Gemini image generation helpers.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4


class ImageGenerationError(RuntimeError):
    pass


def ensure_image_key(api_key: str) -> str:
    resolved = (api_key or "").strip()
    if not resolved:
        raise ImageGenerationError("Gemini API key is not configured. Save it in Settings first.")
    return resolved


def build_image_prompt(*, topic: str, pillar: str, content: str, channel_name: str, platform: str) -> str:
    return (
        "Create a clean, modern editorial illustration inspired by the following post.\n"
        f"Channel: {channel_name}\n"
        f"Platform: {platform}\n"
        f"Pillar: {pillar}\n"
        f"Topic: {topic}\n\n"
        "Visual goals:\n"
        "- Strong single-scene concept\n"
        "- Professional, high-signal composition\n"
        "- No text rendered inside the image\n"
        "- Avoid logos or watermarks\n"
        "- Make the concept understandable for an AI/software audience\n\n"
        f"Post content:\n{content[:3000]}"
    )


def generate_image_bytes(api_key: str, prompt: str) -> Dict[str, Any]:
    ensure_image_key(api_key)
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise ImageGenerationError(f"Google GenAI SDK is not installed: {exc}") from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )

    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is not None and getattr(inline_data, "data", None):
                mime_type = getattr(inline_data, "mime_type", None) or "image/png"
                return {"bytes": inline_data.data, "mime_type": mime_type}

    raise ImageGenerationError("Gemini did not return image bytes.")


def persist_image_file(base_dir: Path, review_item_id: str, mime_type: str, content: bytes) -> Path:
    images_dir = base_dir / "generated-images"
    images_dir.mkdir(parents=True, exist_ok=True)
    extension = ".png"
    if "jpeg" in mime_type:
        extension = ".jpg"
    elif "webp" in mime_type:
        extension = ".webp"
    file_path = images_dir / f"{review_item_id}-{uuid4().hex}{extension}"
    file_path.write_bytes(content)
    return file_path


def image_metadata(record, base_dir: Path) -> Dict[str, Any]:
    path = Path(record.file_path)
    exists = path.exists()
    return {
        "id": record.id,
        "review_item_id": record.review_item_id,
        "prompt": record.prompt,
        "mime_type": record.mime_type,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "exists": exists,
        "download_url": f"/api/v1/review-queue/{record.review_item_id}/image/download" if exists else "",
        "relative_path": str(path.relative_to(base_dir)) if exists and path.is_relative_to(base_dir) else path.name,
    }
