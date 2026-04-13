"""
Торговый сигнал: намерение стратегии до risk и execution.

Не содержит биржевых идентификаторов ордеров; связывается с intent/ордером на следующих этапах.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.enums.side import Side
from domain.value_objects.instrument_id import InstrumentId


@dataclass(slots=True)
class Signal:
    signal_id: str
    instrument: InstrumentId
    side: Side
    created_at: datetime
    strategy_id: str | None = None
    meta: dict[str, str] | None = None
