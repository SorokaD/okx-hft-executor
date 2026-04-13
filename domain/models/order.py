"""
Доменная заявка после принятия risk и маппинга в контур биржи.

Поля расширяются политикой исполнения (TIF, reduce-only, posSide и т.д.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from domain.enums.order_status import OrderStatus
from domain.enums.side import Side
from domain.value_objects.instrument_id import InstrumentId


@dataclass(slots=True)
class Order:
    client_order_id: str
    instrument: InstrumentId
    side: Side
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    quantity: Decimal
    price: Decimal | None = None
    exchange_order_id: str | None = None
    extra: dict[str, str] = field(default_factory=dict)
