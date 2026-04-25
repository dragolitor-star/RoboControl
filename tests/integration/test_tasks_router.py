"""Integration tests for /api/v1/tasks/create."""
from __future__ import annotations

import pytest

from app.models.robot_type import RobotType


@pytest.fixture
async def seed_lmr(db_session_factory):
    async with db_session_factory() as session:
        session.add(RobotType(name="LMR", rcs_task_type="PF-LMR-COMMON"))
        await session.commit()


@pytest.mark.asyncio
async def test_post_create_task_returns_201(async_client, seed_lmr):
    resp = await async_client.post(
        "/api/v1/tasks/create",
        headers={"X-API-Key": "test-api-key"},
        json={"robotType": "LMR", "sourceCode": "A", "targetCode": "B", "priority": 5},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["robotTaskCode"] == "TASK-TEST-001"
    assert body["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_post_create_task_invalid_robot_type_returns_404(async_client):
    resp = await async_client.post(
        "/api/v1/tasks/create",
        headers={"X-API-Key": "test-api-key"},
        json={"robotType": "XYZ", "sourceCode": "A", "targetCode": "B"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ROBOT_TYPE_NOT_FOUND"


@pytest.mark.asyncio
async def test_post_create_task_idempotency_header(async_client, seed_lmr, mock_rcs_client):
    headers = {"X-API-Key": "test-api-key", "Idempotency-Key": "client-uuid-1"}
    payload = {"robotType": "LMR", "sourceCode": "A", "targetCode": "B"}

    r1 = await async_client.post("/api/v1/tasks/create", headers=headers, json=payload)
    r2 = await async_client.post("/api/v1/tasks/create", headers=headers, json=payload)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["data"]["robotTaskCode"] == r2.json()["data"]["robotTaskCode"]
    assert r2.json()["data"]["cached"] is True
    # Second call must NOT re-hit RCS.
    assert mock_rcs_client.submit_task.await_count == 1


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(async_client):
    resp = await async_client.post(
        "/api/v1/tasks/create",
        json={"robotType": "LMR", "sourceCode": "A", "targetCode": "B"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"
