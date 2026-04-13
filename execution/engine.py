"""
Execution engine: координация менеджеров и обработка событий из exchange.

Реализация run-loop появится на фазе 1–2 roadmap; сейчас задан контракт класса.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exchange.protocols import ExchangeClient
    from persistence.unit_of_work import UnitOfWork
    from risk.guards import TradingGuards


class ExecutionEngine:
    """Точка входа исполнительного контура внутри процесса."""

    def __init__(
        self,
        exchange: ExchangeClient,
        guards: TradingGuards,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._exchange = exchange
        self._guards = guards
        self._unit_of_work = unit_of_work

    async def run_forever(self) -> None:
        """Будущий главный цикл; сейчас не вызывается из production-кода."""
        raise NotImplementedError
