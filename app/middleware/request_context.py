"""Request-context middleware.

Generates / propagates `X-Request-ID`, attaches it to log context, measures
request latency, and emits one structured access-log line per request.
"""
from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER
from app.core.logging import get_logger, request_id_ctx, trace_id_ctx

logger = get_logger("request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        trace_id = request.headers.get("X-Trace-ID") or request_id

        rid_token = request_id_ctx.set(request_id)
        tid_token = trace_id_ctx.set(trace_id)
        structlog.contextvars.bind_contextvars(request_id=request_id, trace_id=trace_id)

        request.state.request_id = request_id
        request.state.trace_id = trace_id

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            latency_ms = (time.perf_counter() - started) * 1000.0
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                latency_ms=round(latency_ms, 2),
                client=request.client.host if request.client else None,
            )
            structlog.contextvars.unbind_contextvars("request_id", "trace_id")
            request_id_ctx.reset(rid_token)
            trace_id_ctx.reset(tid_token)
