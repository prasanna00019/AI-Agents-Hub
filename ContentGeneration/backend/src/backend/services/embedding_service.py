"""
Persistent embedding storage backed by PostgreSQL + pgvector.

Provides incremental ingestion: documents are chunked, hashed, and stored
so that only new/changed content is re-embedded on subsequent generations.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import select, text

from src.backend.db.database import get_engine, get_session_factory
from src.backend.models.content_models import EmbeddingRecord


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


class EmbeddingService:
    """Manages persistent embeddings in PostgreSQL for incremental RAG."""

    def __init__(self, get_db_url_fn) -> None:
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

    def _ensure_pgvector(self) -> bool:
        """Check if pgvector extension is available."""
        try:
            engine = get_engine(self._get_db_url())
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            return True
        except Exception:
            return False

    def store_chunks(
        self,
        channel_id: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Store document chunks, skipping those that already exist (by content hash).

        Each chunk dict should have:
            - chunk_text: str
            - parent_chunk_text: str
            - source_url: str (optional)
            - source_title: str (optional)
            - kind: str (optional)
            - metadata: dict (optional)
        """
        stored = 0
        skipped = 0
        seen_hashes = set()

        with self._session() as db:
            for chunk in chunks:
                chunk_text = chunk.get("chunk_text", "")
                if not chunk_text.strip():
                    continue

                content_hash = _content_hash(chunk_text)
                if content_hash in seen_hashes:
                    skipped += 1
                    continue
                    
                seen_hashes.add(content_hash)

                # Check if already exists in DB
                existing = db.execute(
                    select(EmbeddingRecord).where(
                        EmbeddingRecord.content_hash == content_hash,
                    )
                ).scalar_one_or_none()

                if existing:
                    skipped += 1
                    continue

                record = EmbeddingRecord(
                    id=str(uuid4()),
                    channel_id=channel_id,
                    content_hash=content_hash,
                    chunk_text=chunk_text,
                    parent_chunk_text=chunk.get("parent_chunk_text", chunk_text),
                    source_url=chunk.get("source_url", ""),
                    source_title=chunk.get("source_title", ""),
                    kind=chunk.get("kind", "scraped_page"),
                    metadata_json=chunk.get("metadata", {}),
                    embedding=chunk.get("embedding"),
                    created_at=datetime.utcnow(),
                )
                db.add(record)
                stored += 1

        return {"stored": stored, "skipped": skipped, "total": stored + skipped}

    def get_stored_chunks(
        self,
        channel_id: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Retrieve all stored chunks for a channel."""
        with self._session() as db:
            rows = db.execute(
                select(EmbeddingRecord)
                .where(EmbeddingRecord.channel_id == channel_id)
                .order_by(EmbeddingRecord.created_at.desc())
                .limit(limit)
            ).scalars().all()

            return [
                {
                    "id": r.id,
                    "content_hash": r.content_hash,
                    "chunk_text": r.chunk_text,
                    "parent_chunk_text": r.parent_chunk_text,
                    "source_url": r.source_url,
                    "source_title": r.source_title,
                    "kind": r.kind,
                    "metadata": r.metadata_json,
                    "embedding": r.embedding,
                }
                for r in rows
            ]

    def get_chunk_hashes(self, channel_id: str) -> set[str]:
        """Get all content hashes for a channel to check freshness."""
        with self._session() as db:
            rows = db.execute(
                select(EmbeddingRecord.content_hash)
                .where(EmbeddingRecord.channel_id == channel_id)
            ).scalars().all()
            return set(rows)

    def delete_channel_embeddings(self, channel_id: str) -> int:
        """Delete all stored embeddings for a channel."""
        with self._session() as db:
            rows = db.execute(
                select(EmbeddingRecord)
                .where(EmbeddingRecord.channel_id == channel_id)
            ).scalars().all()
            count = len(rows)
            for r in rows:
                db.delete(r)
            return count
