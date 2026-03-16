from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db.database import get_db

router = APIRouter(prefix="/channels", tags=["channels"])

@router.get("/")
async def list_channels(db: Session = Depends(get_db)):
    return {"message": "List of channels"}

@router.post("/")
async def create_channel(channel_data: dict, db: Session = Depends(get_db)):
    return {"message": "Channel created", "data": channel_data}