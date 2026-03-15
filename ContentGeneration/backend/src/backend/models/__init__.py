from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.backend.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    preferences = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    channels = relationship("Channel", back_populates="user")

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    audience = Column(String)
    tone = Column(String)
    platform = Column(String, nullable=False)
    content_pillars = Column(JSON)
    posting_frequency = Column(String)
    language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    ollama_model = Column(String)
    context_notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="channels")
    sources = relationship("ChannelSource", back_populates="channel")
    prompt_templates = relationship("PromptTemplate", back_populates="channel")
    weekly_template = relationship("WeeklyTemplate", back_populates="channel", uselist=False)
    post_slots = relationship("PostSlot", back_populates="channel")
    generation_runs = relationship("GenerationRun", back_populates="channel")
    posts = relationship("Post", back_populates="channel")
    memories = relationship("Memory", back_populates="channel")

class ChannelSource(Base):
    __tablename__ = "channel_sources"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    type = Column(String, nullable=False)  # url/rss/search_query/document/manual_note
    value = Column(Text, nullable=False)
    label = Column(String)
    is_active = Column(Boolean, default=True)
    trust_score = Column(Integer, default=100)
    last_fetched_at = Column(DateTime)

    # Relationships
    channel = relationship("Channel", back_populates="sources")

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    system_prompt = Column(Text)
    content_prompt = Column(Text)
    version = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    parent_version_id = Column(Integer, ForeignKey("prompt_templates.id"))

    # Relationships
    channel = relationship("Channel", back_populates="prompt_templates")

class WeeklyTemplate(Base):
    __tablename__ = "weekly_templates"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)

    # Day of week templates
    monday_pillar = Column(String)
    monday_mode = Column(String)  # pre_generated or source_dump

    tuesday_pillar = Column(String)
    tuesday_mode = Column(String)

    wednesday_pillar = Column(String)
    wednesday_mode = Column(String)

    thursday_pillar = Column(String)
    thursday_mode = Column(String)

    friday_pillar = Column(String)
    friday_mode = Column(String)

    saturday_pillar = Column(String)
    saturday_mode = Column(String)

    sunday_pillar = Column(String)
    sunday_mode = Column(String)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    channel = relationship("Channel", back_populates="weekly_template")

class PostSlot(Base):
    __tablename__ = "post_slots"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    scheduled_date = Column(DateTime, nullable=False)

    # Override settings
    is_override = Column(Boolean, default=False)
    content_pillar = Column(String)
    topic = Column(String)
    generation_mode = Column(String)  # pre_generated or source_dump
    special_instructions = Column(Text)
    sources_override = Column(JSON)
    status = Column(String, default="empty")  # empty, collecting, ready_to_generate, draft, ready

    # Relationships
    channel = relationship("Channel", back_populates="post_slots")
    source_dump_items = relationship("SourceDumpItem", back_populates="post_slot")
    posts = relationship("Post", back_populates="post_slot")

class SourceDumpItem(Base):
    __tablename__ = "source_dump_items"

    id = Column(Integer, primary_key=True, index=True)
    post_slot_id = Column(Integer, ForeignKey("post_slots.id"), nullable=False)
    type = Column(String, nullable=False)  # url/text/file/note
    raw_content = Column(Text)
    scraped_content = Column(Text)
    label = Column(String)
    added_at = Column(DateTime, server_default=func.now())

    # Relationships
    post_slot = relationship("PostSlot", back_populates="source_dump_items")

class GenerationRun(Base):
    __tablename__ = "generation_runs"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    post_slot_ids = Column(JSON)
    triggered_by = Column(String)  # user or system
    status = Column(String)  # queued, running, completed, failed
    ollama_model = Column(String)
    duration_seconds = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    logs = Column(JSON)  # per-step: input, output, duration, tokens_estimated

    # Relationships
    channel = relationship("Channel", back_populates="generation_runs")
    posts = relationship("Post", back_populates="generation_run")

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    post_slot_id = Column(Integer, ForeignKey("post_slots.id"))
    run_id = Column(Integer, ForeignKey("generation_runs.id"))
    content_pillar = Column(String)
    raw_draft = Column(Text)
    formatted_content = Column(Text)
    platform_format = Column(String)
    status = Column(String, default="draft")  # draft, ready, archived
    sources_used = Column(JSON)
    edit_history = Column(JSON)
    refinement_chat_history = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    last_edited_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    channel = relationship("Channel", back_populates="posts")
    post_slot = relationship("PostSlot", back_populates="posts")
    generation_run = relationship("GenerationRun", back_populates="posts")

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    type = Column(String)  # preference, source, episodic, contextual
    content = Column(Text)
    embedding = Column(String)  # We'll store the vector as a string representation
    relevance_score = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    last_accessed_at = Column(DateTime, server_default=func.now())

    # Relationships
    channel = relationship("Channel", back_populates="memories")