from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from domain.enums.order_status import OrderStatus
from domain.enums.side import Side
from domain.models.order import Order
from domain.value_objects.instrument_id import InstrumentId
from risk.guards import TradingGuards
from risk.kill_switch import KillSwitch


def test_trading_guards_respects_kill_switch() -> None:
    ks = KillSwitch()
    g = TradingGuards(ks)
    order = Order(
        client_order_id="c1",
        instrument=InstrumentId("BTC-USDT-SWAP"),
        side=Side.BUY,
        status=OrderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        quantity=Decimal("1"),
    )
    assert g.allow_new_order(order) is True
    ks.arm()
    assert g.allow_new_order(order) is False
