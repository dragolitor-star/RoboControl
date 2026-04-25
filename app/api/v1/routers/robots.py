"""GET /api/v1/robots/status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.security import require_api_key
from app.schemas.common import StandardResponse
from app.schemas.robot import RobotStatusResponse
from app.services.robot_service import RobotService
from app.utils.redis_helper import get_redis

router = APIRouter(prefix="/robots", tags=["robots"])


@router.get(
    "/status",
    response_model=StandardResponse[list[RobotStatusResponse]],
    summary="List current robot states (from Redis cache)",
    dependencies=[Depends(require_api_key)],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "requestId": "8e7f0a86-7d1d-4c47-8c9e-7c5db8ea2bf3",
                        "data": [
                            {
                                "amrCode": "AMR-001",
                                "x": 12.5,
                                "y": 8.3,
                                "state": "running",
                                "updatedAt": "2026-04-25T10:11:12",
                            }
                        ],
                    }
                }
            }
        }
    },
)
async def list_robot_status(request: Request) -> StandardResponse[list[RobotStatusResponse]]:
    redis_client = await get_redis()
    service = RobotService(redis_client)
    items = await service.list_robot_states()
    return StandardResponse[list[RobotStatusResponse]](
        success=True,
        request_id=getattr(request.state, "request_id", ""),
        data=items,
    )
