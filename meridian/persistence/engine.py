"""
Database Engine Factory
=======================

Creates an async SQLAlchemy engine from ``DATABASE_URL``.
Supports PostgreSQL (asyncpg) and SQLite (aiosqlite).

Usage::

    from meridian.persistence import get_async_session

    async with get_async_session() as session:
        result = await session.execute(select(User))
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/deeptutor.db"


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    # Handle Heroku-style postgres:// → postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _build_engine_kwargs(url: str) -> dict:
    kwargs: dict = {
        "echo": os.getenv("DB_ECHO", "false").lower() == "true",
        "future": True,
    }
    if "sqlite" in url:
        # SQLite-specific: allow multithreaded access
        from sqlalchemy.pool import StaticPool

        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    else:
        # PostgreSQL connection pool tuning
        kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
        kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 3600
    return kwargs


def get_async_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it on first call."""
    global _engine
    if _engine is None:
        url = _get_database_url()
        _engine = create_async_engine(url, **_build_engine_kwargs(url))
        logger.info("Database engine created: %s", url.split("@")[-1] if "@" in url else url)
    return _engine


def _get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional async session scope."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields an async session per request."""
    async with get_async_session() as session:
        yield session


async def init_db() -> None:
    """Create all tables. Use only for dev/testing — prefer Alembic in production."""
    from .models.base import Base

    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def dispose_engine() -> None:
    """Dispose the engine connection pool (for graceful shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")
