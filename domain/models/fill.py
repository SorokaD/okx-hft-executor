"""Факт исполнения (частичного или полного), идемпотентно задаётся exchange exec id."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from domain.enums.side import Side
from domain.value_objects.instrument_id import InstrumentId


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    order_client_id: str
    instrument: InstrumentId
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    filled_at: datetime
