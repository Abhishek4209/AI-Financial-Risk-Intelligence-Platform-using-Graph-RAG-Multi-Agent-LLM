"""PostgreSQL engine and session management; the source of truth for structured data."""
from __future__ import annotations
import os
from collections.abc import Generator
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from src.database.models import Base
def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url
def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL to connect to PostgreSQL")
    return _normalize_url(url)
@lru_cache(maxsize=1)
def get_engine():
    return create_engine(database_url(), pool_pre_ping=True)
@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)
def init_db() -> None:
    """Create all tables if they do not already exist; migrations should replace this in production."""
    Base.metadata.create_all(get_engine())
def get_session() -> Session:
    return _session_factory()()
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
