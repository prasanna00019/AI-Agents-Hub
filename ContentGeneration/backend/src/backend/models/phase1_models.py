from sqlalchemy import Column, DateTime, JSON, String, Text, UniqueConstraint

from src.backend.db.database import Base


class ChannelRecord(Base):
    __tablename__ = "phase1_channels"

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
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ReviewItemRecord(Base):
    __tablename__ = "phase1_review_items"
    __table_args__ = (
        UniqueConstraint("channel_id", "date", name="uq_phase1_review_channel_date"),
    )

    id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    date = Column(String, nullable=False, index=True)
    pillar = Column(String, nullable=False, default="")
    topic = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="draft")
    content = Column(Text, nullable=False, default="")
    chat_history = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
