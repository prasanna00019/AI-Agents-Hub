"""
Memory service for ContentPilot: episodic, preference, and contextual memory.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select

from db.database import Base, get_engine, get_session_factory
from models.content_models import MemoryRecord


class MemoryService:
    """Manages episodic, preference, and contextual memory per channel."""

    def __init__(self, get_db_url_fn):
        self._get_db_url = get_db_url_fn

    def _session(self):
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            factory = get_session_factory(self._get_db_url())
            db = factory()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        return _ctx()

    def _ensure_table(self) -> None:
        try:
            engine = get_engine(self._get_db_url())
            Base.metadata.create_all(bind=engine, tables=[MemoryRecord.__table__])
        except Exception:
            pass

    def add_memory(
        self,
        channel_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_text: str = "",
    ) -> Dict[str, Any]:
        self._ensure_table()
        record = MemoryRecord(
            id=str(uuid4()),
            channel_id=channel_id,
            type=memory_type,
            content=content,
            metadata_json=metadata or {},
            embedding_text=embedding_text or content,
            relevance_score=1.0,
            created_at=datetime.utcnow(),
        )
        with self._session() as db:
            db.add(record)
            db.flush()
            return self._serialize(record)

    def list_memories(
        self,
        channel_id: str,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_table()
        with self._session() as db:
            query = select(MemoryRecord).where(MemoryRecord.channel_id == channel_id)
            if memory_type:
                query = query.where(MemoryRecord.type == memory_type)
            rows = db.execute(query.order_by(MemoryRecord.created_at.desc())).scalars().all()
            return [self._serialize(row) for row in rows]

    def delete_memory(self, memory_id: str) -> bool:
        self._ensure_table()
        with self._session() as db:
            record = db.get(MemoryRecord, memory_id)
            if not record:
                return False
            db.delete(record)
            return True

    @staticmethod
    def _serialize(record: MemoryRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "channel_id": record.channel_id,
            "type": record.type,
            "content": record.content,
            "metadata": record.metadata_json or {},
            "relevance_score": record.relevance_score,
            "created_at": record.created_at.isoformat(),
        }

    def store_episodic_memory(
        self,
        channel_id: str,
        topic: str,
        pillar: str,
        content_summary: str,
        date: str,
    ) -> Dict[str, Any]:
        topic_label = " ".join(topic.split()).strip() or "Untitled topic"
        content_preview = " ".join(content_summary.split())[:280]
        return self.add_memory(
            channel_id=channel_id,
            memory_type="episodic",
            content=f"[{date}] {pillar}: {topic_label}",
            metadata={
                "topic": topic_label,
                "pillar": pillar,
                "date": date,
                "content_preview": content_preview,
            },
            embedding_text=f"{topic_label} | {pillar} | {content_preview}",
        )

    def store_preference_memory(
        self,
        channel_id: str,
        instruction: str,
    ) -> Dict[str, Any]:
        return self.add_memory(
            channel_id=channel_id,
            memory_type="preference",
            content=instruction,
            metadata={"source": "refinement"},
        )

    def get_recent_episodic_summaries(
        self,
        channel_id: str,
        limit: int = 10,
    ) -> List[str]:
        return [memory["content"] for memory in self.list_memories(channel_id, "episodic")[:limit]]

    def get_recent_topic_labels(
        self,
        channel_id: str,
        limit: int = 10,
    ) -> List[str]:
        labels: List[str] = []
        for memory in self.list_memories(channel_id, "episodic")[:limit]:
            metadata = memory.get("metadata") or {}
            label = str(metadata.get("topic") or memory.get("content") or "").strip()
            if label:
                labels.append(label)
        return labels

    def get_preference_patterns(
        self,
        channel_id: str,
        limit: int = 10,
    ) -> List[str]:
        seen: set[str] = set()
        patterns: List[str] = []
        for memory in self.list_memories(channel_id, "preference"):
            content = " ".join(str(memory.get("content") or "").split())
            lowered = content.lower()
            if not lowered or lowered in seen:
                continue
            seen.add(lowered)
            patterns.append(content)
            if len(patterns) >= limit:
                break
        return patterns

    def get_contextual_notes(
        self,
        channel_id: str,
        limit: int = 10,
    ) -> List[str]:
        notes: List[str] = []
        for memory in self.list_memories(channel_id, "contextual")[:limit]:
            content = str(memory.get("content") or "").strip()
            if content:
                notes.append(content)
        return notes

    def build_memory_context(
        self,
        channel_id: str,
        context_notes: str = "",
        topic: str = "",
    ) -> str:
        parts: List[str] = []

        if context_notes.strip():
            parts.append(f"Persistent channel notes:\n{context_notes.strip()}")

        contextual_entries = self.get_contextual_notes(channel_id, limit=10)
        if contextual_entries:
            notes = "\n".join(f"  - {note}" for note in contextual_entries)
            parts.append(f"Saved channel memories:\n{notes}")

        recent_topics = self.get_recent_episodic_summaries(channel_id, limit=10)
        if recent_topics:
            topics = "\n".join(f"  - {entry}" for entry in recent_topics)
            parts.append(f"Recent approved posts to avoid repeating:\n{topics}")

        preferences = self.get_preference_patterns(channel_id, limit=10)
        if preferences:
            pref_str = "\n".join(f"  - {pref}" for pref in preferences)
            parts.append(f"Learned refinement preferences:\n{pref_str}")

        if topic.strip():
            parts.append(f"Current requested topic or pillar:\n  - {topic.strip()}")

        return "\n\n".join(parts)
