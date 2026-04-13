"""Снимок PnL на момент времени; детальный расчёт — в пакете `accounting`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PnlSnapshot:
    as_of: datetime
    realized: Decimal
    unrealized: Decimal
    currency: str
