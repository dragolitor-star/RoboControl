"""Celery tasks executed off the request path.

`process_task_feedback` updates the DB and the Redis robot-state cache
in response to a feedback webhook. It is at-least-once delivered, so it
MUST remain idempotent.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis_async

from app.core.config import settings
from app.core.constants import (
    ROBOT_STATE_TTL_SECONDS,
    TASK_METHOD_TO_STATUS,
)
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.task_history import TaskStatus
from app.repositories.task_history_repository import TaskHistoryRepository
from app.utils.redis_helper import robot_state_key
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.process_task_feedback",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
def process_task_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    """Sync entry-point used by Celery; delegates to async impl."""
    return asyncio.run(_process_task_feedback_async(payload))


async def _process_task_feedback_async(payload: dict[str, Any]) -> dict[str, Any]:
    robot_task_code: str = str(payload.get("robotTaskCode", "")).strip()
    method: str = str(payload.get("method", "")).strip()

    if not robot_task_code or not method:
        logger.warning("feedback_missing_fields", payload=payload)
        return {"updated": False, "reason": "missing_fields"}

    target_status_str = TASK_METHOD_TO_STATUS.get(method)
    if target_status_str is None:
        target_status = TaskStatus.failed
        logger.warning(
            "feedback_unknown_method",
            method=method,
            robot_task_code=robot_task_code,
        )
    else:
        target_status = TaskStatus(target_status_str)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    db_updated = await _update_task_history(
        robot_task_code=robot_task_code,
        method=method,
        target_status=target_status,
        amr_code=payload.get("amrCode"),
        error_msg=payload.get("errorMsg"),
        now=now,
    )
    cache_updated = await _update_robot_state(payload, target_status, now)

    logger.info(
        "feedback_processed",
        robot_task_code=robot_task_code,
        method=method,
        status=target_status.value,
        db_updated=db_updated,
        cache_updated=cache_updated,
    )
    return {"updated": db_updated, "cache_updated": cache_updated}


async def _update_task_history(
    *,
    robot_task_code: str,
    method: str,
    target_status: TaskStatus,
    amr_code: str | None,
    error_msg: str | None,
    now: datetime,
) -> bool:
    async with AsyncSessionLocal() as session:
        repo = TaskHistoryRepository(session)
        existing = await repo.get_by_robot_task_code(robot_task_code)
        if existing is None:
            logger.warning("feedback_unknown_task", robot_task_code=robot_task_code)
            return False

        # Idempotency: don't downgrade a terminal status.
        if existing.status in (TaskStatus.completed, TaskStatus.cancelled, TaskStatus.failed):
            if existing.status == target_status:
                return False
            # Allow upgrades only from running/pending; ignore otherwise.
            return False

        kwargs: dict[str, Any] = {
            "robot_task_code": robot_task_code,
            "status": target_status,
            "robot_code": amr_code,
            "error_msg": error_msg,
        }
        if method == "start" and existing.start_time is None:
            kwargs["start_time"] = now
        if target_status in (TaskStatus.completed, TaskStatus.failed, TaskStatus.cancelled):
            kwargs["end_time"] = now

        rowcount = await repo.update_status(**kwargs)
        await session.commit()
        return rowcount > 0


async def _update_robot_state(
    payload: dict[str, Any],
    target_status: TaskStatus,
    now: datetime,
) -> bool:
    amr_code = payload.get("amrCode")
    if not amr_code:
        return False

    state_payload = {
        "amrCode": amr_code,
        "x": payload.get("x"),
        "y": payload.get("y"),
        "state": target_status.value,
        "lastTaskCode": payload.get("robotTaskCode"),
        "updatedAt": now.isoformat(),
    }
    client = redis_async.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    try:
        await client.setex(
            robot_state_key(amr_code),
            ROBOT_STATE_TTL_SECONDS,
            json.dumps(state_payload),
        )
        return True
    finally:
        await client.aclose()
