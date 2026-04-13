"""Технические и бизнес-метрики (каркас; позже Prometheus/OpenTelemetry)."""

from __future__ import annotations


def inc_placeholder_counter(name: str, value: int = 1) -> None:
    """Заглушка инкремента счётчика."""
    _ = (name, value)
