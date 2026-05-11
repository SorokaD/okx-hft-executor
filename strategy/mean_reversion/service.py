from __future__ import annotations

from datetime import datetime

from strategy.random_baseline.service import RandomBaselineStrategy


class MeanReversionPrototypeStrategy(RandomBaselineStrategy):
    """
    Каркас для следующей стратегии.

    Временно наследует baseline-поведение для совместимости runtime,
    но выделен в отдельный модуль и имя, чтобы без правок manager/control
    можно было развивать свою логику mean reversion.
    """

    def __init__(self, strategy_name: str = "mean_reversion_v1") -> None:
        super().__init__(strategy_name=strategy_name)

    def on_position_closed(self, now: datetime) -> None:
        super().on_position_closed(now)
