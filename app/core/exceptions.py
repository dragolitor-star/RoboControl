"""Custom exception hierarchy + global FastAPI handlers.

All errors raised by the service inherit from `BaseAppError` so the handler
can produce a consistent `StandardResponse` envelope no matter where the
exception is raised.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.common import ErrorDetail, StandardResponse

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Exception hierarchy                                                          #
# --------------------------------------------------------------------------- #


class BaseAppError(Exception):
    """All domain errors inherit from this."""

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        http_status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.http_status = http_status or self.http_status
        self.details = details
        super().__init__(self.message)


class RCSClientError(BaseAppError):
    """Generic upstream RCS-2000 failure (HTTP or business code)."""

    http_status = status.HTTP_502_BAD_GATEWAY
    code = "RCS_UPSTREAM_ERROR"
    message = "Upstream RCS-2000 returned an error."


class TaskNotStartedError(RCSClientError):
    """Maps to RCS-2000 `Err_TaskNotStart`."""

    http_status = status.HTTP_409_CONFLICT
    code = "TASK_NOT_STARTED"
    message = "RCS reports the task has not started yet."


class RobotTypeNotFoundError(BaseAppError):
    http_status = status.HTTP_404_NOT_FOUND
    code = "ROBOT_TYPE_NOT_FOUND"
    message = "Robot type not found."


class TaskNotFoundError(BaseAppError):
    http_status = status.HTTP_404_NOT_FOUND
    code = "TASK_NOT_FOUND"
    message = "Task not found."


class DuplicateTaskError(BaseAppError):
    """Raised when two requests collide on the same Idempotency-Key but
    carry different payloads."""

    http_status = status.HTTP_409_CONFLICT
    code = "DUPLICATE_TASK"
    message = "A task with the same Idempotency-Key already exists."


class WebhookSignatureError(BaseAppError):
    http_status = status.HTTP_401_UNAUTHORIZED
    code = "WEBHOOK_SIGNATURE_INVALID"
    message = "Webhook signature is missing or invalid."


class AuthenticationError(BaseAppError):
    http_status = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    message = "Missing or invalid API key."


# --------------------------------------------------------------------------- #
# Handlers                                                                     #
# --------------------------------------------------------------------------- #


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or ""


def _envelope(request_id: str, code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return StandardResponse(
        success=False,
        request_id=request_id,
        error=ErrorDetail(code=code, message=message, details=details),
    ).model_dump(by_alias=True, exclude_none=True)


async def _app_error_handler(request: Request, exc: BaseAppError) -> JSONResponse:
    logger.warning(
        "app_error",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=_envelope(_request_id(request), exc.code, exc.message, exc.details),
    )


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning("http_exception", status=exc.status_code, detail=exc.detail, path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(_request_id(request), f"HTTP_{exc.status_code}", str(exc.detail)),
    )


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("validation_error", errors=exc.errors(), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_envelope(
            _request_id(request),
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": exc.errors()},
        ),
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    # Stack trace lands in the JSON log; client sees a generic message.
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_envelope(_request_id(request), "INTERNAL_ERROR", "Internal server error"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BaseAppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
