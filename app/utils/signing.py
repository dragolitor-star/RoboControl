"""RCS-2000 request signing.

THIS IS THE ONLY FILE THAT NEEDS TO CHANGE WHEN THE OFFICIAL RCS-2000
SPEC ARRIVES. The signing strategy is hidden behind a `Protocol` so the
client (`rcs2000_client.py`) and the rest of the code never need updates.

TODO(RCS-DOC): Validate the canonical-string layout below against the
official RCS-2000 documentation. Possible variations:
  * Body hash function (MD5 vs SHA-256)
  * Order of fields in the canonical string
  * Whether query string is included
  * Whether `Authorization` header carries the signature inline rather
    than as `?sign=` query parameter
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from app.core.config import settings


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _utc_iso8601() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _secure_nonce(length: int = 8) -> str:
    return secrets.token_hex(length)[:length]


# --------------------------------------------------------------------------- #
# Strategy interface                                                           #
# --------------------------------------------------------------------------- #


class SignedRequest:
    """Container for a fully-signed RCS request.

    `headers` is the dict to send on the wire. `sign` must be appended to
    the URL as `?sign={sign}` (or merged into existing query string).
    """

    __slots__ = ("headers", "sign", "nonce", "timestamp", "request_id", "trace_id")

    def __init__(
        self,
        *,
        headers: dict[str, str],
        sign: str,
        nonce: str,
        timestamp: str,
        request_id: str,
        trace_id: str,
    ) -> None:
        self.headers = headers
        self.sign = sign
        self.nonce = nonce
        self.timestamp = timestamp
        self.request_id = request_id
        self.trace_id = trace_id


class SigningStrategy(Protocol):
    """All RCS signing strategies must implement this interface."""

    def sign(self, *, method: str, path: str, body: bytes) -> SignedRequest: ...


# --------------------------------------------------------------------------- #
# Default strategy: HMAC-SHA256                                                #
# --------------------------------------------------------------------------- #


class HmacSha256Strategy:
    """HMAC-SHA256 over a canonical string of (timestamp, nonce, method, path, body_md5).

    This is a *plausible* layout matching common Hikrobot integration patterns;
    it MUST be confirmed against the RCS-2000 doc.
    """

    def __init__(
        self,
        *,
        app_key: str | None = None,
        app_secret: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._app_key = app_key or settings.RCS_APP_KEY
        self._app_secret = (
            app_secret if app_secret is not None else settings.RCS_APP_SECRET.get_secret_value()
        )
        self._api_version = api_version or settings.RCS_API_VERSION

    # ------------------------------ public API ------------------------------ #

    def sign(self, *, method: str, path: str, body: bytes) -> SignedRequest:
        timestamp = _utc_iso8601()
        nonce = _secure_nonce(8)
        request_id = str(uuid4())
        trace_id = str(uuid4())

        sign_value = self._build_sign(
            method=method, path=path, body=body, nonce=nonce, timestamp=timestamp
        )

        headers = {
            "Authorization": (
                f'nonce="{nonce}", method="HMAC-SHA256", timestamp="{timestamp}"'
            ),
            "X-lr-appkey": self._app_key,
            "X-lr-version": self._api_version,
            "X-lr-request-id": request_id,
            "X-lr-trace-id": trace_id,
            "Content-Type": "application/json;charset=UTF-8",
        }
        return SignedRequest(
            headers=headers,
            sign=sign_value,
            nonce=nonce,
            timestamp=timestamp,
            request_id=request_id,
            trace_id=trace_id,
        )

    # ---------------------- internals (testable directly) ------------------- #

    def build_canonical_string(
        self, *, method: str, path: str, body: bytes, nonce: str, timestamp: str
    ) -> str:
        """Format: timestamp\\nnonce\\nMETHOD\\npath\\nbody_md5

        TODO(RCS-DOC): Confirm field order and separator.
        """
        body_md5 = hashlib.md5(body or b"").hexdigest()
        return f"{timestamp}\n{nonce}\n{method.upper()}\n{path}\n{body_md5}"

    def _build_sign(
        self, *, method: str, path: str, body: bytes, nonce: str, timestamp: str
    ) -> str:
        canonical = self.build_canonical_string(
            method=method, path=path, body=body, nonce=nonce, timestamp=timestamp
        )
        return hmac.new(
            self._app_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()


def get_signing_strategy() -> SigningStrategy:
    """Factory returning the active signing strategy.

    Swap this body when the real RCS algorithm differs.
    """
    return HmacSha256Strategy()
