"""Контракты и триггеры операционных алертов (интеграция с внешними системами — позже)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Alert:
    name: str
    severity: str
    message: str


def emit_alert_placeholder(alert: Alert) -> None:
    _ = alert
