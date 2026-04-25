"""Integration tests for /health/* endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_live_always_200(async_client):
    resp = await async_client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_ok(async_client):
    resp = await async_client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["db"] == "ok"
    assert body["redis"] == "ok"


@pytest.mark.asyncio
async def test_ready_redis_down_returns_503(async_client, redis_mock, monkeypatch):
    async def _broken_ping():
        raise RuntimeError("redis down")

    monkeypatch.setattr(redis_mock, "ping", AsyncMock(side_effect=_broken_ping))

    resp = await async_client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["redis"] == "error"
