from __future__ import annotations

from typing import Callable

from strategy.contracts import StrategyPlugin
from strategy.random_baseline.service import RandomBaselineStrategy
from strategy.mean_reversion.service import MeanReversionPrototypeStrategy

StrategyFactory = Callable[[str], StrategyPlugin]


def _build_random_baseline(strategy_name: str) -> StrategyPlugin:
    return RandomBaselineStrategy(strategy_name=strategy_name)


def _build_mean_reversion_prototype(strategy_name: str) -> StrategyPlugin:
    return MeanReversionPrototypeStrategy(strategy_name=strategy_name)


STRATEGY_REGISTRY: dict[str, StrategyFactory] = {
    "random_baseline_v1": _build_random_baseline,
    "mean_reversion_v1": _build_mean_reversion_prototype,
}


def create_strategy(strategy_name: str) -> StrategyPlugin:
    factory = STRATEGY_REGISTRY.get(strategy_name)
    if factory is None:
        raise ValueError(
            f"Unknown strategy_name='{strategy_name}'. "
            f"Known values: {', '.join(sorted(STRATEGY_REGISTRY))}"
        )
    return factory(strategy_name)
