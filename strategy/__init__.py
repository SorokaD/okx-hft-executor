"""Стратегия: сигналы, правила входа/выхода, фильтры режима."""

from strategy.contracts import StrategyPlugin, StrategySignal
from strategy.registry import STRATEGY_REGISTRY, create_strategy
from strategy.random_baseline import RandomBaselineStrategy

__all__ = [
    "RandomBaselineStrategy",
    "STRATEGY_REGISTRY",
    "StrategyPlugin",
    "StrategySignal",
    "create_strategy",
]
