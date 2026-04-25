"""GET /api/v1/system/stats — Dashboard summary statistics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.schemas.common import StandardResponse
from app.schemas.stats import SystemStats
from app.schemas.system import ConnectionSettingsUpdate, ConnectionSettingsResponse
from app.services.stats_service import StatsService
from app.repositories.system_config_repository import SystemConfigRepository
from app.utils.redis_helper import get_redis

router = APIRouter(prefix="/system", tags=["system"])


@router.get(
    "/stats",
    response_model=StandardResponse[SystemStats],
    summary="Dashboard summary statistics",
    dependencies=[Depends(require_api_key)],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "requestId": "8e7f0a86-7d1d-4c47-8c9e-7c5db8ea2bf3",
                        "data": {
                            "activeRobots": 3,
                            "pendingTasks": 2,
                            "runningTasks": 1,
                            "completedTasksToday": 15,
                            "failedTasksToday": 0,
                            "totalTasks": 42,
                            "dbStatus": "ok",
                            "redisStatus": "ok",
                        },
                    }
                }
            }
        }
    },
)
async def system_stats(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[SystemStats]:
    redis_client = await get_redis()
    service = StatsService(session=session, redis_client=redis_client)
    data = await service.get_stats()
    return StandardResponse[SystemStats](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=data,
    )


@router.get(
    "/config",
    response_model=StandardResponse[ConnectionSettingsResponse],
    summary="Get system connection configuration",
    dependencies=[Depends(require_api_key)],
)
async def get_system_config(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[ConnectionSettingsResponse]:
    redis_client = await get_redis()
    repo = SystemConfigRepository(session=session, redis_client=redis_client)
    data = await repo.get_connection_settings()
    return StandardResponse[ConnectionSettingsResponse](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=ConnectionSettingsResponse(**data),
    )


@router.put(
    "/config",
    response_model=StandardResponse[ConnectionSettingsResponse],
    summary="Update system connection configuration",
    dependencies=[Depends(require_api_key)],
)
async def update_system_config(
    payload: ConnectionSettingsUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> StandardResponse[ConnectionSettingsResponse]:
    redis_client = await get_redis()
    repo = SystemConfigRepository(session=session, redis_client=redis_client)
    
    await repo.set("rcs_ip", payload.rcs_ip)
    await repo.set("rcs_port", str(payload.rcs_port))
    
    data = await repo.get_connection_settings()
    return StandardResponse[ConnectionSettingsResponse](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=ConnectionSettingsResponse(**data),
    )
