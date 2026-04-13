"""Усечённое представление рынка для стратегии и guard-ов (bid/ask/время)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from domain.value_objects.instrument_id import InstrumentId


@dataclass(frozen=True, slots=True)
class MarketState:
    instrument: InstrumentId
    bid: Decimal
    ask: Decimal
    last_update: datetime
