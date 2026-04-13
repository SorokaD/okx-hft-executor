"""Pre-trade проверки до формирования заявки (каркас)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.order import Order


class PreTradeCheck(ABC):
    @abstractmethod
    def ok(self, order: Order) -> bool:
        """False — ордер не должен отправляться на биржу."""
