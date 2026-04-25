"""Business logic for task creation."""
from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.rcs2000_client import RCS2000Client
from app.core.constants import IDEMPOTENCY_KEY_TTL_SECONDS
from app.core.exceptions import DuplicateTaskError, RCSClientError, RobotTypeNotFoundError
from app.core.logging import get_logger
from app.models.task_history import TaskStatus
from app.repositories.robot_type_repository import RobotTypeRepository
from app.repositories.task_history_repository import TaskHistoryRepository
from app.schemas.task import TaskCreateRequest, TaskCreateResponseData
from app.utils.redis_helper import idempotency_key as build_idem_key

logger = get_logger(__name__)


class TaskService:
    """Orchestrates RobotType lookup → RCS submission → DB persistence."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        redis_client: Redis,
        rcs_client: RCS2000Client,
    ) -> None:
        self._session = session
        self._redis = redis_client
        self._rcs = rcs_client
        self._robot_types = RobotTypeRepository(session)
        self._tasks = TaskHistoryRepository(session)

    async def create_task(
        self,
        *,
        request: TaskCreateRequest,
        idempotency_key: str | None = None,
    ) -> TaskCreateResponseData:
        # 1. Idempotency cache check
        if idempotency_key:
            cached = await self._lookup_idempotency(idempotency_key, request)
            if cached is not None:
                logger.info("idempotency_hit", key=idempotency_key)
                return cached

        # 2. Resolve RobotType
        robot_type = await self._robot_types.get_by_name(request.robot_type)
        if robot_type is None:
            raise RobotTypeNotFoundError(
                message=f"Robot type '{request.robot_type}' not found.",
                details={"robotType": request.robot_type},
            )

        # 3. Build RCS submit payload
        payload = self._build_submit_payload(request, robot_type.rcs_task_type)

        # 4. Call RCS (NO retry — non-idempotent)
        try:
            rcs_response = await self._rcs.submit_task(payload)
        except RCSClientError:
            logger.exception("rcs_submit_failed", payload=payload)
            raise

        robot_task_code = self._extract_task_code(rcs_response)

        # 5. Persist TaskHistory + commit
        try:
            await self._tasks.create(
                robot_task_code=robot_task_code,
                status=TaskStatus.pending,
                source_code=request.source_code,
                target_code=request.target_code,
                idempotency_key=idempotency_key,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        result = TaskCreateResponseData(
            robot_task_code=robot_task_code,
            status=TaskStatus.pending.value,
            cached=False,
        )

        # 6. Cache idempotent response
        if idempotency_key:
            await self._save_idempotency(idempotency_key, request, result)

        logger.info(
            "task_created",
            robot_task_code=robot_task_code,
            robot_type=request.robot_type,
            idempotent=bool(idempotency_key),
        )
        return result

    # --------------------------- helpers ----------------------------------- #

    @staticmethod
    def _build_submit_payload(req: TaskCreateRequest, rcs_task_type: str) -> dict[str, Any]:
        """Translate internal request into RCS payload.

        TODO(RCS-DOC): `targetRoute` schema is a guess. Confirm whether RCS
        expects a flat dict, a list of waypoints, or a routing graph node.
        """
        return {
            "taskTyp": rcs_task_type,
            "sourceCode": req.source_code,
            "targetRoute": _build_target_route(req),
            "priority": req.priority,
        }

    @staticmethod
    def _extract_task_code(rcs_response: dict[str, Any]) -> str:
        # RCS-2000 typically returns {"data": {"robotTaskCode": "..."}}
        data = rcs_response.get("data") or {}
        code = data.get("robotTaskCode") or rcs_response.get("robotTaskCode")
        if not code:
            raise RCSClientError(
                message="RCS submit response missing robotTaskCode",
                code="RCS_MALFORMED_RESPONSE",
                details={"response": rcs_response},
            )
        return str(code)

    async def _lookup_idempotency(
        self, key: str, request: TaskCreateRequest
    ) -> TaskCreateResponseData | None:
        cached_raw = await self._redis.get(build_idem_key(key))
        if not cached_raw:
            return None
        try:
            cached = json.loads(cached_raw)
        except (TypeError, ValueError):
            return None

        # Reject collisions: same key, different payload.
        if cached.get("request_fingerprint") != _fingerprint(request):
            raise DuplicateTaskError(
                message="Idempotency-Key reused with a different payload.",
                details={"idempotency_key": key},
            )

        data = cached.get("response") or {}
        return TaskCreateResponseData(
            robot_task_code=data["robotTaskCode"],
            status=data["status"],
            cached=True,
        )

    async def _save_idempotency(
        self,
        key: str,
        request: TaskCreateRequest,
        result: TaskCreateResponseData,
    ) -> None:
        envelope = {
            "request_fingerprint": _fingerprint(request),
            "response": result.model_dump(by_alias=True),
        }
        await self._redis.setex(
            build_idem_key(key),
            IDEMPOTENCY_KEY_TTL_SECONDS,
            json.dumps(envelope),
        )


def _fingerprint(request: TaskCreateRequest) -> str:
    return json.dumps(
        request.model_dump(by_alias=True), sort_keys=True, separators=(",", ":")
    )


def _build_target_route(req: TaskCreateRequest) -> dict[str, Any]:
    """Public helper so unit tests can target it directly.

    TODO(RCS-DOC): Real schema TBD; current shape is `{targetCode, priority}`.
    """
    return {"targetCode": req.target_code, "priority": req.priority}
