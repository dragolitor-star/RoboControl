"""GET /api/v1/alerts/recent — Recent alerts for the dashboard."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.models.task_history import TaskHistory, TaskStatus
from app.models.webhook_log import WebhookLog
from app.schemas.common import StandardResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get(
    "/recent",
    response_model=StandardResponse[dict],
    summary="Recent alerts — failed tasks, invalid signatures, system events",
    dependencies=[Depends(require_api_key)],
)
async def recent_alerts(
    request: Request,
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[dict]:
    alerts = []

    # 1. Failed / cancelled tasks
    failed_q = (
        select(TaskHistory)
        .where(TaskHistory.status.in_([TaskStatus.failed, TaskStatus.cancelled]))
        .order_by(desc(TaskHistory.updated_at))
        .limit(limit)
    )
    failed_rows = (await session.execute(failed_q)).scalars().all()
    for r in failed_rows:
        alerts.append({
            "type": "task_failed" if r.status == TaskStatus.failed else "task_cancelled",
            "severity": "error" if r.status == TaskStatus.failed else "warning",
            "message": f"Görev {r.robot_task_code} {'başarısız' if r.status == TaskStatus.failed else 'iptal edildi'}",
            "details": r.error_msg or "",
            "robotTaskCode": r.robot_task_code,
            "timestamp": r.updated_at.isoformat() if r.updated_at else None,
        })

    # 2. Invalid webhook signatures
    sig_q = (
        select(WebhookLog)
        .where(WebhookLog.signature_valid == False)  # noqa: E712
        .order_by(desc(WebhookLog.created_at))
        .limit(limit)
    )
    sig_rows = (await session.execute(sig_q)).scalars().all()
    for r in sig_rows:
        alerts.append({
            "type": "webhook_signature_invalid",
            "severity": "error",
            "message": f"Geçersiz webhook imzası: {r.robot_task_code} ({r.method})",
            "details": "",
            "robotTaskCode": r.robot_task_code,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        })

    # Sort all alerts by timestamp descending
    alerts.sort(key=lambda a: a.get("timestamp") or "", reverse=True)

    return StandardResponse[dict](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data={"items": alerts[:limit], "total": len(alerts)},
    )
