"""Агрегированная позиция по инструменту (упрощённый каркас)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from domain.value_objects.instrument_id import InstrumentId


@dataclass(slots=True)
class Position:
    instrument: InstrumentId
    net_size: Decimal
    avg_entry_price: Decimal | None = None
