from __future__ import annotations

import asyncio
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
from src.backend.models.content_models import (
    ChannelRecord,
    GenerationRunRecord,
    ReviewItemRecord,
    SourceDumpItemRecord,
)
from src.backend.utils.formatting import format_for_platform
from src.backend.agents.graph import content_graph


# ---------------------------------------------------------------------------
# In-memory run event queues for SSE streaming
# ---------------------------------------------------------------------------
_run_queues: Dict[str, asyncio.Queue] = {}


def get_run_queue(run_id: str) -> asyncio.Queue:
    if run_id not in _run_queues:
        _run_queues[run_id] = asyncio.Queue()
    return _run_queues[run_id]


def cleanup_run_queue(run_id: str) -> None:
    _run_queues.pop(run_id, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ContentService:
    def __init__(self) -> None:
        self._settings_file = Path(__file__).resolve().parents[3] / ".contentpilot" / "settings.json"
        self._settings: Dict[str, str] = {
            "database_url": settings.DATABASE_URL,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "default_ollama_model": settings.DEFAULT_OLLAMA_MODEL,
            "searxng_url": settings.SEARXNG_URL,
        }
        self._load_runtime_settings()

    # ── Storage init ──────────────────────────────────────────────────────

    def initialize_storage(self) -> None:
        engine = get_engine(self._settings["database_url"])
        Base.metadata.create_all(
            bind=engine,
            tables=[
                ChannelRecord.__table__,
                ReviewItemRecord.__table__,
                SourceDumpItemRecord.__table__,
                GenerationRunRecord.__table__,
            ],
        )

    # ── Settings persistence ──────────────────────────────────────────────

    def _load_runtime_settings(self) -> None:
        if self._settings_file.exists():
            persisted = json.loads(self._settings_file.read_text(encoding="utf-8"))
            self._settings.update({k: v for k, v in persisted.items() if v})

    def _persist_runtime_settings(self) -> None:
        self._settings_file.parent.mkdir(parents=True, exist_ok=True)
        self._settings_file.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")

    # ── DB session ────────────────────────────────────────────────────────

    @contextmanager
    def _session(self):
        factory = get_session_factory(self._settings["database_url"])
        db = factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── Serializers ───────────────────────────────────────────────────────

    @staticmethod
    def _serialize_channel(r: ChannelRecord) -> Dict[str, Any]:
        return {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "audience": r.audience,
            "tone": r.tone,
            "platform": r.platform,
            "language": r.language,
            "timezone": r.timezone,
            "sources": r.sources or [],
            "prompt_template": r.prompt_template,
            "weekly_template": r.weekly_template or _default_weekly_template(),
            "overrides": r.overrides or {},
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }

    @staticmethod
    def _serialize_review_item(r: ReviewItemRecord) -> Dict[str, Any]:
        return {
            "id": r.id,
            "channel_id": r.channel_id,
            "date": r.date,
            "pillar": r.pillar,
            "topic": r.topic,
            "status": r.status,
            "content": r.content,
            "chat_history": r.chat_history or [],
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }

    @staticmethod
    def _serialize_run(r: GenerationRunRecord) -> Dict[str, Any]:
        return {
            "id": r.id,
            "channel_id": r.channel_id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "logs": r.logs or [],
            "dates": r.dates or [],
            "error": r.error,
        }

    # ── Settings API ──────────────────────────────────────────────────────

    def get_settings(self) -> Dict[str, str]:
        return self._settings.copy()

    def update_settings(self, updates: Dict[str, str]) -> Dict[str, str]:
        self._settings.update({k: v for k, v in updates.items() if v is not None})
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
                resp = await client.get(url)
                resp.raise_for_status()
                payload = resp.json()
            models = [m.get("name") for m in payload.get("models", []) if m.get("name")]
            return {"ok": True, "models": models, "base_url": ollama_base_url}
        except Exception as exc:
            return {"ok": False, "models": [], "base_url": ollama_base_url, "message": str(exc)}

    # ── Channels ──────────────────────────────────────────────────────────

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
            return [self._serialize_channel(r) for r in rows]

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ChannelRecord, channel_id)
            return self._serialize_channel(r) if r else None

    def update_channel(self, channel_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ChannelRecord, channel_id)
            if not r:
                return None
            for f in ["name", "description", "audience", "tone", "platform", "language", "timezone", "sources", "prompt_template"]:
                if f in updates and updates[f] is not None:
                    setattr(r, f, updates[f])
            r.updated_at = datetime.utcnow()
            db.add(r)
            db.flush()
            db.refresh(r)
            return self._serialize_channel(r)

    def delete_channel(self, channel_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ChannelRecord, channel_id)
            if not r:
                return False
            db.delete(r)
            return True

    def set_weekly_template(self, channel_id: str, weekly_template: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ChannelRecord, channel_id)
            if not r:
                return None
            r.weekly_template = weekly_template
            r.updated_at = datetime.utcnow()
            db.add(r)
            return self._serialize_channel(r)

    def set_override(self, channel_id: str, date_key: str, override: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ChannelRecord, channel_id)
            if not r:
                return None
            overrides = dict(r.overrides or {})
            overrides[date_key] = {
                "pillar": override.get("pillar", ""),
                "topic": override.get("topic", ""),
                "special_instructions": override.get("special_instructions", ""),
                "mode": override.get("mode", "pre_generated"),
            }
            r.overrides = overrides
            r.updated_at = datetime.utcnow()
            db.add(r)
            return self._serialize_channel(r)

    # ── Source Dumps ──────────────────────────────────────────────────────

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
                    "id": r.id,
                    "channel_id": r.channel_id,
                    "date": r.date,
                    "type": r.type,
                    "label": r.label,
                    "raw_content": r.raw_content,
                }
                for r in rows
            ]

    def delete_source_dump(self, dump_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(SourceDumpItemRecord, dump_id)
            if not r:
                return False
            db.delete(r)
            return True

    # ── Generation (core engine) ──────────────────────────────────────────

    async def generate_day(
        self,
        channel_id: str,
        date_key: str,
        model: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate content for a single day using the LangGraph pipeline."""
        self.initialize_storage()

        with self._session() as db:
            channel = db.get(ChannelRecord, channel_id)
            if not channel:
                raise ValueError("Channel not found")
            channel_payload = self._serialize_channel(channel)

            # Get source dumps for source_dump mode
            source_rows = db.execute(
                select(SourceDumpItemRecord).where(
                    SourceDumpItemRecord.channel_id == channel_id,
                    SourceDumpItemRecord.date == date_key,
                )
            ).scalars().all()
            raw_sources = [r.raw_content for r in source_rows]

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
            "model": model or self._settings.get("default_ollama_model"),
            "ollama_base_url": self._settings.get("ollama_base_url"),
            "searx_url": self._settings.get("searxng_url"),
            "agent_logs": [],
        }

        # Push initial event to SSE queue
        if run_id:
            q = get_run_queue(run_id)
            await q.put({"step": "pipeline", "status": "running", "message": f"Generating {date_key}: {topic}", "date": date_key})

        # Run the LangGraph pipeline
        result_state = await content_graph.ainvoke(state_input)

        # Push step logs to SSE queue
        if run_id:
            for log_entry in (result_state.get("agent_logs") or []):
                log_entry["date"] = date_key
                await q.put(log_entry)

        formatted = result_state.get("formatted_content", "") or result_state.get("draft", "")

        # Persist review item
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
        """Launch async week generation and return a run_id."""
        run_id = str(uuid4())

        # Create run record
        self.initialize_storage()
        start_dt = date.fromisoformat(start_date_str)
        dates = [(start_dt + timedelta(days=i)).isoformat() for i in range(7)]

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

        # Launch background task
        asyncio.create_task(self._run_week_generation(run_id, channel_id, dates, model))

        return {"run_id": run_id, "status": "queued", "dates": dates}

    async def _run_week_generation(
        self, run_id: str, channel_id: str, dates: List[str], model: Optional[str]
    ) -> None:
        """Background task that generates content for each day."""
        q = get_run_queue(run_id)

        # Mark as running
        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = "running"
                run.started_at = datetime.utcnow()
                db.add(run)

        await q.put({"step": "pipeline", "status": "running", "message": f"Starting generation for {len(dates)} days"})

        all_logs: List[Dict[str, Any]] = []
        error_msg = ""
        generated = 0

        for date_key in dates:
            try:
                await q.put({"step": "pipeline", "status": "running", "message": f"Processing {date_key}…", "date": date_key})
                await self.generate_day(channel_id, date_key, model, run_id)
                generated += 1
            except Exception as e:
                error_msg += f"{date_key}: {e}\n"
                await q.put({"step": "error", "status": "error", "message": str(e), "date": date_key})

        # Mark as completed
        final_status = "completed" if not error_msg else "failed"
        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = final_status
                run.completed_at = datetime.utcnow()
                run.error = error_msg
                db.add(run)

        await q.put({
            "step": "pipeline",
            "status": "done",
            "message": f"Completed: {generated}/{len(dates)} days generated",
        })

        # Signal end of stream
        await q.put(None)

    def get_generation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(GenerationRunRecord, run_id)
            return self._serialize_run(r) if r else None

    # ── Review Queue ──────────────────────────────────────────────────────

    def list_review_items(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            q = select(ReviewItemRecord).order_by(ReviewItemRecord.date.asc())
            if channel_id:
                q = q.where(ReviewItemRecord.channel_id == channel_id)
            rows = db.execute(q).scalars().all()
            return [self._serialize_review_item(r) for r in rows]

    def update_review_item(self, item_id: str, updates: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ReviewItemRecord, item_id)
            if not r:
                return None
            if "content" in updates:
                r.content = updates["content"]
            if "status" in updates:
                r.status = updates["status"]
            r.updated_at = datetime.utcnow()
            db.add(r)
            return self._serialize_review_item(r)

    def delete_review_item(self, item_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            r = db.get(ReviewItemRecord, item_id)
            if not r:
                return False
            db.delete(r)
            return True

    async def refine_review_item(
        self, item_id: str, instruction: str, model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
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

        ollama_url = (self._settings.get("ollama_base_url") or settings.OLLAMA_BASE_URL).rstrip("/")
        model_name = model or self._settings.get("default_ollama_model") or settings.DEFAULT_OLLAMA_MODEL

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": model_name, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                refined = resp.json().get("response", "").strip()

            with self._session() as db:
                r = db.get(ReviewItemRecord, item_id)
                if r:
                    r.content = refined
                    chat_history.append({"instruction": instruction, "timestamp": datetime.utcnow().isoformat()})
                    r.chat_history = chat_history
                    r.updated_at = datetime.utcnow()
                    db.add(r)
                    db.flush()
                    return self._serialize_review_item(r)
        except Exception as e:
            print(f"Refinement failed: {e}")
        return None


content_service = ContentService()
