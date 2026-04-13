"""Событие риск-контура: отказ, предупреждение, срабатывание kill switch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RiskEvent:
    event_id: str
    code: str
    message: str
    severity: str
    occurred_at: datetime
