"""Robot status reporting service (Redis-backed)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

from app.core.constants import REDIS_ROBOT_STATE_SCAN_PATTERN
from app.core.logging import get_logger
from app.schemas.robot import RobotStatusResponse
from app.utils.redis_helper import scan_iter

logger = get_logger(__name__)


class RobotService:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def list_robot_states(self) -> list[RobotStatusResponse]:
        """Iterate `robot:*:state` via SCAN — never KEYS.

        Empty Redis → empty list (no mock data, by design).
        """
        results: list[RobotStatusResponse] = []
        async for key in scan_iter(self._redis, match=REDIS_ROBOT_STATE_SCAN_PATTERN):
            raw = await self._redis.get(key)
            if not raw:
                continue
            payload = self._decode(raw)
            if not payload:
                continue
            try:
                results.append(self._to_schema(key, payload))
            except (KeyError, ValueError, TypeError):
                logger.warning("robot_state_decode_failed", key=key)
        return results

    @staticmethod
    def _decode(raw: str) -> dict[str, Any] | None:
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_schema(key: str, payload: dict[str, Any]) -> RobotStatusResponse:
        amr_code = payload.get("amrCode") or _extract_amr_code(key)
        updated_at_raw = payload.get("updatedAt")
        updated_at = (
            datetime.fromisoformat(updated_at_raw) if isinstance(updated_at_raw, str) else None
        )
        return RobotStatusResponse(
            amr_code=amr_code,
            x=payload.get("x"),
            y=payload.get("y"),
            state=payload.get("state"),
            updated_at=updated_at,
        )


def _extract_amr_code(key: str) -> str:
    # key format: robot:{amr_code}:state
    parts = key.split(":")
    return parts[1] if len(parts) >= 2 else key
