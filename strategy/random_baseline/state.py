from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RandomBaselineState:
    """Минимальное состояние стратегии между decision step-ами."""

    last_decision_ts: datetime | None = None
    cooldown_until: datetime | None = None
