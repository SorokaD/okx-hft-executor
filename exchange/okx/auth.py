"""Подпись REST-запросов OKX v5."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone


def make_timestamp() -> str:
    """RFC3339 timestamp с миллисекундами в UTC."""
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def sign_okx_request(
    *,
    secret_key: str,
    timestamp: str,
    method: str,
    request_path: str,
    body: str = "",
) -> str:
    """Возвращает Base64 подпись OKX (ts + method + path + body)."""
    payload = f"{timestamp}{method.upper()}{request_path}{body}".encode("utf-8")
    digest = hmac.new(secret_key.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")
