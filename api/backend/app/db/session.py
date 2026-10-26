"""Database engine and session management using SQLAlchemy 2.0 and psycopg 3."""

from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import get_settings
from backend.app.db.base import Base

_engine = None
_SessionFactory = None


def get_engine():
    """Lazily initialize and return the SQLAlchemy engine."""
    global _engine, _SessionFactory
    if _engine is None:
        settings = get_settings()
        db_url = (
            settings.TEST_DATABASE_URL
            if (settings.APP_ENV == "testing" and settings.TEST_DATABASE_URL)
            else settings.DATABASE_URL
        )
        if not db_url:
            return None
        # Ensure psycopg 3 driver is specified if raw postgresql is provided
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
            connect_args={"connect_timeout": 5},
        )
        _SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
    return _engine


def get_db_session() -> Optional[Session]:
    """Get an isolated session instance if engine is configured."""
    engine = get_engine()
    if engine is None or _SessionFactory is None:
        return None
    return _SessionFactory()


def get_db() -> Generator[Optional[Session], None, None]:
    """FastAPI dependency for obtaining a database session."""
    session = get_db_session()
    if session is None:
        yield None
        return
    try:
        yield session
    finally:
        session.close()
