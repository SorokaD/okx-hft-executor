"""
Правила выхода из позиции (take-profit, stop, время в сделке и т.д.).

Работают над доменным состоянием позиции и рынка; side effects — в execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.market_state import MarketState
from domain.models.position import Position


class ExitRule(ABC):
    @abstractmethod
    def should_exit(self, position: Position, market: MarketState) -> bool:
        """True — инициировать выход согласно политике execution."""
