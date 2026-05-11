from __future__ import annotations

import pytest

from strategy.registry import create_strategy


def test_create_strategy_random_baseline() -> None:
    strategy = create_strategy("random_baseline_v1")
    assert strategy.strategy_name == "random_baseline_v1"


def test_create_strategy_mean_reversion() -> None:
    strategy = create_strategy("mean_reversion_v1")
    assert strategy.strategy_name == "mean_reversion_v1"


def test_create_strategy_unknown_raises() -> None:
    with pytest.raises(ValueError):
        create_strategy("unknown_strategy")
