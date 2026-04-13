"""
Фильтры рыночного режима: спред, волатильность, ликвидность, сессии.

Используются до агрессивного исполнения; могут дублировать часть runtime risk.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.market_state import MarketState


class RegimeFilter(ABC):
    @abstractmethod
    def allowed(self, market: MarketState) -> bool:
        """False — не торговать в текущем режиме."""
