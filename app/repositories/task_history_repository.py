"""Repository for `TaskHistory` queries.

Service layer should call only repository methods; raw SQLAlchemy must
not leak into services.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_history import TaskHistory, TaskStatus


class TaskHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_robot_task_code(self, robot_task_code: str) -> TaskHistory | None:
        stmt = select(TaskHistory).where(TaskHistory.robot_task_code == robot_task_code)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> TaskHistory | None:
        stmt = select(TaskHistory).where(TaskHistory.idempotency_key == key)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        robot_task_code: str,
        status: TaskStatus,
        source_code: str | None = None,
        target_code: str | None = None,
        robot_code: str | None = None,
        idempotency_key: str | None = None,
    ) -> TaskHistory:
        item = TaskHistory(
            robot_task_code=robot_task_code,
            status=status,
            source_code=source_code,
            target_code=target_code,
            robot_code=robot_code,
            idempotency_key=idempotency_key,
        )
        self._session.add(item)
        await self._session.flush()  # populate id without committing
        return item

    async def update_status(
        self,
        *,
        robot_task_code: str,
        status: TaskStatus,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        error_msg: str | None = None,
        robot_code: str | None = None,
    ) -> int:
        values: dict[str, Any] = {"status": status}
        if start_time is not None:
            values["start_time"] = start_time
        if end_time is not None:
            values["end_time"] = end_time
        if error_msg is not None:
            values["error_msg"] = error_msg
        if robot_code is not None:
            values["robot_code"] = robot_code

        stmt = (
            update(TaskHistory)
            .where(TaskHistory.robot_task_code == robot_task_code)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        return result.rowcount or 0
