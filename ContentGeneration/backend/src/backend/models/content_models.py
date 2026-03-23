from sqlalchemy import Column, DateTime, Float, JSON, String, Text, UniqueConstraint

from src.backend.db.database import Base


class ChannelRecord(Base):
    __tablename__ = "channels"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    audience = Column(Text, nullable=False, default="")
    tone = Column(String, nullable=False, default="Educational")
    platform = Column(String, nullable=False, default="whatsapp")
    language = Column(String, nullable=False, default="en")
    timezone = Column(String, nullable=False, default="UTC")
    sources = Column(JSON, nullable=False, default=list)
    prompt_template = Column(Text, nullable=False, default="")
    weekly_template = Column(JSON, nullable=False, default=dict)
    overrides = Column(JSON, nullable=False, default=dict)
    context_notes = Column(Text, nullable=False, default="")  # persistent channel memory
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ReviewItemRecord(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        UniqueConstraint("channel_id", "date", name="uq_review_channel_date"),
    )

    id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    date = Column(String, nullable=False, index=True)  # YYYY-MM-DD
    pillar = Column(String, nullable=False, default="")
    topic = Column(Text, nullable=False, default="")
    platform = Column(String, nullable=False, default="whatsapp")
    status = Column(String, nullable=False, default="draft")  # draft, ready
    content = Column(Text, nullable=False, default="")
    chat_history = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class SourceDumpItemRecord(Base):
    __tablename__ = "source_dumps"

    id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    date = Column(String, nullable=False, index=True)  # YYYY-MM-DD
    type = Column(String, nullable=False, default="text")  # url, text, note
    label = Column(String, nullable=False, default="")
    raw_content = Column(Text, nullable=False, default="")
    scraped_content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False)


class GenerationRunRecord(Base):
    __tablename__ = "generation_runs"

    id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="queued")  # queued, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    logs = Column(JSON, nullable=False, default=list)
    dates = Column(JSON, nullable=False, default=list)  # list of date strings being generated
    error = Column(Text, nullable=False, default="")


class MemoryRecord(Base):
    """Stores episodic / preference / contextual memories per channel."""
    __tablename__ = "memories"

    id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, default="contextual")  # episodic, preference, contextual
    content = Column(Text, nullable=False, default="")
    metadata_json = Column(JSON, nullable=False, default=dict)  # extra info (topic, date, score, etc.)
    embedding_text = Column(Text, nullable=False, default="")   # text used for embedding search
    relevance_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, nullable=False)


class EmbeddingRecord(Base):
    """Persistent vector store backed by pgvector for incremental RAG ingestion."""
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_embedding_content_hash"),
    )

    id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)  # MD5 of chunk content
    chunk_text = Column(Text, nullable=False, default="")
    parent_chunk_text = Column(Text, nullable=False, default="")  # the parent chunk for parent-child retrieval
    source_url = Column(String, nullable=False, default="")
    source_title = Column(String, nullable=False, default="")
    kind = Column(String, nullable=False, default="scraped_page")  # scraped_page, search_result, provided_text
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False)

