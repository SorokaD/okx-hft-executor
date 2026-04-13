from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RandomBaselineConfig:
    """Параметры baseline v1 для простого случайного входа."""

    decision_step_sec: int = 30
    cooldown_sec: int = 20
    take_profit_ticks: int = 700
    stop_loss_ticks: int = 350
    timeout_sec: int = 300
