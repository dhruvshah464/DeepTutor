"""
Database Layer
==============

SQLAlchemy async engine, session factory, and ORM models for the
DeepTutor SaaS platform.  Supports both PostgreSQL (production) and
SQLite (single-user / CLI mode) via a single ``DATABASE_URL`` env var.
"""

from .engine import get_async_engine, get_async_session, init_db

__all__ = ["get_async_engine", "get_async_session", "init_db"]
