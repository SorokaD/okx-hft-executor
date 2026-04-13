"""
Базовый тип доменного события.

Конкретные подтипы (OrderPlaced, FillReceived, …) добавляются по мере
введения event bus или журнала событий.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: str
    name: str
    occurred_at: datetime
