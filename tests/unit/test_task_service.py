"""Unit tests for `TaskService`."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import RCSClientError, RobotTypeNotFoundError
from app.models.robot_type import RobotType
from app.schemas.task import TaskCreateRequest
from app.services.task_service import TaskService


@pytest.fixture
async def seeded_robot_type(db_session) -> RobotType:
    rt = RobotType(name="LMR", rcs_task_type="PF-LMR-COMMON", description="test")
    db_session.add(rt)
    await db_session.commit()
    await db_session.refresh(rt)
    return rt


def _request() -> TaskCreateRequest:
    return TaskCreateRequest(
        robotType="LMR", sourceCode="A1", targetCode="B1", priority=10
    )


@pytest.mark.asyncio
async def test_create_task_success(db_session, redis_mock, mock_rcs_client, seeded_robot_type):
    service = TaskService(session=db_session, redis_client=redis_mock, rcs_client=mock_rcs_client)
    result = await service.create_task(request=_request())
    assert result.robot_task_code == "TASK-TEST-001"
    assert result.status == "pending"
    assert result.cached is False
    mock_rcs_client.submit_task.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_robot_type_not_found(db_session, redis_mock, mock_rcs_client):
    service = TaskService(session=db_session, redis_client=redis_mock, rcs_client=mock_rcs_client)
    with pytest.raises(RobotTypeNotFoundError):
        await service.create_task(
            request=TaskCreateRequest(
                robotType="DOES_NOT_EXIST", sourceCode="A", targetCode="B", priority=5
            )
        )
    mock_rcs_client.submit_task.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_task_rcs_error(db_session, redis_mock, mock_rcs_client, seeded_robot_type):
    mock_rcs_client.submit_task = AsyncMock(side_effect=RCSClientError("boom"))
    service = TaskService(session=db_session, redis_client=redis_mock, rcs_client=mock_rcs_client)
    with pytest.raises(RCSClientError):
        await service.create_task(request=_request())


@pytest.mark.asyncio
async def test_create_task_idempotency_returns_cached_response(
    db_session, redis_mock, mock_rcs_client, seeded_robot_type
):
    service = TaskService(session=db_session, redis_client=redis_mock, rcs_client=mock_rcs_client)
    first = await service.create_task(request=_request(), idempotency_key="abc")
    second = await service.create_task(request=_request(), idempotency_key="abc")

    assert first.robot_task_code == second.robot_task_code
    assert second.cached is True
    # RCS only called once even though we created twice with same key.
    assert mock_rcs_client.submit_task.await_count == 1
