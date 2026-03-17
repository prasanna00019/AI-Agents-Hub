"""
Memory service for ContentPilot — episodic, preference, and contextual memory.

Uses Chroma + HuggingFace for episodic similarity search, and SQLAlchemy for
preference / contextual memory storage.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import select

from src.backend.db.database import Base, get_engine, get_session_factory
from src.backend.models.content_models import MemoryRecord


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

    # ── CRUD ──────────────────────────────────────────────────────────

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
            q = select(MemoryRecord).where(MemoryRecord.channel_id == channel_id)
            if memory_type:
                q = q.where(MemoryRecord.type == memory_type)
            q = q.order_by(MemoryRecord.created_at.desc())
            rows = db.execute(q).scalars().all()
            return [self._serialize(r) for r in rows]

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

    # ── Episodic memory ──────────────────────────────────────────────

    def store_episodic_memory(
        self,
        channel_id: str,
        topic: str,
        pillar: str,
        content_summary: str,
        date: str,
    ) -> Dict[str, Any]:
        """Store a summary of an approved post for future topic-avoidance."""
        embedding_text = f"{topic} | {pillar} | {content_summary[:500]}"
        return self.add_memory(
            channel_id=channel_id,
            memory_type="episodic",
            content=f"[{date}] {pillar}: {topic}",
            metadata={"topic": topic, "pillar": pillar, "date": date},
            embedding_text=embedding_text,
        )

    def store_preference_memory(
        self,
        channel_id: str,
        instruction: str,
    ) -> Dict[str, Any]:
        """Log a user refinement instruction as a preference signal."""
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
        """Return recent episodic memory entries as a list of text strings."""
        memories = self.list_memories(channel_id, memory_type="episodic")
        return [m["content"] for m in memories[:limit]]

    def get_preference_patterns(
        self,
        channel_id: str,
        limit: int = 15,
    ) -> List[str]:
        """Return recent preference memories as guidance strings."""
        memories = self.list_memories(channel_id, memory_type="preference")
        return [m["content"] for m in memories[:limit]]

    def build_memory_context(
        self,
        channel_id: str,
        context_notes: str = "",
        topic: str = "",
    ) -> str:
        """
        Build a combined memory context string to inject into the writer prompt.
        Includes: contextual notes + episodic avoidance + preference patterns.
        """
        parts: List[str] = []

        # Contextual notes (user-defined persistent notes)
        if context_notes.strip():
            parts.append(f"Persistent channel notes:\n{context_notes.strip()}")

        # Episodic memory: recent posts to avoid repeating
        recent_topics = self.get_recent_episodic_summaries(channel_id, limit=10)
        if recent_topics:
            topics_str = "\n".join(f"  - {t}" for t in recent_topics)
            parts.append(
                f"Recent posts (AVOID repeating these topics):\n{topics_str}"
            )

        # Preference memory: learned editing patterns
        preferences = self.get_preference_patterns(channel_id, limit=10)
        if preferences:
            pref_str = "\n".join(f"  - {p}" for p in preferences)
            parts.append(
                f"Learned user preferences (apply these writing style adjustments):\n{pref_str}"
            )

        return "\n\n".join(parts)
