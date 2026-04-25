"""Webhook ingestion service (signature verification + dedupe + dispatch + logging).

The HTTP handler must return within ~100ms; therefore this service does the
minimum required work synchronously (verify, dedupe, log, enqueue) and offloads
the actual DB/Redis updates to a Celery task.
"""
from __future__ import annotations

import json

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import WEBHOOK_DEDUPE_TTL_SECONDS
from app.core.exceptions import WebhookSignatureError
from app.core.logging import get_logger
from app.core.security import verify_webhook_signature
from app.models.webhook_log import WebhookLog
from app.schemas.webhook import TaskFeedbackPayload, WebhookAck
from app.utils.redis_helper import webhook_dedupe_key

logger = get_logger(__name__)


class WebhookService:
    def __init__(self, *, redis_client: Redis, session: AsyncSession | None = None) -> None:
        self._redis = redis_client
        self._session = session

    async def handle_task_feedback(
        self,
        *,
        raw_body: bytes,
        signature: str | None,
        payload: TaskFeedbackPayload,
    ) -> WebhookAck:
        sig_valid = True
        is_duplicate = False

        # 1. Verify signature (raises WebhookSignatureError on mismatch)
        try:
            verify_webhook_signature(raw_body, signature)
        except WebhookSignatureError:
            sig_valid = False
            await self._log_event(payload, raw_body, sig_valid, False)
            raise

        # 2. Dedupe (atomic SET NX)
        dedupe_k = webhook_dedupe_key(payload.robot_task_code, payload.method)
        first = await self._redis.set(
            dedupe_k, "1", nx=True, ex=WEBHOOK_DEDUPE_TTL_SECONDS
        )
        if not first:
            is_duplicate = True
            logger.info(
                "webhook_duplicate",
                robot_task_code=payload.robot_task_code,
                method=payload.method,
            )
            await self._log_event(payload, raw_body, sig_valid, is_duplicate)
            return WebhookAck(acknowledged=True, duplicate=True)

        # 3. Log event to DB
        await self._log_event(payload, raw_body, sig_valid, is_duplicate)

        # 4. Enqueue async processing
        from app.workers.tasks import process_task_feedback  # noqa: WPS433
        process_task_feedback.delay(payload.model_dump(by_alias=True))

        logger.info(
            "webhook_enqueued",
            robot_task_code=payload.robot_task_code,
            method=payload.method,
        )
        return WebhookAck(acknowledged=True, duplicate=False)

    async def _log_event(
        self, payload: TaskFeedbackPayload, raw_body: bytes, sig_valid: bool, duplicate: bool
    ) -> None:
        if not self._session:
            return
        try:
            self._session.add(WebhookLog(
                robot_task_code=payload.robot_task_code,
                method=payload.method,
                amr_code=payload.amr_code,
                x=payload.x,
                y=payload.y,
                raw_payload=raw_body.decode("utf-8", errors="replace")[:4096],
                signature_valid=sig_valid,
                duplicate=duplicate,
            ))
            await self._session.commit()
        except Exception as exc:
            logger.warning("webhook_log_failed", error=str(exc))
            await self._session.rollback()

