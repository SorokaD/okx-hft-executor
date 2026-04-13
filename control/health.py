"""Логика health/readiness для выдачи наружу (без привязки к конкретному ASGI фреймворку)."""

from __future__ import annotations

from services.health import HealthStatus, process_alive


def get_liveness() -> HealthStatus:
    return process_alive()
