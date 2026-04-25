"""structlog-based JSON logging.

All logs are JSON in production for easy ingestion by ELK / Loki / Datadog.
A `request_id` context variable is injected by the request middleware so
every log line emitted during a request can be correlated.
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.config import settings
from app.core.constants import SENSITIVE_LOG_FIELDS

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)


def _add_request_context(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    rid = request_id_ctx.get()
    tid = trace_id_ctx.get()
    if rid is not None:
        event_dict.setdefault("request_id", rid)
    if tid is not None:
        event_dict.setdefault("trace_id", tid)
    return event_dict


def _mask_sensitive(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact obvious secret-bearing fields anywhere in the event dict."""
    for key in list(event_dict.keys()):
        lowered = key.lower()
        if lowered in SENSITIVE_LOG_FIELDS or any(s in lowered for s in ("secret", "token", "password")):
            event_dict[key] = "***"
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _mask_dict(event_dict[key])
    return event_dict


def _mask_dict(value: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for k, v in value.items():
        lk = k.lower()
        if lk in SENSITIVE_LOG_FIELDS or any(s in lk for s in ("secret", "token", "password")):
            masked[k] = "***"
        elif isinstance(v, dict):
            masked[k] = _mask_dict(v)
        else:
            masked[k] = v
    return masked


def configure_logging() -> None:
    """Configure structlog + the stdlib root logger.

    Call once during application start-up.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    logging.getLogger("uvicorn.access").handlers.clear()

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_context,
        _mask_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.APP_ENV == "dev":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
