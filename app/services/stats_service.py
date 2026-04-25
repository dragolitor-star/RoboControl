"""Dashboard statistics service."""
from __future__ import annotations

from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REDIS_ROBOT_STATE_SCAN_PATTERN
from app.core.logging import get_logger
from app.models.task_history import TaskHistory, TaskStatus
from app.observability.health import check_database, check_redis
from app.schemas.stats import SystemStats
from app.utils.redis_helper import scan_iter

logger = get_logger(__name__)


class StatsService:
    def __init__(self, *, session: AsyncSession, redis_client: Redis) -> None:
        self._session = session
        self._redis = redis_client

    async def get_stats(self) -> SystemStats:
        active_robots = await self._count_active_robots()
        pending = await self._count_by_status(TaskStatus.pending)
        running = await self._count_by_status(TaskStatus.running)
        completed_today = await self._count_today(TaskStatus.completed)
        failed_today = await self._count_today(TaskStatus.failed)
        total = await self._count_total()
        db_ok = await check_database(self._session)
        redis_ok = await check_redis(self._redis)

        return SystemStats(
            active_robots=active_robots,
            pending_tasks=pending,
            running_tasks=running,
            completed_tasks_today=completed_today,
            failed_tasks_today=failed_today,
            total_tasks=total,
            db_status="ok" if db_ok else "error",
            redis_status="ok" if redis_ok else "error",
        )

    async def _count_active_robots(self) -> int:
        count = 0
        async for _ in scan_iter(self._redis, match=REDIS_ROBOT_STATE_SCAN_PATTERN):
            count += 1
        return count

    async def _count_by_status(self, status: TaskStatus) -> int:
        stmt = select(func.count()).select_from(TaskHistory).where(TaskHistory.status == status)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def _count_today(self, status: TaskStatus) -> int:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        stmt = (
            select(func.count())
            .select_from(TaskHistory)
            .where(TaskHistory.status == status, TaskHistory.updated_at >= today_start)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def _count_total(self) -> int:
        stmt = select(func.count()).select_from(TaskHistory)
        result = await self._session.execute(stmt)
        return result.scalar() or 0
