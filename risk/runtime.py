"""Runtime мониторинг: просадка, качество данных, частота сбоев API (каркас)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RuntimeRiskMonitor(ABC):
    @abstractmethod
    def healthy(self) -> bool:
        """False — инициировать осторожный режим или kill switch по политике."""
