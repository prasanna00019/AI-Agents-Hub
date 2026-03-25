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
from sqlalchemy import inspect, select, text

from agents.graph import content_graph
from core.config import settings
from db.database import Base, get_engine, get_session_factory
from models.content_models import (
    ChannelRecord,
    GenerationRunRecord,
    MemoryRecord,
    ReviewImageRecord,
    ReviewItemRecord,
    SourceDumpItemRecord,
)
from services.image_service import (
    ImageGenerationError,
    build_image_prompt,
    generate_image_bytes,
    image_metadata,
    persist_image_file,
)
from services.memory_service import MemoryService
from services.research_pipeline import collect_research_material, search_searxng
from services.run_events import emit_run_event, get_run_queue


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
        base_dir = Path(__file__).resolve().parents[2]
        self._project_dir = base_dir
        self._data_dir = base_dir / ".contentpilot"
        self._settings_file = self._data_dir / "settings.json"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        db_path = (self._data_dir / "contentpilot.db").absolute().as_posix()
        self._settings: Dict[str, Any] = {
            "database_url": settings.DATABASE_URL or f"sqlite:///{db_path}",
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "default_ollama_model": settings.DEFAULT_OLLAMA_MODEL,
            "searxng_url": settings.SEARXNG_URL,
            "searxng_categories": "general",
            "searxng_max_results": 4,
            "searxng_time_range": "any",
            "gemini_api_key": "",
        }
        self._load_runtime_settings()
        self._memory = MemoryService(get_db_url_fn=self.ensure_database_configured)

    def initialize_storage(self) -> None:
        db_url = self._settings.get("database_url")
        if not db_url or "CHANGE_ME" in str(db_url):
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
                        ReviewImageRecord.__table__,
                        SourceDumpItemRecord.__table__,
                        GenerationRunRecord.__table__,
                        MemoryRecord.__table__,
                    ],
                )
                self._run_schema_migrations(engine)
            except Exception as exc:
                print(f"Database initialization failed or deferred: {exc}")

        import threading

        threading.Thread(target=_init, daemon=True).start()

    @staticmethod
    def _run_schema_migrations(engine) -> None:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        if "review_items" in table_names:
            existing_columns = {column["name"] for column in inspector.get_columns("review_items")}
            dialect = engine.dialect.name
            statements: list[str] = []

            if "generation_context" not in existing_columns:
                statements.append(
                    "ALTER TABLE review_items ADD COLUMN generation_context TEXT NOT NULL DEFAULT ''"
                )

            if "source_urls" not in existing_columns:
                if dialect == "postgresql":
                    statements.append(
                        "ALTER TABLE review_items ADD COLUMN source_urls JSON NOT NULL DEFAULT '[]'::json"
                    )
                else:
                    statements.append(
                        "ALTER TABLE review_items ADD COLUMN source_urls JSON NOT NULL DEFAULT '[]'"
                    )

            if statements:
                with engine.begin() as conn:
                    for statement in statements:
                        conn.execute(text(statement))

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

    # ── Serialisers ──────────────────────────────────────────────────

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
            "context_notes": record.context_notes or "",
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
            "platform": record.platform or "whatsapp",
            "status": record.status,
            "content": record.content,
            "chat_history": record.chat_history or [],
            "source_urls": record.source_urls or [],
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

    @staticmethod
    def _mask_settings(data: Dict[str, Any]) -> Dict[str, Any]:
        masked = dict(data)
        if masked.get("gemini_api_key"):
            masked["gemini_api_key"] = "configured"
        return masked

    async def _ollama_generate(self, prompt: str, model: Optional[str] = None, timeout: float = 120.0) -> str:
        config = self.validate_ollama_runtime_config(model)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{config['base_url']}/api/generate",
                json={"model": config["model_name"], "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()

    @staticmethod
    def _looks_like_topic(value: str) -> str:
        text = " ".join((value or "").replace('"', "").split())
        if not text:
            return ""
        return text.splitlines()[0].strip(" -:*")[:160]

    @staticmethod
    def _instruction_needs_research(instruction: str) -> bool:
        lowered = instruction.lower()
        triggers = [
            "update",
            "latest",
            "current",
            "new source",
            "new sources",
            "fact-check",
            "fact check",
            "verify",
            "research",
            "search",
            "add data",
            "add stats",
        ]
        return any(token in lowered for token in triggers)

    # ── DB / config helpers ──────────────────────────────────────────

    def ensure_database_configured(self) -> str:
        database_url = str(self._settings.get("database_url") or "").strip()
        if not database_url:
            raise ValueError("Database URL is not configured. Save it in Settings first.")
        return database_url

    def get_ollama_runtime_config(self, override_model: Optional[str] = None) -> Dict[str, str]:
        base_url = str(self._settings.get("ollama_base_url") or "").rstrip("/")
        model_name = (override_model or str(self._settings.get("default_ollama_model") or "")).strip()
        return {"base_url": base_url, "model_name": model_name}

    def validate_ollama_runtime_config(self, override_model: Optional[str] = None) -> Dict[str, str]:
        config = self.get_ollama_runtime_config(override_model)
        if not config["base_url"]:
            raise ValueError("Ollama Base URL is not configured. Save it in Settings first.")
        if not config["model_name"]:
            raise ValueError("Default Ollama model is not configured. Save it in Settings first.")
        return config

    def get_searxng_runtime_config(self) -> Dict[str, Any]:
        url = str(self._settings.get("searxng_url") or "").strip().rstrip("/")
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

    # ── Settings ─────────────────────────────────────────────────────

    def get_settings(self) -> Dict[str, Any]:
        return self._mask_settings({key: value for key, value in self._settings.items()})

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
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
        resolved_base_url = (base_url or str(self._settings.get("ollama_base_url") or "")).strip()
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

    # ── Channels ─────────────────────────────────────────────────────

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
            context_notes=payload.get("context_notes", ""),
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
                "context_notes",
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
                "search_additional": override.get("search_additional", True),
                "suggest_new_topic": override.get("suggest_new_topic", False),
            }
            record.overrides = overrides
            record.updated_at = datetime.utcnow()
            db.add(record)
            return self._serialize_channel(record)

    # ── Source Dumps ─────────────────────────────────────────────────

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

    def get_source_dump_counts(self, channel_id: str) -> Dict[str, int]:
        """Return a map of date -> dump count for all dates that have dumps."""
        self.initialize_storage()
        with self._session() as db:
            rows = db.execute(
                select(SourceDumpItemRecord.date)
                .where(SourceDumpItemRecord.channel_id == channel_id)
            ).scalars().all()
            counts: Dict[str, int] = {}
            for d in rows:
                counts[d] = counts.get(d, 0) + 1
            return counts

    def delete_source_dump(self, dump_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(SourceDumpItemRecord, dump_id)
            if not record:
                return False
            db.delete(record)
            return True

    # ── Generation ───────────────────────────────────────────────────

    def _create_generation_run(self, channel_id: str, dates: List[str]) -> Dict[str, Any]:
        run_id = str(uuid4())
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
        return {"run_id": run_id, "status": "queued", "dates": dates}

    async def _resolve_generation_topic(
        self,
        channel_payload: Dict[str, Any],
        channel_id: str,
        pillar: str,
        explicit_topic: str,
        suggest_new_topic: bool,
    ) -> str:
        explicit = self._looks_like_topic(explicit_topic)
        if explicit and not suggest_new_topic:
            return explicit

        recent_topics = self._memory.get_recent_topic_labels(channel_id, limit=12)
        search_notes = ""
        searx_url = str(self._settings.get("searxng_url") or "").rstrip("/")
        if suggest_new_topic and searx_url:
            query = f"{channel_payload.get('audience', '')} {pillar} AI topic ideas".strip()
            try:
                results = await search_searxng(
                    searx_url,
                    query,
                    limit=min(int(self._settings.get("searxng_max_results", 4)), 5),
                    categories=str(self._settings.get("searxng_categories", "general")) or None,
                    time_range=str(self._settings.get("searxng_time_range", "any")) or None,
                )
                if results:
                    search_notes = "\n".join(
                        f"- {result.get('title')}: {result.get('snippet')}"
                        for result in results
                        if result.get("title") or result.get("snippet")
                    )
            except Exception as exc:
                print(f"Topic search failed: {exc}")

        prompt = (
            "Choose one concrete content topic for the channel below.\n"
            "Return only the final topic title, with no bullets or explanation.\n\n"
            f"Channel: {channel_payload.get('name')}\n"
            f"Audience: {channel_payload.get('audience')}\n"
            f"Tone: {channel_payload.get('tone')}\n"
            f"Pillar: {pillar}\n"
            f"Persistent notes: {channel_payload.get('context_notes', '')}\n"
        )
        if explicit:
            prompt += f"Starting topic hint: {explicit}\n"
        if recent_topics:
            prompt += "Avoid repeating these recent topics:\n" + "\n".join(f"- {topic}" for topic in recent_topics) + "\n"
        if search_notes:
            prompt += f"Fresh search ideas and signals:\n{search_notes}\n"
        prompt += "Make the topic specific, new-feeling, and usable for one post."

        try:
            resolved = self._looks_like_topic(await self._ollama_generate(prompt, timeout=60.0))
            if resolved:
                return resolved
        except Exception as exc:
            print(f"Topic resolution failed: {exc}")

        if explicit:
            return explicit
        return f"{pillar}: a fresh angle for {channel_payload.get('name', 'the channel')}"

    async def start_day_generation(
        self,
        channel_id: str,
        date_key: str,
        model: Optional[str] = None,
        search_additional: bool = True,
        suggest_new_topic: bool = False,
    ) -> Dict[str, Any]:
        self.validate_ollama_runtime_config(model)
        self.initialize_storage()
        run_data = self._create_generation_run(channel_id, [date_key])
        asyncio.create_task(
            self._run_day_generation(
                run_data["run_id"],
                channel_id,
                date_key,
                model,
                search_additional,
                suggest_new_topic,
            )
        )
        return run_data

    async def generate_day(
        self,
        channel_id: str,
        date_key: str,
        model: Optional[str] = None,
        run_id: Optional[str] = None,
        search_additional: bool = True,
        suggest_new_topic: bool = False,
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
            date_sources = [record.raw_content for record in source_rows if record.raw_content]

        day_dt = date.fromisoformat(date_key)
        day_key = day_dt.strftime("%A").lower()
        override = channel_payload.get("overrides", {}).get(date_key, {})
        pillar = override.get("pillar") or channel_payload.get("weekly_template", {}).get(day_key, "General")
        special_instructions = override.get("special_instructions", "")
        mode = override.get("mode", "pre_generated")
        override_search = override.get("search_additional", True)
        suggest_new_topic = bool(override.get("suggest_new_topic", False) or suggest_new_topic)
        topic = await self._resolve_generation_topic(
            channel_payload=channel_payload,
            channel_id=channel_id,
            pillar=pillar,
            explicit_topic=override.get("topic", ""),
            suggest_new_topic=suggest_new_topic,
        )
        raw_sources = date_sources if mode == "source_dump" else [*(channel_payload.get("sources") or []), *date_sources]

        # Build memory context
        memory_context = self._memory.build_memory_context(
            channel_id=channel_id,
            context_notes=channel_payload.get("context_notes", ""),
            topic=topic,
        )

        # SearXNG search preferences
        searxng_categories = str(self._settings.get("searxng_categories", "general"))
        searxng_time_range = str(self._settings.get("searxng_time_range", "any"))
        searxng_max_results = int(self._settings.get("searxng_max_results", 4))

        if run_id:
            await emit_run_event(
                run_id,
                {
                    "step": "pipeline",
                    "status": "running",
                    "message": f"Generating {date_key}: {topic}",
                    "date": date_key,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        state_input = {
            "channel": channel_payload,
            "item_date": date_key,
            "pillar": pillar,
            "topic": topic,
            "special_instructions": special_instructions,
            "mode": mode,
            "raw_sources": raw_sources,
            "research_documents": [],
            "scraped_data": "",
            "summarized_context": "",
            "draft": "",
            "formatted_content": "",
            "quality_report": "",
            "error": "",
            "model": ollama_config["model_name"],
            "ollama_base_url": ollama_config["base_url"],
            "searx_url": str(self._settings.get("searxng_url") or "").rstrip("/"),
            "search_additional": search_additional and override_search,
            "searxng_categories": searxng_categories,
            "searxng_time_range": searxng_time_range,
            "searxng_max_results": searxng_max_results,
            "memory_context": memory_context,
            "run_id": run_id,
            "agent_logs": [],
        }

        result_state = await content_graph.ainvoke(state_input)
        formatted = result_state.get("formatted_content", "") or result_state.get("draft", "")
        generation_context = result_state.get("summarized_context", "") or result_state.get("scraped_data", "")
        source_urls = result_state.get("source_urls", []) or []

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
                existing.platform = channel_payload.get("platform", "whatsapp")
                existing.content = formatted
                existing.generation_context = generation_context
                existing.source_urls = source_urls
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
                    platform=channel_payload.get("platform", "whatsapp"),
                    status="draft",
                    content=formatted,
                    chat_history=[],
                    generation_context=generation_context,
                    source_urls=source_urls,
                    created_at=now,
                    updated_at=now,
                )
            db.add(record)
            db.flush()
            return self._serialize_review_item(record)

    async def _run_day_generation(
        self,
        run_id: str,
        channel_id: str,
        date_key: str,
        model: Optional[str],
        search_additional: bool = True,
        suggest_new_topic: bool = False,
    ) -> None:
        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = "running"
                run.started_at = datetime.utcnow()
                db.add(run)

        error_message = ""
        try:
            await self.generate_day(channel_id, date_key, model, run_id, search_additional, suggest_new_topic)
            await emit_run_event(
                run_id,
                {
                    "step": "pipeline",
                    "status": "done",
                    "message": f"Completed generation for {date_key}",
                    "date": date_key,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            final_status = "completed"
        except Exception as exc:
            error_message = str(exc)
            final_status = "failed"
            await emit_run_event(
                run_id,
                {
                    "step": "error",
                    "status": "error",
                    "message": str(exc),
                    "date": date_key,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        finally:
            with self._session() as db:
                run = db.get(GenerationRunRecord, run_id)
                if run:
                    run.status = final_status
                    run.completed_at = datetime.utcnow()
                    run.error = error_message
                    db.add(run)
            await get_run_queue(run_id).put(None)

    async def generate_week(
        self, channel_id: str, start_date_str: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        self.validate_ollama_runtime_config(model)
        self.initialize_storage()
        start_dt = date.fromisoformat(start_date_str)
        dates = [(start_dt + timedelta(days=index)).isoformat() for index in range(7)]
        run_data = self._create_generation_run(channel_id, dates)
        asyncio.create_task(self._run_week_generation(run_data["run_id"], channel_id, dates, model))
        return run_data

    async def _run_week_generation(
        self, run_id: str, channel_id: str, dates: List[str], model: Optional[str]
    ) -> None:
        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = "running"
                run.started_at = datetime.utcnow()
                db.add(run)

        await emit_run_event(
            run_id,
            {
                "step": "pipeline",
                "status": "running",
                "message": f"Starting generation for {len(dates)} day(s)",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        error_message = ""
        generated = 0

        for date_key in dates:
            try:
                await self.generate_day(channel_id, date_key, model, run_id)
                generated += 1
            except Exception as exc:
                error_message += f"{date_key}: {exc}\n"
                await emit_run_event(
                    run_id,
                    {
                        "step": "error",
                        "status": "error",
                        "message": str(exc),
                        "date": date_key,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

        final_status = "completed" if not error_message else "failed"
        with self._session() as db:
            run = db.get(GenerationRunRecord, run_id)
            if run:
                run.status = final_status
                run.completed_at = datetime.utcnow()
                run.error = error_message
                db.add(run)

        await emit_run_event(
            run_id,
            {
                "step": "pipeline",
                "status": "done",
                "message": f"Completed: {generated}/{len(dates)} day(s) generated",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        await get_run_queue(run_id).put(None)

    def get_generation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.get(GenerationRunRecord, run_id)
            return self._serialize_run(record) if record else None

    # ── Review Queue ─────────────────────────────────────────────────

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
            old_status = record.status
            if "status" in updates:
                record.status = updates["status"]
            record.updated_at = datetime.utcnow()
            db.add(record)

            # Episodic memory: when a post is marked "ready", store it
            if updates.get("status") == "ready" and old_status != "ready":
                content_snippet = (record.content or "")[:300]
                try:
                    self._memory.store_episodic_memory(
                        channel_id=record.channel_id,
                        topic=record.topic or "",
                        pillar=record.pillar or "",
                        content_summary=content_snippet,
                        date=record.date,
                    )
                except Exception as exc:
                    print(f"Failed to store episodic memory: {exc}")

            return self._serialize_review_item(record)

    def delete_review_item(self, item_id: str) -> bool:
        self.initialize_storage()
        with self._session() as db:
            image_record = db.execute(
                select(ReviewImageRecord).where(ReviewImageRecord.review_item_id == item_id)
            ).scalar_one_or_none()
            if image_record:
                try:
                    Path(image_record.file_path).unlink(missing_ok=True)
                except Exception:
                    pass
                db.delete(image_record)
            record = db.get(ReviewItemRecord, item_id)
            if not record:
                return False
            db.delete(record)
            return True

    async def refine_review_item(
        self, item_id: str, instruction: str, model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        self.validate_ollama_runtime_config(model)
        self.initialize_storage()
        with self._session() as db:
            record = db.get(ReviewItemRecord, item_id)
            if not record:
                return None
            channel = db.get(ChannelRecord, record.channel_id)
            if not channel:
                return None
            source_rows = db.execute(
                select(SourceDumpItemRecord).where(
                    SourceDumpItemRecord.channel_id == record.channel_id,
                    SourceDumpItemRecord.date == record.date,
                )
            ).scalars().all()

            current_content = record.content
            chat_history = list(record.chat_history or [])
            channel_id = record.channel_id
            record_topic = record.topic or ""
            record_pillar = record.pillar or ""
            generation_context = record.generation_context or ""
            source_urls = list(record.source_urls or [])
            channel_payload = self._serialize_channel(channel)
            raw_sources = [*(channel.sources or []), *source_urls, *[row.raw_content for row in source_rows if row.raw_content]]

        needs_research = self._instruction_needs_research(instruction)
        refined_context = generation_context
        if needs_research:
            research = await collect_research_material(
                topic=record_topic or record_pillar or channel_payload["name"],
                raw_sources=raw_sources,
                searx_url=str(self._settings.get("searxng_url") or "").rstrip("/"),
                mode="pre_generated",
                search_additional=True,
                searxng_categories=str(self._settings.get("searxng_categories", "general")),
                searxng_time_range=str(self._settings.get("searxng_time_range", "any")),
                searxng_max_results=int(self._settings.get("searxng_max_results", 4)),
            )
            refined_context = research.get("combined_text", "") or generation_context
            merged_urls: List[str] = []
            seen: set[str] = set()
            for value in [*source_urls, *(research.get("provided_urls") or []), *(research.get("new_search_urls") or [])]:
                normalized = (value or "").strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    merged_urls.append(normalized)
            source_urls = merged_urls

        memory_context = self._memory.build_memory_context(
            channel_id=channel_id,
            context_notes=channel_payload.get("context_notes", ""),
            topic=record_topic or record_pillar or "",
        )
        chat_lines = "\n".join(
            f"- {entry.get('instruction', '')}"
            for entry in chat_history[-6:]
            if entry.get("instruction")
        )
        prompt = (
            "You are refining a previously generated post.\n"
            "Use the current post, source context, channel memory, and the latest instruction.\n"
            "Return only the revised post.\n\n"
            f"Channel: {channel_payload.get('name')}\n"
            f"Audience: {channel_payload.get('audience')}\n"
            f"Tone: {channel_payload.get('tone')}\n"
            f"Platform: {channel_payload.get('platform')}\n"
            f"Pillar: {record_pillar}\n"
            f"Topic: {record_topic}\n\n"
            f"--- CURRENT CONTENT ---\n{current_content}\n\n"
            f"--- ORIGINAL / BEST AVAILABLE CONTEXT ---\n{refined_context[:9000]}\n\n"
            f"--- CHANNEL MEMORY ---\n{memory_context}\n\n"
        )
        if chat_lines:
            prompt += f"--- PRIOR REFINEMENT REQUESTS ---\n{chat_lines}\n\n"
        if source_urls:
            prompt += "--- SOURCE URLS ---\n" + "\n".join(f"- {url}" for url in source_urls[:20]) + "\n\n"
        prompt += f"--- NEW USER INSTRUCTION ---\n{instruction}\n"

        try:
            refined = await self._ollama_generate(prompt, model=model, timeout=150.0)
        except Exception as exc:
            print(f"Refinement failed: {exc}")
            return None

        with self._session() as db:
            refreshed = db.get(ReviewItemRecord, item_id)
            if not refreshed:
                return None
            refreshed.content = refined
            refreshed.generation_context = refined_context or refreshed.generation_context
            refreshed.source_urls = source_urls
            chat_history.append(
                {
                    "instruction": instruction,
                    "timestamp": datetime.utcnow().isoformat(),
                    "result_preview": refined[:140],
                    "used_research": needs_research,
                }
            )
            refreshed.chat_history = chat_history
            refreshed.updated_at = datetime.utcnow()
            db.add(refreshed)
            db.flush()
            try:
                self._memory.store_preference_memory(channel_id, instruction)
            except Exception as exc:
                print(f"Failed to store preference memory: {exc}")
            return self._serialize_review_item(refreshed)

    # ── Memory ───────────────────────────────────────────────────────

    def list_memories(self, channel_id: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._memory.list_memories(channel_id, memory_type)

    def add_memory(self, channel_id: str, memory_type: str, content: str) -> Dict[str, Any]:
        return self._memory.add_memory(channel_id, memory_type, content)

    def delete_memory(self, memory_id: str) -> bool:
        return self._memory.delete_memory(memory_id)

    def get_review_image(self, item_id: str) -> Optional[Dict[str, Any]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.execute(
                select(ReviewImageRecord).where(ReviewImageRecord.review_item_id == item_id)
            ).scalar_one_or_none()
            if not record:
                return None
            return image_metadata(record, self._data_dir)

    def get_review_image_file(self, item_id: str) -> Optional[tuple[Path, str]]:
        self.initialize_storage()
        with self._session() as db:
            record = db.execute(
                select(ReviewImageRecord).where(ReviewImageRecord.review_item_id == item_id)
            ).scalar_one_or_none()
            if not record or not record.file_path:
                return None
            path = Path(record.file_path)
            if not path.exists():
                return None
            return path, record.mime_type

    def generate_review_image(self, item_id: str) -> Dict[str, Any]:
        api_key = str(self._settings.get("gemini_api_key") or "")
        if not api_key.strip():
            raise ImageGenerationError("Gemini API key is not configured. Save it in Settings first.")

        self.initialize_storage()
        with self._session() as db:
            review_item = db.get(ReviewItemRecord, item_id)
            if not review_item:
                raise ValueError("Review item not found")
            channel = db.get(ChannelRecord, review_item.channel_id)
            if not channel:
                raise ValueError("Channel not found")

            prompt = build_image_prompt(
                topic=review_item.topic or "",
                pillar=review_item.pillar or "",
                content=review_item.content or "",
                channel_name=channel.name,
                platform=review_item.platform or channel.platform or "whatsapp",
            )
            result = generate_image_bytes(api_key, prompt)
            file_path = persist_image_file(self._data_dir, review_item.id, result["mime_type"], result["bytes"])

            existing = db.execute(
                select(ReviewImageRecord).where(ReviewImageRecord.review_item_id == item_id)
            ).scalar_one_or_none()
            now = datetime.utcnow()
            if existing:
                try:
                    Path(existing.file_path).unlink(missing_ok=True)
                except Exception:
                    pass
                existing.prompt = prompt
                existing.mime_type = result["mime_type"]
                existing.file_path = str(file_path)
                existing.updated_at = now
                db.add(existing)
                db.flush()
                return image_metadata(existing, self._data_dir)

            image_record = ReviewImageRecord(
                id=str(uuid4()),
                review_item_id=item_id,
                prompt=prompt,
                mime_type=result["mime_type"],
                file_path=str(file_path),
                created_at=now,
                updated_at=now,
            )
            db.add(image_record)
            db.flush()
            return image_metadata(image_record, self._data_dir)


content_service = ContentService()
