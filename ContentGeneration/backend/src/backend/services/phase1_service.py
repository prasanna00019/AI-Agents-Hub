from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from sqlalchemy import select, text

from src.backend.core.config import settings
from src.backend.db.database import Base, get_engine, get_session_factory
from src.backend.models.phase1_models import ChannelRecord, ReviewItemRecord
from src.backend.utils.formatting import format_for_platform


def _default_weekly_template() -> Dict[str, str]:
    return {
        "monday": "Concept Deep Dive",
        "tuesday": "Tool Spotlight",
        "wednesday": "AI News Highlight",
        "thursday": "Tutorial / How-To",
        "friday": "Opinion / Commentary",
        "saturday": "Case Study",
        "sunday": "Weekly Summary",
    }


class Phase1Service:
    def __init__(self) -> None:
        self._settings_file = Path(__file__).resolve().parents[3] / ".contentpilot" / "settings.json"
        self._settings: Dict[str, str] = {
            "database_url": settings.DATABASE_URL,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "default_ollama_model": settings.DEFAULT_OLLAMA_MODEL,
            "searxng_url": settings.SEARXNG_URL,
        }
        self._load_runtime_settings()

    def initialize_storage(self) -> None:
        engine = get_engine(self._settings["database_url"])
        Base.metadata.create_all(bind=engine, tables=[ChannelRecord.__table__, ReviewItemRecord.__table__])

    def _load_runtime_settings(self) -> None:
        if self._settings_file.exists():
            persisted = json.loads(self._settings_file.read_text(encoding="utf-8"))
            self._settings.update({key: value for key, value in persisted.items() if value})

    def _persist_runtime_settings(self) -> None:
        self._settings_file.parent.mkdir(parents=True, exist_ok=True)
        self._settings_file.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")

    @contextmanager
    def _session(self):
        session_factory = get_session_factory(self._settings["database_url"])
        db = session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _serialize_channel(record: ChannelRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "audience": record.audience,
            "tone": record.tone,
            "platform": record.platform,
            "language": record.language,
            "timezone": record.timezone,
            "sources": record.sources or [],
            "prompt_template": record.prompt_template,
            "weekly_template": record.weekly_template or _default_weekly_template(),
            "overrides": record.overrides or {},
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    @staticmethod
    def _serialize_review_item(record: ReviewItemRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "channel_id": record.channel_id,
            "date": record.date,
            "pillar": record.pillar,
            "topic": record.topic,
            "status": record.status,
            "content": record.content,
            "chat_history": record.chat_history or [],
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    def get_settings(self) -> Dict[str, str]:
        return self._settings.copy()

    def update_settings(self, updates: Dict[str, str]) -> Dict[str, str]:
        self._settings.update({key: value for key, value in updates.items() if value is not None})
        self.initialize_storage()
        self._persist_runtime_settings()
        return self.get_settings()

    def test_database_url(self, database_url: str) -> Dict[str, Any]:
        try:
            engine = get_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"ok": True, "message": "Database connection successful"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    async def list_ollama_models(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        if not base_url:
            url = "http://localhost:11434/api/tags"
            ollama_base_url = "http://localhost:11434"
        elif base_url.rstrip("/").endswith("/api/tags"):
            url = base_url.rstrip("/")
            ollama_base_url = url[: -len("/api/tags")]
        else:
            ollama_base_url = base_url.rstrip("/")
            url = f"{ollama_base_url}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()

            models = [m.get("name") for m in payload.get("models", []) if m.get("name")]
            if models and not self._settings.get("default_ollama_model"):
                self._settings["default_ollama_model"] = models[0]
                self._persist_runtime_settings()
            return {"ok": True, "models": models, "base_url": ollama_base_url}
        except Exception as exc:
            return {
                "ok": False,
                "models": [],
                "base_url": ollama_base_url,
                "message": str(exc),
            }

    def create_channel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.initialize_storage()
        now = datetime.utcnow()
        record = ChannelRecord(
            id=str(uuid4()),
            name=payload["name"],
            description=payload.get("description", ""),
            audience=payload.get("audience", ""),
            tone=payload.get("tone", "Educational"),
            platform=payload.get("platform", "whatsapp"),
            language=payload.get("language", "en"),
            timezone=payload.get("timezone", "UTC"),
            sources=payload.get("sources", []),
            prompt_template=payload.get("prompt_template", ""),
            weekly_template=payload.get("weekly_template") or _default_weekly_template(),
            overrides=payload.get("overrides", {}),
            created_at=now,
            updated_at=now,
        )
        with self._session() as db:
            db.add(record)
            db.flush()
            db.refresh(record)
            return self._serialize_channel(record)

    def list_channels(self) -> List[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            records = db.execute(select(ChannelRecord).order_by(ChannelRecord.created_at.desc())).scalars().all()
            return [self._serialize_channel(record) for record in records]

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ChannelRecord, channel_id)
            return self._serialize_channel(record) if record else None

    def update_channel(self, channel_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ChannelRecord, channel_id)
            if not record:
                return None

            for field in [
                "name",
                "description",
                "audience",
                "tone",
                "platform",
                "language",
                "timezone",
                "sources",
                "prompt_template",
            ]:
                if field in updates and updates[field] is not None:
                    setattr(record, field, updates[field])

            record.updated_at = datetime.utcnow()
            db.add(record)
            db.flush()
            db.refresh(record)
            return self._serialize_channel(record)

    def set_weekly_template(self, channel_id: str, weekly_template: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ChannelRecord, channel_id)
            if not record:
                return None
            record.weekly_template = weekly_template
            record.updated_at = datetime.utcnow()
            db.add(record)
            db.flush()
            db.refresh(record)
            return self._serialize_channel(record)

    def set_override(self, channel_id: str, date_key: str, override: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ChannelRecord, channel_id)
            if not record:
                return None

            overrides = dict(record.overrides or {})
            overrides[date_key] = {
                "pillar": override.get("pillar", ""),
                "topic": override.get("topic", ""),
                "special_instructions": override.get("special_instructions", ""),
            }
            record.overrides = overrides
            record.updated_at = datetime.utcnow()
            db.add(record)
            db.flush()
            db.refresh(record)
            return self._serialize_channel(record)

    async def _generate_with_ollama(self, prompt: str, model: Optional[str]) -> str:
        model_name = model or self._settings["default_ollama_model"]
        ollama_base_url = self._settings["ollama_base_url"].rstrip("/")
        url = f"{ollama_base_url}/api/generate"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    async def generate_week(self, channel_id: str, start_date_str: str, model: Optional[str]) -> List[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            channel = db.get(ChannelRecord, channel_id)
            if not channel:
                return []
            channel_payload = self._serialize_channel(channel)

        start_dt = date.fromisoformat(start_date_str)
        generated: List[Dict[str, Any]] = []

        for offset in range(7):
            day_dt = start_dt + timedelta(days=offset)
            day_key = day_dt.strftime("%A").lower()
            date_key = day_dt.isoformat()

            override = channel_payload.get("overrides", {}).get(date_key, {})
            pillar = override.get("pillar") or channel_payload.get("weekly_template", {}).get(day_key, "General")
            topic = override.get("topic") or f"{pillar} for {channel_payload['name']}"
            special_instructions = override.get("special_instructions", "")

            prompt = (
                f"You are writing content for the channel '{channel_payload['name']}'.\n"
                f"Platform: {channel_payload['platform']}\n"
                f"Audience: {channel_payload['audience']}\n"
                f"Tone: {channel_payload['tone']}\n"
                f"Language: {channel_payload['language']}\n"
                f"Pillar: {pillar}\n"
                f"Topic: {topic}\n"
                f"Sources: {', '.join(channel_payload.get('sources', [])[:8])}\n"
                f"Special instructions: {special_instructions}\n"
                f"Channel prompt template: {channel_payload.get('prompt_template', '')}\n"
                "Write one polished WhatsApp-ready post with a compelling opening, structured body, and clear closing CTA."
            )

            try:
                draft_text = await self._generate_with_ollama(prompt, model)
                if not draft_text:
                    raise ValueError("Empty response from Ollama")
            except Exception:
                draft_text = (
                    f"*{topic}*\n\n"
                    f"Today's focus: {pillar}.\n"
                    f"Ollama was unavailable, so this fallback draft is ready for editing.\n\n"
                    f"Use this as a starting point for your {channel_payload['platform']} channel."
                )

            formatted = format_for_platform(draft_text, channel_payload["platform"])
            now = datetime.utcnow()

            with self._session() as db:
                existing = db.execute(
                    select(ReviewItemRecord).where(
                        ReviewItemRecord.channel_id == channel_id,
                        ReviewItemRecord.date == date_key,
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.pillar = pillar
                    existing.topic = topic
                    existing.content = formatted
                    existing.status = "draft"
                    existing.updated_at = now
                    record = existing
                else:
                    record = ReviewItemRecord(
                        id=str(uuid4()),
                        channel_id=channel_id,
                        date=date_key,
                        pillar=pillar,
                        topic=topic,
                        status="draft",
                        content=formatted,
                        chat_history=[],
                        created_at=now,
                        updated_at=now,
                    )

                db.add(record)
                db.flush()
                db.refresh(record)
                generated.append(self._serialize_review_item(record))

        return generated

    def list_review_items(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            query = select(ReviewItemRecord).order_by(ReviewItemRecord.date.asc())
            if channel_id:
                query = query.where(ReviewItemRecord.channel_id == channel_id)
            records = db.execute(query).scalars().all()
            return [self._serialize_review_item(record) for record in records]

    def update_review_item(self, item_id: str, updates: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ReviewItemRecord, item_id)
            if not record:
                return None
            if "content" in updates and updates["content"] is not None:
                record.content = updates["content"]
            if "status" in updates and updates["status"] is not None:
                record.status = updates["status"]
            record.updated_at = datetime.utcnow()
            db.add(record)
            db.flush()
            db.refresh(record)
            return self._serialize_review_item(record)

    async def refine_review_item(self, item_id: str, instruction: str, model: Optional[str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            existing = db.get(ReviewItemRecord, item_id)
            if not existing:
                return None
            current_content = existing.content
            channel_id = existing.channel_id

        with self._session() as db:
            channel = db.get(ChannelRecord, channel_id)
            if not channel:
                return None
            channel_platform = channel.platform

        prompt = (
            "Refine the following WhatsApp post based on the user instruction.\n\n"
            f"Current post:\n{current_content}\n\n"
            f"Instruction:\n{instruction}\n\n"
            "Return only the final revised post."
        )

        try:
            refined = await self._generate_with_ollama(prompt, model)
            if not refined:
                raise ValueError("Empty response from Ollama")
        except Exception:
            refined = f"{current_content}\n\nRefinement note: {instruction}"

        with self._session() as db:
            record = db.get(ReviewItemRecord, item_id)
            if not record:
                return None
            chat_history = list(record.chat_history or [])
            chat_history.append(
                {
                    "instruction": instruction,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            record.content = format_for_platform(refined, channel_platform)
            record.chat_history = chat_history
            record.updated_at = datetime.utcnow()
            db.add(record)
            db.flush()
            db.refresh(record)
            return self._serialize_review_item(record)


phase1_service = Phase1Service()
