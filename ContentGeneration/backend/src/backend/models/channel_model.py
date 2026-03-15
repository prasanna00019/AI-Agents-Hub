from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.backend.models.base import Base

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    audience = Column(String)
    tone = Column(String)
    platform = Column(String, nullable=False)
    content_pillars = Column(Text)  # JSON string
    posting_frequency = Column(String)
    language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    ollama_model = Column(String)
    context_notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships would be defined here when we have the User model