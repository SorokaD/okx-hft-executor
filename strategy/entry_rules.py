"""
Правила входа в позицию на основе сигнала и рыночного контекста.

Не выполняют I/O; возвращают решение «разрешить / запретить / изменить параметры».
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.market_state import MarketState
from domain.models.signal import Signal


class EntryRule(ABC):
    """Одиночное правило; pipeline собирается в orchestration."""

    @abstractmethod
    def evaluate(self, signal: Signal, market: MarketState) -> bool:
        """True — правило пройдено."""
