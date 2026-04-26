"""Task endpoints: create + history list."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.rcs2000_client import RCS2000Client, get_rcs_client
from app.core.constants import IDEMPOTENCY_HEADER
from app.core.security import require_api_key
from app.db.session import get_db_session
from app.models.task_history import TaskHistory, TaskStatus
from app.schemas.common import StandardResponse
from app.schemas.task import (
    RcsRawSubmitRequest,
    RcsRawSubmitResult,
    RcsSubmitPreviewData,
    TaskCreateRequest,
    TaskCreateResponseData,
    TaskHistoryItem,
)
from app.services.rcs_submit_service import RcsSubmitService
from app.services.task_service import TaskService
from app.utils.redis_helper import get_redis

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_rcs() -> RCS2000Client:
    return get_rcs_client()


@router.get(
    "/rcs-preview",
    response_model=StandardResponse[RcsSubmitPreviewData],
    summary="RCS görev submit için çözümlenen taban URL, path ve örnek JSON",
    dependencies=[Depends(require_api_key)],
)
async def rcs_submit_preview(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[RcsSubmitPreviewData]:
    redis_client: Redis = await get_redis()
    svc = RcsSubmitService(session=session, redis_client=redis_client, rcs_client=_get_rcs())
    data = await svc.preview()
    return StandardResponse[RcsSubmitPreviewData](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=data,
    )


@router.post(
    "/rcs-submit",
    response_model=StandardResponse[RcsRawSubmitResult],
    status_code=status.HTTP_200_OK,
    summary="Postman tarzı: imzalı RCS isteği (path + JSON body)",
    dependencies=[Depends(require_api_key)],
)
async def rcs_submit_raw(
    request: Request,
    payload: RcsRawSubmitRequest,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    session: AsyncSession = Depends(get_db_session),
    rcs_client: RCS2000Client = Depends(_get_rcs),
) -> StandardResponse[RcsRawSubmitResult]:
    redis_client: Redis = await get_redis()
    svc = RcsSubmitService(session=session, redis_client=redis_client, rcs_client=rcs_client)
    data = await svc.submit_raw(request=payload, idempotency_key=idempotency_key)
    return StandardResponse[RcsRawSubmitResult](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=data,
    )


_TASK_CREATE_EXAMPLES = {
    "success": {
        "summary": "Task accepted by RCS",
        "value": {
            "success": True,
            "requestId": "8e7f0a86-7d1d-4c47-8c9e-7c5db8ea2bf3",
            "data": {
                "robotTaskCode": "TASK-20250419-001",
                "status": "pending",
                "cached": False,
            },
        },
    },
    "robot_type_not_found": {
        "summary": "Unknown robot type",
        "value": {
            "success": False,
            "requestId": "8e7f0a86-7d1d-4c47-8c9e-7c5db8ea2bf3",
            "error": {
                "code": "ROBOT_TYPE_NOT_FOUND",
                "message": "Robot type 'XYZ' not found.",
                "details": {"robotType": "XYZ"},
            },
        },
    },
}


@router.post(
    "/create",
    response_model=StandardResponse[TaskCreateResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new robot task",
    responses={
        201: {"content": {"application/json": {"examples": {"ok": _TASK_CREATE_EXAMPLES["success"]}}}},
        404: {
            "content": {
                "application/json": {
                    "examples": {"not_found": _TASK_CREATE_EXAMPLES["robot_type_not_found"]}
                }
            }
        },
    },
    dependencies=[Depends(require_api_key)],
)
async def create_task(
    request: Request,
    payload: TaskCreateRequest,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    session: AsyncSession = Depends(get_db_session),
    rcs_client: RCS2000Client = Depends(_get_rcs),
) -> StandardResponse[TaskCreateResponseData]:
    redis_client: Redis = await get_redis()
    service = TaskService(session=session, redis_client=redis_client, rcs_client=rcs_client)
    data = await service.create_task(request=payload, idempotency_key=idempotency_key)
    return StandardResponse[TaskCreateResponseData](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=data,
    )


@router.get(
    "/history",
    response_model=StandardResponse[dict],
    summary="List task history with pagination",
    dependencies=[Depends(require_api_key)],
)
async def list_task_history(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[dict]:
    # Build query
    query = select(TaskHistory).order_by(desc(TaskHistory.created_at))
    count_query = select(func.count()).select_from(TaskHistory)

    if status_filter:
        try:
            ts = TaskStatus(status_filter)
            query = query.where(TaskHistory.status == ts)
            count_query = count_query.where(TaskHistory.status == ts)
        except ValueError:
            pass  # ignore invalid status filter

    # Count total
    total = (await session.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    rows = (await session.execute(query)).scalars().all()

    items = [
        TaskHistoryItem(
            robot_task_code=r.robot_task_code,
            status=r.status.value if isinstance(r.status, TaskStatus) else str(r.status),
            robot_code=r.robot_code,
            source_code=r.source_code,
            target_code=r.target_code,
            error_msg=r.error_msg,
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

