"""Constants used across services.

Keep magic strings/numbers here so they don't drift between modules.
"""
from __future__ import annotations

TASK_METHOD_TO_STATUS: dict[str, str] = {
    "start": "running",
    "outbin": "running",
    "end": "completed",
}

ROBOT_STATE_TTL_SECONDS: int = 300
"""Heartbeat TTL for robot state in Redis (5 minutes).

TODO(OPS): Tune this once we know the real RCS heartbeat cadence.
"""

IDEMPOTENCY_KEY_TTL_SECONDS: int = 86400
"""How long an Idempotency-Key remains valid (24 hours)."""

REDIS_ROBOT_STATE_PREFIX: str = "robot:{amr_code}:state"
REDIS_ROBOT_STATE_SCAN_PATTERN: str = "robot:*:state"
REDIS_IDEMPOTENCY_PREFIX: str = "idempotency:{key}"
REDIS_WEBHOOK_DEDUPE_PREFIX: str = "webhook:dedupe:{robot_task_code}:{method}"

WEBHOOK_DEDUPE_TTL_SECONDS: int = 3600

RCS_PATH_PREFIX: str = "/rcs/rtas"
RCS_TASK_SUBMIT_PATH: str = "/api/robot/controller/task/submit"
RCS_TASK_CANCEL_PATH: str = "/api/robot/controller/task/cancel"
RCS_ROBOT_STATUS_PATH: str = "/api/robot/controller/robot/status"

REQUEST_ID_HEADER: str = "X-Request-ID"
API_KEY_HEADER: str = "X-API-Key"
IDEMPOTENCY_HEADER: str = "Idempotency-Key"
WEBHOOK_SIGNATURE_HEADER: str = "X-Webhook-Signature"

SENSITIVE_LOG_FIELDS: frozenset[str] = frozenset(
    {"password", "secret", "token", "authorization", "x-api-key", "x-webhook-signature"}
)
