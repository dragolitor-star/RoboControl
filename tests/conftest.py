"""Shared pytest fixtures.

Strategy:
    * Use SQLite in-memory async engine for fast unit/integration tests.
    * Use `fakeredis.aioredis` for Redis (avoids needing a live broker).
    * Patch the RCS HTTP client to a controllable AsyncMock-style fake.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db import session as db_session_module
from app.db.session import get_db_session
from app.utils import redis_helper


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    db_session_module.AsyncSessionLocal = factory
    db_session_module.engine = db_engine
    return factory


@pytest_asyncio.fixture
async def db_session(db_session_factory) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def redis_mock(monkeypatch) -> AsyncIterator[Any]:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_helper._redis_client = fake

    async def _get_redis() -> Any:
        return fake

    monkeypatch.setattr(redis_helper, "get_redis", _get_redis)
    yield fake
    await fake.aclose()
    redis_helper._redis_client = None


@pytest.fixture
def mock_rcs_client() -> AsyncMock:
    """Drop-in replacement for `RCS2000Client`. Override return values per test."""
    client = AsyncMock()
    client.submit_task = AsyncMock(
        return_value={"code": "Success", "data": {"robotTaskCode": "TASK-TEST-001"}}
    )
    client.get_robot_status = AsyncMock(return_value={"code": "Success", "data": {}})
    client.cancel_task = AsyncMock(return_value={"code": "Success"})
    return client


@pytest_asyncio.fixture
async def async_client(
    db_session_factory, redis_mock, mock_rcs_client, monkeypatch
) -> AsyncIterator[AsyncClient]:
    """ASGI client with all external dependencies stubbed."""
    # Override API key so requests can authenticate using a known value.
    settings.API_KEY = settings.API_KEY.__class__("test-api-key")
    settings.WEBHOOK_SECRET = settings.WEBHOOK_SECRET.__class__("test-webhook-secret")

    from app import main as main_module
    from app.clients import rcs2000_client as client_mod

    monkeypatch.setattr(client_mod, "_singleton", mock_rcs_client)
    monkeypatch.setattr(client_mod, "get_rcs_client", lambda: mock_rcs_client)
    monkeypatch.setattr(main_module, "init_rcs_client", lambda: mock_rcs_client)

    app = main_module.create_app()

    async def _override_session() -> AsyncIterator[AsyncSession]:
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
