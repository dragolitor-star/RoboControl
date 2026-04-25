"""Async HTTP client for the RCS-2000 platform.

Responsibilities:
    * Sign every outgoing request via the pluggable `SigningStrategy`.
    * Manage a long-lived `httpx.AsyncClient` (lifespan-controlled).
    * Apply tenacity retries ONLY for idempotent calls.
    * Translate RCS error envelopes into typed `RCSClientError` subclasses.
"""
from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.constants import (
    RCS_PATH_PREFIX,
    RCS_ROBOT_STATUS_PATH,
    RCS_TASK_CANCEL_PATH,
    RCS_TASK_SUBMIT_PATH,
)
from app.core.exceptions import RCSClientError, TaskNotStartedError
from app.core.logging import get_logger
from app.utils.redis_helper import get_redis
from app.utils.signing import SigningStrategy, get_signing_strategy

logger = get_logger(__name__)

# Errors we are willing to retry against (idempotent paths only).
_RETRYABLE_HTTP_EXC = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)


class _RetryableUpstreamError(Exception):
    """Internal marker for 5xx responses we want tenacity to retry."""


class RCS2000Client:
    """Thin async wrapper over RCS-2000 HTTP API."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        signing_strategy: SigningStrategy | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._signer: SigningStrategy = signing_strategy or get_signing_strategy()
        self._base_url = (base_url or settings.RCS_BASE_URL).rstrip("/")
        self._timeout = timeout or settings.RCS_TIMEOUT
        self._client_owned = client is None
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    # ----------------------------- lifecycle -------------------------------- #

    async def aclose(self) -> None:
        if self._client_owned and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "RCS2000Client":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ------------------------------ public API ------------------------------ #

    async def submit_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a task in RCS. NOT retried (non-idempotent)."""
        return await self._request(
            method="POST",
            path=RCS_PATH_PREFIX + RCS_TASK_SUBMIT_PATH,
            body=payload,
            idempotent=False,
        )

    async def get_robot_status(self, robot_code: str) -> dict[str, Any]:
        """Read robot status. Idempotent → retried."""
        return await self._request(
            method="GET",
            path=RCS_PATH_PREFIX + RCS_ROBOT_STATUS_PATH,
            body=None,
            idempotent=True,
            params={"robotCode": robot_code},
        )

    async def cancel_task(self, robot_task_code: str) -> dict[str, Any]:
        """Cancel an existing task. Idempotent (cancel of already-cancelled is a no-op) → retried."""
        return await self._request(
            method="POST",
            path=RCS_PATH_PREFIX + RCS_TASK_CANCEL_PATH,
            body={"robotTaskCode": robot_task_code},
            idempotent=True,
        )

    # ------------------------------ internals ------------------------------- #

    async def _request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        idempotent: bool,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if idempotent:
            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=1, max=8),
                    retry=retry_if_exception_type(
                        (_RetryableUpstreamError, *_RETRYABLE_HTTP_EXC)
                    ),
                    reraise=True,
                ):
                    with attempt:
                        return await self._do_request(method, path, body, params)
            except RetryError as exc:  # pragma: no cover - reraise=True normally surfaces
                raise RCSClientError(message=str(exc)) from exc
            # Loop exits via `return` in `attempt`; the line below is unreachable
            # but satisfies type checkers.
            raise RCSClientError("Retry loop exited without result")  # pragma: no cover
        return await self._do_request(method, path, body, params)

    async def _do_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8") if body else b""
        signed = self._signer.sign(method=method, path=path, body=body_bytes)

        merged_params: dict[str, Any] = dict(params or {})
        merged_params["sign"] = signed.sign

        logger.debug(
            "rcs_request",
            method=method,
            path=path,
            request_id=signed.request_id,
            trace_id=signed.trace_id,
        )

        redis_client = await get_redis()
        rcs_ip = await redis_client.get("sysconfig:rcs_ip")
        rcs_port = await redis_client.get("sysconfig:rcs_port")
        
        if rcs_ip and rcs_port:
            base_url = f"http://{rcs_ip}:{rcs_port}"
            full_url = f"{base_url}{path}"
        else:
            full_url = f"{self._base_url}{path}"

        try:
            response = await self._client.request(
                method=method,
                url=full_url,
                content=body_bytes if body_bytes else None,
                params=merged_params,
                headers=signed.headers,
            )
        except _RETRYABLE_HTTP_EXC:
            logger.warning("rcs_network_error", path=path, method=method)
            raise
        except httpx.HTTPError as exc:
            logger.error("rcs_http_error", path=path, error=str(exc))
            raise RCSClientError(message=f"HTTP error: {exc}") from exc

        return self._parse_response(response, path)

    def _parse_response(self, response: httpx.Response, path: str) -> dict[str, Any]:
        if response.status_code >= 500:
            logger.warning(
                "rcs_5xx",
                status=response.status_code,
                path=path,
                body=response.text[:512],
            )
            raise _RetryableUpstreamError(
                f"RCS 5xx {response.status_code} on {path}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise RCSClientError(
                message=f"RCS returned non-JSON body (status={response.status_code})"
            ) from exc

        if response.status_code >= 400:
            code = str(data.get("code", f"HTTP_{response.status_code}"))
            message = str(data.get("message", "RCS error"))
            self._raise_business_error(code, message, data)

        # Even on 200, RCS may signal a business error in the envelope.
        envelope_code = data.get("code")
        if envelope_code and envelope_code not in (0, "0", "Success", "OK", "success"):
            self._raise_business_error(
                str(envelope_code), str(data.get("message", "RCS error")), data
            )

        return data

    @staticmethod
    def _raise_business_error(code: str, message: str, payload: dict[str, Any]) -> None:
        # TODO(RCS-DOC): expand mapping once full RCS error code list is known.
        if code == "Err_TaskNotStart":
            raise TaskNotStartedError(message=message, details={"rcs_code": code, "payload": payload})
        raise RCSClientError(
            message=message,
            code=f"RCS_{code}",
            details={"rcs_code": code, "payload": payload},
        )


# --------------------------------------------------------------------------- #
# App-wide singleton (initialised in lifespan)                                 #
# --------------------------------------------------------------------------- #

_singleton: RCS2000Client | None = None


def init_rcs_client() -> RCS2000Client:
    global _singleton
    if _singleton is None:
        _singleton = RCS2000Client()
    return _singleton


async def shutdown_rcs_client() -> None:
    global _singleton
    if _singleton is not None:
        await _singleton.aclose()
        _singleton = None


def get_rcs_client() -> RCS2000Client:
    if _singleton is None:
        raise RuntimeError("RCS client not initialised; call init_rcs_client() first.")
    return _singleton
