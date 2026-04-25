"""Unit tests for the HMAC signing strategy."""
from __future__ import annotations

from app.utils.signing import HmacSha256Strategy


def test_canonical_string_format() -> None:
    strategy = HmacSha256Strategy(app_key="ak", app_secret="secret", api_version="1.0")
    canonical = strategy.build_canonical_string(
        method="post",
        path="/rcs/rtas/api/robot/controller/task/submit",
        body=b'{"a":1}',
        nonce="abcd1234",
        timestamp="2026-04-25T10:00:00.000000Z",
    )

    lines = canonical.split("\n")
    assert lines[0] == "2026-04-25T10:00:00.000000Z"
    assert lines[1] == "abcd1234"
    assert lines[2] == "POST"
    assert lines[3] == "/rcs/rtas/api/robot/controller/task/submit"
    assert len(lines[4]) == 32  # md5 hex


def test_sign_is_deterministic() -> None:
    strategy = HmacSha256Strategy(app_key="ak", app_secret="secret", api_version="1.0")
    args = dict(
        method="POST",
        path="/p",
        body=b"{}",
        nonce="aaaa",
        timestamp="2026-04-25T10:00:00.000000Z",
    )
    assert strategy._build_sign(**args) == strategy._build_sign(**args)


def test_sign_changes_when_body_changes() -> None:
    strategy = HmacSha256Strategy(app_key="ak", app_secret="secret", api_version="1.0")
    common = dict(
        method="POST",
        path="/p",
        nonce="aaaa",
        timestamp="2026-04-25T10:00:00.000000Z",
    )
    sig_1 = strategy._build_sign(body=b"{}", **common)
    sig_2 = strategy._build_sign(body=b'{"x":1}', **common)
    assert sig_1 != sig_2


def test_signed_request_has_required_headers() -> None:
    strategy = HmacSha256Strategy(app_key="my-key", app_secret="secret", api_version="1.0")
    signed = strategy.sign(method="POST", path="/p", body=b"{}")
    assert signed.headers["X-lr-appkey"] == "my-key"
    assert signed.headers["X-lr-version"] == "1.0"
    assert "Authorization" in signed.headers
    assert signed.sign  # non-empty
