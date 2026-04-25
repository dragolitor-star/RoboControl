"""Repository for WebhookLog queries."""
from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_log import WebhookLog


class WebhookLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> WebhookLog:
        item = WebhookLog(**kwargs)
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_recent(
        self, *, limit: int = 50, offset: int = 0, task_code: str | None = None
    ) -> tuple[list[WebhookLog], int]:
        query = select(WebhookLog).order_by(desc(WebhookLog.created_at))
        count_q = select(func.count()).select_from(WebhookLog)

        if task_code:
            query = query.where(WebhookLog.robot_task_code.contains(task_code))
            count_q = count_q.where(WebhookLog.robot_task_code.contains(task_code))

        total = (await self._session.execute(count_q)).scalar() or 0
        rows = (await self._session.execute(query.offset(offset).limit(limit))).scalars().all()
        return list(rows), total
