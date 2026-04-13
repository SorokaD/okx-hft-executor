"""Простые проверки готовности зависимостей (без FastAPI; см. `control` для HTTP)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    ok: bool
    detail: str


def process_alive() -> HealthStatus:
    """Минимальная заглушка; позже — ping БД, доступность API биржи по read-only."""
    return HealthStatus(ok=True, detail="process up")
