from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChannelBase(BaseModel):
    name: str
    description: str
    audience: str
    tone: str
    platform: str
    language: str = "en"
    timezone: str = "UTC"

class ChannelCreate(ChannelBase):
    pass

class ChannelUpdate(ChannelBase):
    pass

class Channel(ChannelBase):
    id: int
    user_id: int
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True