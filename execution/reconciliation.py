"""
Оркестрация сверки локального состояния с биржей.

Вызывает exchange для snapshot и согласует OrderManager/PositionManager;
детали политики — в docs/reconciliation.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from exchange.protocols import ExchangeClient
    from execution.order_manager import OrderManager
    from execution.position_manager import PositionManager


class ReconciliationService(Protocol):
    async def run_cycle(self) -> None:
        """Один цикл сверки (по расписанию или триггеру)."""
        ...


class StubReconciliationService:
    """Заглушка до реализации REST snapshot и сравнения."""

    def __init__(
        self,
        exchange: ExchangeClient,
        orders: OrderManager,
        positions: PositionManager,
    ) -> None:
        self._exchange = exchange
        self._orders = orders
        self._positions = positions

    async def run_cycle(self) -> None:
        _ = (self._exchange, self._orders, self._positions)
        return None
