"""
Заглушка клиента OKX для сборки графа зависимостей без сети.

Заменяется на REST/WS реализации на фазе 1 roadmap.
"""

from __future__ import annotations

import logging

from config.settings import Settings
from domain.models.order import Order

log = logging.getLogger(__name__)


class OkxStubExchangeClient:
    """Реализует подмножество ExchangeClient без I/O."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def place_order(self, order: Order) -> str:
        log.debug("stub place_order %s (demo=%s)", order.client_order_id, self._settings.okx_flag_demo)
        return "stub-exchange-order-id"

    async def cancel_order(self, client_order_id: str) -> None:
        log.debug("stub cancel_order %s", client_order_id)
