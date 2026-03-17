from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from sqlalchemy import select, text

from src.backend.agents.graph import content_graph
from src.backend.core.config import settings
from src.backend.db.database import Base, get_engine, get_session_factory
from src.backend.models.content_models import (
    ChannelRecord,
    GenerationRunRecord,
    ReviewItemRecord,
    SourceDumpItemRecord,
)


_run_queues: Dict[str, asyncio.Queue] = {}


def get_run_queue(run_id: str) -> asyncio.Queue:
    if run_id not in _run_queues:
        _run_queues[run_id] = asyncio.Queue()
    return _run_queues[run_id]


def cleanup_run_queue(run_id: str) -> None:
    _run_queues.pop(run_id, None)


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


class ContentService:
    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parents[4]
        self._data_dir = base_dir / ".contentpilot"
        self._settings_file = self._data_dir / "settings.json"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        db_path = (self._data_dir / "contentpilot.db").absolute().as_posix()
        self._settings: Dict[str, str] = {
            "database_url": settings.DATABASE_URL or f"sqlite:///{db_path}",
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "default_ollama_model": settings.DEFAULT_OLLAMA_MODEL,
            "searxng_url": settings.SEARXNG_URL,
        }
        self._load_runtime_settings()

    def initialize_storage(self) -> None:
        db_url = self._settings.get("database_url")
        if not db_url or "CHANGE_ME" in db_url:
            return

        def _init() -> None:
            try:
                engine = get_engine(db_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                Base.metadata.create_all(
                    bind=engine,
                    tables=[
                        ChannelRecord.__table__,
                        ReviewItemRecord.__table__,
                        SourceDumpItemRecord.__table__,
                        GenerationRunRecord.__table__,
                    ],
                )
            except Exception as exc:
                print(f"Database initialization failed or deferred: {exc}")

        import threading

        threading.Thread(target=_init, daemon=True).start()

    def _load_runtime_settings(self) -> None:
        if not self._settings_file.exists():
            return

        try:
            persisted = json.loads(self._settings_file.read_text(encoding="utf-8"))
            self._settings.update({key: value for key, value in persisted.items() if value is not None})
        except Exception as exc:
            print(f"Error loading settings: {exc}")

    def _persist_runtime_settings(self) -> None:
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._settings_file.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"Error persisting settings: {exc}")

    @contextmanager
    def _session(self):
        factory = get_session_factory(self.ensure_database_configured())
        db = factory()
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

    @staticmethod
    def _serialize_run(record: GenerationRunRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "channel_id": record.channel_id,
            "status": record.status,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "logs": record.logs or [],
            "dates": record.dates or [],
            "error": record.error,
        }

    @staticmethod
    def _normalize_settings_update(key: str, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if key in {"ollama_base_url", "searxng_url"}:
            normalized = normalized.rstrip("/")
        return normalized

    def ensure_database_configured(self) -> str:
        database_url = (self._settings.get("database_url") or "").strip()
        if not database_url:
            raise ValueError("Database URL is not configured. Save it in Settings first.")
        return database_url

    def get_ollama_runtime_config(self, override_model: Optional[str] = None) -> Dict[str, str]:
        base_url = (self._settings.get("ollama_base_url") or "").rstrip("/")
        model_name = (override_model or self._settings.get("default_ollama_model") or "").strip()
        return {"base_url": base_url, "model_name": model_name}

    def validate_ollama_runtime_config(self, override_model: Optional[str] = None) -> Dict[str, str]:
        config = self.get_ollama_runtime_config(override_model)
        if not config["base_url"]:
            raise ValueError("Ollama Base URL is not configured. Save it in Settings first.")
        if not config["model_name"]:
            raise ValueError("Default Ollama model is not configured. Save it in Settings first.")
        return config

    def get_searxng_runtime_config(self) -> Dict[str, Any]:
        url = (self._settings.get("searxng_url") or "").strip().rstrip("/")
        if not url:
            return {"configured": False, "url": "", "port": None, "controllable": False}

        parsed = urlparse(url)
        port = parsed.port
        return {
            "configured": True,
            "url": url,
            "port": port,
            "controllable": port is not None,
        }

    def get_settings(self) -> Dict[str, str]:
        return self._settings.copy()

    def update_settings(self, updates: Dict[str, str]) -> Dict[str, str]:
        normalized_updates = {
            key: self._normalize_settings_update(key, value)
            for key, value in updates.items()
            if value is not None
        }
        self._settings.update(normalized_updates)
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
        resolved_base_url = (base_url or self._settings.get("ollama_base_url") or "").strip()
        if not resolved_base_url:
            return {
                "ok": False,
                "models": [],
                "base_url": "",
                "message": "Ollama Base URL is not configured.",
            }

        if resolved_base_url.rstrip("/").endswith("/api/tags"):
            url = resolved_base_url.rstrip("/")
            ollama_base_url = url[: -len("/api/tags")]
        else:
            ollama_base_url = resolved_base_url.rstrip("/")
            url = f"{ollama_base_url}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                payload = resp.json()
            models = [model.get("name") for model in payload.get("models", []) if model.get("name")]
            return {"ok": True, "models": models, "base_url": ollama_base_url}
        except Exception as exc:
            return {"ok": False, "models": [], "base_url": ollama_base_url, "message": str(exc)}

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
            rows = db.execute(select(ChannelRecord).order_by(ChannelRecord.created_at.desc())).scalars().all()
            return [self._serialize_channel(record) for record in rows]

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

    def delete_channel(self, channel_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ChannelRecord, channel_id)
            if not record:
                return False
            db.delete(record)
            return True

    def set_weekly_template(self, channel_id: str, weekly_template: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ChannelRecord, channel_id)
            if not record:
                return None
            record.weekly_template = weekly_template
            record.updated_at = datetime.utcnow()
            db.add(record)
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
                "mode": override.get("mode", "pre_generated"),
            }
            record.overrides = overrides
            record.updated_at = datetime.utcnow()
            db.add(record)
            return self._serialize_channel(record)

    def add_source_dump(self, channel_id: str, date_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.initialize_storage()
        record = SourceDumpItemRecord(
            id=str(uuid4()),
            channel_id=channel_id,
            date=date_key,
            type=payload.get("type", "text"),
            label=payload.get("label", ""),
            raw_content=payload.get("raw_content", ""),
            scraped_content=payload.get("scraped_content", ""),
            created_at=datetime.utcnow(),
        )
        with self._session() as db:
            db.add(record)
            return {
                "id": record.id,
                "channel_id": record.channel_id,
                "date": record.date,
                "type": record.type,
                "label": record.label,
                "raw_content": record.raw_content,
            }

    def list_source_dumps(self, channel_id: str, date_key: str) -> List[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            rows = db.execute(
                select(SourceDumpItemRecord).where(
                    SourceDumpItemRecord.channel_id == channel_id,
                    SourceDumpItemRecord.date == date_key,
                )
            ).scalars().all()
            return [
                {
                    "id": record.id,
                    "channel_id": record.channel_id,
                    "date": record.date,
                    "type": record.type,
                    "label": record.label,
                    "raw_content": record.raw_content,
                }
                for record in rows
            ]

    def delete_source_dump(self, dump_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(SourceDumpItemRecord, dump_id)
            if not record:
                return False
            db.delete(record)
            return True

    async def generate_day(
        self,
        channel_id: str,
        date_key: str,
        model: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ollama_config = self.validate_ollama_runtime_config(model)
        self.initialize_storage()

        with self._session() as db:
            channel = db.get(ChannelRecord, channel_id)
            if not channel:
                raise ValueError("Channel not found")
            channel_payload = self._serialize_channel(channel)

            source_rows = db.execute(
                select(SourceDumpItemRecord).where(
                    SourceDumpItemRecord.channel_id == channel_id,
                    SourceDumpItemRecord.date == date_key,
                )
            ).scalars().all()
            raw_sources = [record.raw_content for record in source_rows]

        day_dt = date.fromisoformat(date_key)
        day_key = day_dt.strftime("%A").lower()
        override = channel_payload.get("overrides", {}).get(date_key, {})
        pillar = override.get("pillar") or channel_payload.get("weekly_template", {}).get(day_key, "General")
        topic = override.get("topic") or f"{pillar} for {channel_payload['name']}"
        special_instructions = override.get("special_instructions", "")
        mode = override.get("mode", "pre_generated")

        state_input = {
            "channel": channel_payload,
            "item_date": date_key,
            "pillar": pillar,
            "topic": topic,
            "special_instructions": special_instructions,
            "mode": mode,
            "raw_sources": raw_sources if mode == "source_dump" else channel_payload.get("sources", []),
            "scraped_data": "",
            "summarized_context": "",
            "draft": "",
            "formatted_content": "",
            "quality_report": "",
            "error": "",
            "model": ollama_config["model_name"],
            "ollama_base_url": ollama_config["base_url"],
            "searx_url": (self._settings.get("searxng_url") or "").rstrip("/"),
            "agent_logs": [],
        }

        if run_id:
            queue = get_run_queue(run_id)
            await queue.put(
                {
                    "step": "pipeline",
                    "status": "running",
                    "message": f"Generating {date_key}: {topic}",
                    "date": date_key,
                }
            )

        result_state = await content_graph.ainvoke(state_input)

        if run_id:
            queue = get_run_queue(run_id)
            for log_entry in result_state.get("agent_logs") or []:
                log_entry["date"] = date_key
                await queue.put(log_entry)

        formatted = result_state.get("formatted_content", "") or result_state.get("draft", "")

        with self._session() as db:
            existing = db.execute(
                select(ReviewItemRecord).where(
                    ReviewItemRecord.channel_id == channel_id,
                    ReviewItemRecord.date == date_key,
                )
            ).scalar_one_or_none()

            now = datetime.utcnow()
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
            return self._serialize_review_item(record)

    async def generate_week(
        self, channel_id: str, start_date_str: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        self.validate_ollama_runtime_config(model)
        run_id = str(uuid4())

        self.initialize_storage()
        start_dt = date.fromisoformat(start_date_str)
        dates = [(start_dt + timedelta(days=index)).isoformat() for index in range(7)]

        with self._session() as db:
            run_record = GenerationRunRecord(
                id=run_id,
                channel_id=channel_id,
                status="queued",
                started_at=None,
                completed_at=None,
                logs=[],
                dates=dates,
                error="",
            )
            db.add(run_record)

        asyncio.create_task(self._run_week_generation(run_id, channel_id, dates, model))
        return {"run_id": run_id, "status": "queued", "dates": dates}

    async def _run_week_generation(
        self, run_id: str, channel_id: str, dates: List[str], model: Optional[str]
    ) -> None:
        queue = get_run_queue(run_id)

        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = "running"
                run.started_at = datetime.utcnow()
                db.add(run)

        await queue.put(
            {
                "step": "pipeline",
                "status": "running",
                "message": f"Starting generation for {len(dates)} days",
            }
        )

        error_message = ""
        generated = 0

        for date_key in dates:
            try:
                await queue.put(
                    {
                        "step": "pipeline",
                        "status": "running",
                        "message": f"Processing {date_key}...",
                        "date": date_key,
                    }
                )
                await self.generate_day(channel_id, date_key, model, run_id)
                generated += 1
            except Exception as exc:
                error_message += f"{date_key}: {exc}\n"
                await queue.put(
                    {
                        "step": "error",
                        "status": "error",
                        "message": str(exc),
                        "date": date_key,
                    }
                )

        final_status = "completed" if not error_message else "failed"
        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = final_status
                run.completed_at = datetime.utcnow()
                run.error = error_message
                db.add(run)

        await queue.put(
            {
                "step": "pipeline",
                "status": "done",
                "message": f"Completed: {generated}/{len(dates)} days generated",
            }
        )
        await queue.put(None)

    def get_generation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(GenerationRunRecord, run_id)
            return self._serialize_run(record) if record else None

    def list_review_items(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            query = select(ReviewItemRecord).order_by(ReviewItemRecord.date.asc())
            if channel_id:
                query = query.where(ReviewItemRecord.channel_id == channel_id)
            rows = db.execute(query).scalars().all()
            return [self._serialize_review_item(record) for record in rows]

    def update_review_item(self, item_id: str, updates: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ReviewItemRecord, item_id)
            if not record:
                return None
            if "content" in updates:
                record.content = updates["content"]
            if "status" in updates:
                record.status = updates["status"]
            record.updated_at = datetime.utcnow()
            db.add(record)
            return self._serialize_review_item(record)

    def delete_review_item(self, item_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ReviewItemRecord, item_id)
            if not record:
                return False
            db.delete(record)
            return True

    async def refine_review_item(
        self, item_id: str, instruction: str, model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        ollama_config = self.validate_ollama_runtime_config(model)
        self.initialize_storage()
        with self._session() as db:
            existing = db.get(ReviewItemRecord, item_id)
            if not existing:
                return None
            current_content = existing.content
            chat_history = list(existing.chat_history or [])

        prompt = (
            "You are refining content. Update the following post based on user instructions.\n\n"
            f"--- CURRENT CONTENT ---\n{current_content}\n\n"
            f"--- INSTRUCTION ---\n{instruction}\n\n"
            "Output ONLY the new refined post."
        )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{ollama_config['base_url']}/api/generate",
                    json={
                        "model": ollama_config["model_name"],
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                refined = resp.json().get("response", "").strip()

            with self._session() as db:
                record = db.get(ReviewItemRecord, item_id)
                if record:
                    record.content = refined
                    chat_history.append(
                        {
                            "instruction": instruction,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    record.chat_history = chat_history
                    record.updated_at = datetime.utcnow()
                    db.add(record)
                    db.flush()
                    return self._serialize_review_item(record)
        except Exception as exc:
            print(f"Refinement failed: {exc}")
        return None


content_service = ContentService()
