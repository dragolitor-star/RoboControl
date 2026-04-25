"""Async SQLAlchemy 2.0 engine + session factory + FastAPI dependency."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.MYSQL_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )


engine: AsyncEngine = _build_engine()
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a per-request session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # Commit/rollback semantics live in the service layer; we only ensure
        # the session is closed here.
