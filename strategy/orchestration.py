"""
Оркестрация правил стратегии: порядок evaluation, агрегация решений.

Не знает о бирже; вызывается из run-loop приложения перед risk/execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.models.market_state import MarketState
from domain.models.signal import Signal
from strategy.entry_rules import EntryRule
from strategy.regime_filters import RegimeFilter


@dataclass(slots=True)
class StrategyPipeline:
    """Каркас цепочки фильтр → правила входа (расширяется списками правил)."""

    regime: RegimeFilter
    entry: EntryRule

    def accept_signal(self, signal: Signal, market: MarketState) -> bool:
        return self.regime.allowed(market) and self.entry.evaluate(signal, market)
