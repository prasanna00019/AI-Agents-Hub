from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.backend.core.config import settings

Base = declarative_base()


@lru_cache(maxsize=8)
def get_engine(database_url: str | None = None):
    return create_engine(
        database_url or settings.DATABASE_URL,
        pool_pre_ping=True,
    )


def get_session_factory(database_url: str | None = None):
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine(database_url),
    )


engine = get_engine()
SessionLocal = get_session_factory()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()