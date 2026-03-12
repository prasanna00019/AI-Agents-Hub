import os
import dotenv
from sqlalchemy import create_engine, Column, DateTime, Integer, String, Text, func, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

dotenv.load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

Base = declarative_base()
_engines = {}
_session_factories = {}


def get_database_url(database_url: str | None = None) -> str | None:
    candidate = (database_url or DATABASE_URL or "").strip()
    return candidate or None


def get_engine(database_url: str | None = None):
    resolved_url = get_database_url(database_url)
    if not resolved_url:
        return None
    if resolved_url in _engines:
        return _engines[resolved_url]

    try:
        engine = create_engine(resolved_url, pool_pre_ping=True)
        _engines[resolved_url] = engine
        return engine
    except Exception as e:
        print(f"Failed to initialize database connection: {e}")
        return None


def get_session_factory(database_url: str | None = None):
    resolved_url = get_database_url(database_url)
    if not resolved_url:
        return None
    if resolved_url in _session_factories:
        return _session_factories[resolved_url]

    engine = get_engine(resolved_url)
    if not engine:
        return None

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _session_factories[resolved_url] = session_factory
    return session_factory


SessionLocal = get_session_factory()

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
    settings_signature = Column(Text, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def _ensure_schema(engine):
    inspector = inspect(engine)
    if "video_notes_cache" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("video_notes_cache")}
    statements = []

    if "settings_signature" not in columns:
        statements.append("ALTER TABLE video_notes_cache ADD COLUMN settings_signature TEXT")
    if "created_at" not in columns:
        statements.append(
            "ALTER TABLE video_notes_cache ADD COLUMN created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

def init_db(database_url: str | None = None):
    engine = get_engine(database_url)
    if engine:
        Base.metadata.create_all(bind=engine)
        _ensure_schema(engine)
