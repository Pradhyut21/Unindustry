"""
Database connection and session management.
Uses SQLAlchemy 2.0 async engine with asyncpg driver.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.db import Base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://producttruth:producttruth@localhost:5432/producttruth",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """
    Create all tables on startup.
    In production this would be replaced by Alembic migrations.
    """
    async with engine.begin() as conn:
        # Enable pgvector extension first
        await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
