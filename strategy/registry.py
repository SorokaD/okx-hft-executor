from __future__ import annotations

from typing import Any, Callable

from strategy.contracts import StrategyPlugin
from strategy.mean_reversion.service import MeanReversionPrototypeStrategy
from strategy.random_baseline.config import config_from_params
from strategy.random_baseline.service import RandomBaselineStrategy

StrategyFactory = Callable[[str, dict[str, Any]], StrategyPlugin]


def _build_random_baseline(strategy_name: str, params: dict[str, Any]) -> StrategyPlugin:
    return RandomBaselineStrategy(
        strategy_name=strategy_name,
        config=config_from_params(params),
    )


def _build_mean_reversion_prototype(strategy_name: str, params: dict[str, Any]) -> StrategyPlugin:
    _ = params
    return MeanReversionPrototypeStrategy(strategy_name=strategy_name)


STRATEGY_REGISTRY: dict[str, StrategyFactory] = {
    "random_baseline_v1": _build_random_baseline,
    "mean_reversion_v1": _build_mean_reversion_prototype,
}


def create_strategy(
    strategy_name: str,
    params: dict[str, Any] | None = None,
) -> StrategyPlugin:
    factory = STRATEGY_REGISTRY.get(strategy_name)
    if factory is None:
        raise ValueError(
            f"Unknown strategy_name='{strategy_name}'. "
            f"Known values: {', '.join(sorted(STRATEGY_REGISTRY))}"
        )
    return factory(strategy_name, params or {})
