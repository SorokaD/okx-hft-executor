"""
Явные переходы статусов заявки и связанные инварианты.

Предотвращает недопустимые переходы (например filled → open) и централизует побочные эффекты.
"""

from __future__ import annotations

from domain.enums.order_status import OrderStatus
from domain.models.order import Order


class OrderStateMachine:
    """Минимальный каркас; полная таблица переходов добавляется с тестами."""

    @staticmethod
    def apply_fill_progress(order: Order, new_status: OrderStatus) -> None:
        """Заглушка перехода; в реализации — валидация и обновление timestamps."""
        order.status = new_status
