"""Liveness + readiness HTTP endpoints (mounted at /health/...)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.observability.health import readiness_report
from app.utils.redis_helper import get_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    summary="Liveness probe — always 200 if process is alive",
    status_code=status.HTTP_200_OK,
)
async def liveness(request: Request) -> dict[str, str]:
    return {"status": "ok", "request_id": getattr(request.state, "request_id", "")}


@router.get(
    "/ready",
    summary="Readiness probe — verifies DB + Redis",
)
async def readiness(
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    redis_client = await get_redis()
    ok, report = await readiness_report(session=session, redis_client=redis_client)
    return JSONResponse(
        status_code=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=report,
    )
