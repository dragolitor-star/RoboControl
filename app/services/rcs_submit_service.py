"""Postman-style RCS submit: preview URL/body and dispatch signed HTTP calls."""
from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.rcs2000_client import RCS2000Client
from app.core.constants import (
    IDEMPOTENCY_KEY_TTL_SECONDS,
    RCS_PATH_PREFIX,
    RCS_TASK_SUBMIT_PATH,
)
from app.core.exceptions import DuplicateTaskError, InvalidRcsPathError, RCSClientError
from app.core.logging import get_logger
from app.models.task_history import TaskStatus
from app.repositories.system_config_repository import SystemConfigRepository
from app.repositories.task_history_repository import TaskHistoryRepository
from app.schemas.task import (
    RcsRawSubmitRequest,
    RcsRawSubmitResult,
    RcsSubmitPreviewData,
)
from app.utils.rcs_path import normalize_rcs_path

logger = get_logger(__name__)

_IDEM_PREFIX_RAW = "idempotency:rcs_raw:"


def _validate_rcs_path(path: str) -> None:
    if ".." in path or not path.startswith(RCS_PATH_PREFIX):
        raise InvalidRcsPathError(
            message=f"Path must start with '{RCS_PATH_PREFIX}' and must not contain '..'.",
            details={"path": path},
        )


def _default_submit_path() -> str:
    return f"{RCS_PATH_PREFIX}{RCS_TASK_SUBMIT_PATH}"


def _example_submit_body() -> dict[str, Any]:
    """Default template matching typical CTU-style submits (customer reference)."""
    return {
        "taskType": "CT71",
        "targetRoute": [
            {"type": "SITE", "code": "PW-CELL-3"},
            {"type": "SITE", "code": "GP"},
        ],
        "extra": {
            "carrierInfo": [
                {"carrierType": "4", "carrierCode": "100003"},
            ],
        },
    }


def _extract_task_code(rcs_response: dict[str, Any]) -> str | None:
    data = rcs_response.get("data") or {}
    code = data.get("robotTaskCode") or rcs_response.get("robotTaskCode")
    return str(code) if code else None


def _meta_from_body(body: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Best-effort fields for TaskHistory when body shape varies (flat vs list targetRoute)."""
    if not body:
        return None, None
    source = body.get("sourceCode")
    source_code: str | None = source if isinstance(source, str) else None
    target_code: str | None = None
    tr = body.get("targetRoute")
    if isinstance(tr, list) and tr:
        codes: list[str] = []
        for step in tr:
            if isinstance(step, dict):
                c = step.get("code")
                if isinstance(c, str):
                    codes.append(c)
        if codes:
            target_code = " → ".join(codes)
    elif isinstance(tr, dict):
        tc = tr.get("targetCode")
        if isinstance(tc, str):
            target_code = tc
    if target_code is None:
        tc2 = body.get("targetCode")
        if isinstance(tc2, str):
            target_code = tc2
    return source_code, target_code


def _raw_fingerprint(method: str, path: str, body: dict[str, Any] | None) -> str:
    return json.dumps(
        {"method": method.upper(), "path": path, "body": body or {}},
        sort_keys=True,
        separators=(",", ":"),
    )


class RcsSubmitService:
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
        self._tasks = TaskHistoryRepository(session)

    async def preview(self) -> RcsSubmitPreviewData:
        repo = SystemConfigRepository(session=self._session, redis_client=self._redis)
        conn = await repo.get_connection_settings()
        base = str(conn.get("rcs_base_url") or "").rstrip("/")
        path = _default_submit_path()
        return RcsSubmitPreviewData(
            resolved_base_url=base,
            method="POST",
            path=path,
            full_url_without_sign=f"{base}{path}",
            example_body=_example_submit_body(),
        )

    async def submit_raw(
        self,
        *,
        request: RcsRawSubmitRequest,
        idempotency_key: str | None,
    ) -> RcsRawSubmitResult:
        path = normalize_rcs_path(request.path)
        if not path:
            raise InvalidRcsPathError(message="Path is empty.", details={})
        _validate_rcs_path(path)

        if idempotency_key:
            cached = await self._lookup_idempotency(idempotency_key, request)
            if cached is not None:
                return cached

        try:
            rcs_response = await self._rcs.signed_request(
                method=request.method,
                path=path,
                body=request.body if request.method == "POST" else None,
            )
        except RCSClientError:
            logger.exception("rcs_raw_submit_failed", path=path, method=request.method)
            raise
        except Exception as exc:
            logger.exception(
                "rcs_raw_submit_unexpected",
                path=path,
                method=request.method,
                error=str(exc),
            )
            raise RCSClientError(
                message=f"RCS connection failed: {exc}",
                code="RCS_NETWORK_ERROR",
                details={"path": path, "method": request.method},
            ) from exc

        robot_task_code = _extract_task_code(rcs_response)
        persisted = False
        if request.persist_task and robot_task_code:
            source_code, target_code = _meta_from_body(request.body)
            try:
                await self._tasks.create(
                    robot_task_code=robot_task_code,
                    status=TaskStatus.pending,
                    source_code=source_code,
                    target_code=target_code,
                    idempotency_key=idempotency_key,
                )
                await self._session.commit()
                persisted = True
            except Exception:
                await self._session.rollback()
                raise

        result = RcsRawSubmitResult(
            robot_task_code=robot_task_code,
            status=TaskStatus.pending.value if robot_task_code else None,
            cached=False,
            persisted=persisted,
            rcs=rcs_response,
        )

        if idempotency_key:
            await self._save_idempotency(idempotency_key, request, path, result)

        logger.info(
            "rcs_raw_submit_ok",
            path=path,
            method=request.method,
            robot_task_code=robot_task_code,
            persisted=persisted,
        )
        return result

    async def _lookup_idempotency(
        self, key: str, request: RcsRawSubmitRequest
    ) -> RcsRawSubmitResult | None:
        raw = await self._redis.get(_idem_key(key))
        if not raw:
            return None
        try:
            envelope = json.loads(raw)
        except (TypeError, ValueError):
            return None
        path = normalize_rcs_path(request.path)
        if envelope.get("fingerprint") != _raw_fingerprint(request.method, path, request.body):
            raise DuplicateTaskError(
                message="Idempotency-Key reused with a different RCS request.",
                details={"idempotency_key": key},
            )
        data = envelope.get("result") or {}
        return RcsRawSubmitResult.model_validate(data)

    async def _save_idempotency(
        self,
        key: str,
        request: RcsRawSubmitRequest,
        normalized_path: str,
        result: RcsRawSubmitResult,
    ) -> None:
        envelope = {
            "fingerprint": _raw_fingerprint(request.method, normalized_path, request.body),
            "result": result.model_dump(by_alias=True),
        }
        await self._redis.setex(
            _idem_key(key),
            IDEMPOTENCY_KEY_TTL_SECONDS,
            json.dumps(envelope),
        )


def _idem_key(client_key: str) -> str:
    return f"{_IDEM_PREFIX_RAW}{client_key}"
