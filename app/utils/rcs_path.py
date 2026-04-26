"""Normalize RCS URL/path input from dashboards (Postman-style editors)."""
from __future__ import annotations

from urllib.parse import urlparse


def normalize_rcs_path(path_or_url: str) -> str:
    """Return path starting with `/`, without query string.

    Accepts either a path (`/rcs/rtas/...`) or a full URL; host and scheme
    are ignored so the server always calls the configured RCS base (no SSRF).
    """
    raw = (path_or_url or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        path = parsed.path or "/"
    else:
        path = raw if raw.startswith("/") else f"/{raw}"
    if "?" in path:
        path = path.split("?", 1)[0]
    return path
