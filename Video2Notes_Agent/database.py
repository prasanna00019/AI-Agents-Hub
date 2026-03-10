import os
import dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

dotenv.load_dotenv()
DATABASE_URL = "postgresql://postgres:radha@localhost:6739/videonotes"

engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        print(f"Failed to initialize database connection: {e}")
        engine = None
        SessionLocal = None

class VideoNoteCache(Base):
    __tablename__ = "video_notes_cache"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    provider = Column(String, index=True)
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    title = Column(String)
    description = Column(Text)
    notes = Column(Text)

def init_db():
    if engine:
        Base.metadata.create_all(bind=engine)
