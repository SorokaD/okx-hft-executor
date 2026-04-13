"""
Заглушка клиента OKX для сборки графа зависимостей без сети.

Заменяется на REST/WS реализации на фазе 1 roadmap.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime, timezone

from config.settings import Settings
from domain.models.order import Order
from exchange.okx.models import OkxOrder, OkxPosition, OkxTicker

log = logging.getLogger(__name__)


class OkxStubExchangeClient:
    """Реализует подмножество ExchangeClient без I/O."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._price = Decimal("50000")
        self._tick_counter = 0
        self._orders: dict[str, OkxOrder] = {}

    async def place_order(self, order: Order) -> str:
        log.debug("stub place_order %s (demo=%s)", order.client_order_id, self._settings.okx_flag_demo)
        return "stub-exchange-order-id"

    async def cancel_order(self, client_order_id: str) -> None:
        log.debug("stub cancel_order %s", client_order_id)

    async def place_market_order(
        self, *, side: str, size: str, cl_ord_id: str, reduce_only: bool = False
    ) -> str:
        _ = reduce_only
        ord_id = f"stub-{cl_ord_id}"
        order = OkxOrder(
            ord_id=ord_id,
            cl_ord_id=cl_ord_id,
            state="filled",
            side=side,
            px=self._price,
            avg_px=self._price,
            sz=Decimal(size),
            fill_sz=Decimal(size),
        )
        self._orders[ord_id] = order
        return ord_id

    async def get_order(
        self, *, inst_id: str, ord_id: str | None = None, cl_ord_id: str | None = None
    ) -> OkxOrder | None:
        _ = inst_id
        if ord_id and ord_id in self._orders:
            return self._orders[ord_id]
        if cl_ord_id:
            for order in self._orders.values():
                if order.cl_ord_id == cl_ord_id:
                    return order
        return None

    async def get_open_orders(self, *, inst_id: str) -> list[OkxOrder]:
        _ = inst_id
        return []

    async def get_positions(self, *, inst_id: str) -> list[OkxPosition]:
        _ = inst_id
        return []

    async def get_account_snapshot(self) -> dict[str, object]:
        return {}

    async def get_ticker_last(self, *, inst_id: str) -> OkxTicker:
        _ = inst_id
        self._tick_counter += 1
        shift = Decimal("25") if self._tick_counter % 2 == 0 else Decimal("-20")
        self._price += shift
        ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        return OkxTicker(inst_id=self._settings.okx_inst_id, last=self._price, ts_ms=ts_ms)

    async def get_tick_size(self, *, inst_id: str) -> Decimal:
        _ = inst_id
        return Decimal("0.1")
