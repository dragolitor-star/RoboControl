"""Security primitives: API-key auth dependency + webhook signature verification."""
from __future__ import annotations

import hashlib
import hmac

from fastapi import Header, status
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.constants import API_KEY_HEADER, WEBHOOK_SIGNATURE_HEADER
from app.core.exceptions import AuthenticationError, WebhookSignatureError

api_key_header_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def require_api_key(api_key: str | None = Header(default=None, alias=API_KEY_HEADER)) -> str:
    """Constant-time comparison against the configured API_KEY."""
    expected = settings.API_KEY.get_secret_value()
    if not api_key or not hmac.compare_digest(api_key.encode(), expected.encode()):
        raise AuthenticationError(http_status=status.HTTP_401_UNAUTHORIZED)
    return api_key


def compute_webhook_signature(body: bytes) -> str:
    """HMAC-SHA256 hex digest using `WEBHOOK_SECRET`.

    TODO(RCS-DOC): RCS-2000 may use a different canonical string or
    HMAC encoding. Update only this function when the spec arrives.
    """
    secret = settings.WEBHOOK_SECRET.get_secret_value().encode()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def verify_webhook_signature(body: bytes, signature: str | None) -> None:
    """Constant-time signature verification; raise on mismatch."""
    if not signature:
        raise WebhookSignatureError("Missing webhook signature header")
    expected = compute_webhook_signature(body)
    if not hmac.compare_digest(expected, signature.strip()):
        raise WebhookSignatureError("Webhook signature mismatch")


async def webhook_signature_dependency(
    x_webhook_signature: str | None = Header(default=None, alias=WEBHOOK_SIGNATURE_HEADER),
) -> str:
    if not x_webhook_signature:
        raise WebhookSignatureError("Missing webhook signature header")
    return x_webhook_signature
