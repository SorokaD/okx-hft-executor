"""
Порты доступа к бирже. Реализации: live OKX, paper, replay mock.

Доменные типы на границе метода — предпочтительнее «сырых» dict.
"""

from __future__ import annotations

from typing import Protocol

from domain.models.order import Order


class ExchangeClient(Protocol):
    """Минимальный контракт клиента биржи для каркаса."""

    async def place_order(self, order: Order) -> str:
        """Возвращает exchange order id или пустую строку, если модель async иная — уточнится в реализации."""
        ...

    async def cancel_order(self, client_order_id: str) -> None:
        ...
