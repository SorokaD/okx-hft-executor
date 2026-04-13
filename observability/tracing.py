"""Hooks для распределённой трассировки (OpenTelemetry и т.п.)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def span_placeholder(name: str) -> Iterator[None]:
    """Контекстный менеджер-заглушка для будущих span."""
    _ = name
    yield
