"""Liveness + readiness probe logic."""
from __future__ import annotations

from typing import Any

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_database(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover - exercised in integration test
        logger.warning("readiness_db_failed", error=str(exc))
        return False


async def check_redis(client: Redis) -> bool:
    try:
        return bool(await client.ping())
    except Exception as exc:  # pragma: no cover
        logger.warning("readiness_redis_failed", error=str(exc))
        return False


async def readiness_report(
    *, session: AsyncSession, redis_client: Redis
) -> tuple[bool, dict[str, Any]]:
    db_ok = await check_database(session)
    redis_ok = await check_redis(redis_client)
    report = {
        "db": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    return db_ok and redis_ok, report
