"""
Управление жизненным циклом доменных заявок: создание intent, трекинг статусов.

Детали API OKX инкапсулируются в `exchange`; здесь только доменная логика.
"""

from __future__ import annotations

from domain.models.order import Order


class OrderManager:
    """Каркас; внутреннее хранилище заявок и связь с state machine добавятся позже."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def track(self, order: Order) -> None:
        self._orders[order.client_order_id] = order
