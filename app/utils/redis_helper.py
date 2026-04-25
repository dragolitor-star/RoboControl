"""Async Redis helpers (singleton client + key builders + scan iterator)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings
from app.core.constants import (
    REDIS_IDEMPOTENCY_PREFIX,
    REDIS_ROBOT_STATE_PREFIX,
    REDIS_WEBHOOK_DEDUPE_PREFIX,
)

_redis_client: Redis | None = None


async def get_redis() -> Redis:
    """Return a process-wide async Redis client.

    `redis-py>=5` connection pools are async-safe; one pool per process is fine.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# --------------------------------------------------------------------------- #
# Key builders                                                                 #
# --------------------------------------------------------------------------- #


def robot_state_key(amr_code: str) -> str:
    return REDIS_ROBOT_STATE_PREFIX.format(amr_code=amr_code)


def idempotency_key(key: str) -> str:
    return REDIS_IDEMPOTENCY_PREFIX.format(key=key)


def webhook_dedupe_key(robot_task_code: str, method: str) -> str:
    return REDIS_WEBHOOK_DEDUPE_PREFIX.format(
        robot_task_code=robot_task_code, method=method
    )


# --------------------------------------------------------------------------- #
# SCAN helper (NEVER use KEYS in production)                                   #
# --------------------------------------------------------------------------- #


async def scan_iter(client: Redis, match: str, count: int = 200) -> AsyncIterator[str]:
    """Async iterator over keys matching `match`, batched by `count`.

    Wraps `Redis.scan_iter` to keep service code ignorant of redis-py internals.
    """
    async for key in client.scan_iter(match=match, count=count):
        yield key


async def get_json(client: Redis, key: str) -> Any | None:
    raw = await client.get(key)
    if raw is None:
        return None
    import json
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw
