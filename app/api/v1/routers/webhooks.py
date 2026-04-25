"""POST /api/v1/webhook/rcs2000/task-feedback."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import WEBHOOK_SIGNATURE_HEADER
from app.core.exceptions import WebhookSignatureError
from app.db.session import get_db_session
from app.schemas.common import StandardResponse
from app.schemas.webhook import TaskFeedbackPayload, WebhookAck
from app.services.webhook_service import WebhookService
from app.utils.redis_helper import get_redis

router = APIRouter(prefix="/webhook/rcs2000", tags=["webhooks"])


@router.post(
    "/task-feedback",
    response_model=StandardResponse[WebhookAck],
    summary="Receive task progress callbacks from RCS-2000",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "requestId": "8e7f0a86-7d1d-4c47-8c9e-7c5db8ea2bf3",
                        "data": {"acknowledged": True, "duplicate": False},
                    }
                }
            }
        },
        401: {
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "requestId": "8e7f0a86-7d1d-4c47-8c9e-7c5db8ea2bf3",
                        "error": {
                            "code": "WEBHOOK_SIGNATURE_INVALID",
                            "message": "Webhook signature mismatch",
                        },
                    }
                }
            }
        },
    },
)
async def task_feedback(
    request: Request,
    x_webhook_signature: str | None = Header(default=None, alias=WEBHOOK_SIGNATURE_HEADER),
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[WebhookAck]:
    raw = await request.body()

    try:
        payload_dict = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise WebhookSignatureError("Webhook body is not valid JSON")

    payload = TaskFeedbackPayload.model_validate(payload_dict)

    redis_client = await get_redis()
    service = WebhookService(redis_client=redis_client, session=session)
    ack = await service.handle_task_feedback(
        raw_body=raw, signature=x_webhook_signature, payload=payload
    )
    return StandardResponse[WebhookAck](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=ack,
    )
