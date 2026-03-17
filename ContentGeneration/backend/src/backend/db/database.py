from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.backend.core.config import settings

Base = declarative_base()


@lru_cache(maxsize=8)
def get_engine(database_url: str | None = None):
    url = (database_url or settings.DATABASE_URL or "").strip()
    if not url:
        raise ValueError("Database URL is not configured.")
    # Use 5 second timeout for engine connections
    connect_args = {}
    if "postgresql" in url.lower():
        connect_args["connect_timeout"] = 5
        
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args
    )


def get_session_factory(database_url: str | None = None):
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine(database_url),
    )

def get_db(database_url: str | None = None):
    db = get_session_factory(database_url)()
    try:
        yield db
    finally:
        db.close()
