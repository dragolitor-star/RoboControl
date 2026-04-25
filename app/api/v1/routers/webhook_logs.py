"""GET /api/v1/webhook/logs — Webhook event log viewer."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.repositories.webhook_log_repository import WebhookLogRepository
from app.schemas.common import StandardResponse
from app.schemas.webhook_log import WebhookLogItem

router = APIRouter(prefix="/webhook", tags=["webhook-logs"])


@router.get(
    "/logs",
    response_model=StandardResponse[dict],
    summary="List webhook event logs with pagination",
    dependencies=[Depends(require_api_key)],
)
async def list_webhook_logs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100, alias="pageSize"),
    task_code: str | None = Query(default=None, alias="taskCode"),
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[dict]:
    repo = WebhookLogRepository(session)
    offset = (page - 1) * page_size
    rows, total = await repo.list_recent(limit=page_size, offset=offset, task_code=task_code)

    items = [
        WebhookLogItem(
            id=r.id,
            robot_task_code=r.robot_task_code,
            method=r.method,
            amr_code=r.amr_code,
            x=r.x,
            y=r.y,
            signature_valid=r.signature_valid,
            duplicate=r.duplicate,
            created_at=r.created_at,
        ).model_dump(by_alias=True)
        for r in rows
    ]

    return StandardResponse[dict](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data={
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    )
