"""
Торговые guard-ы: фасад над pre-trade, runtime и kill switch.

Используется execution engine перед отправкой ордеров.
"""

from __future__ import annotations

from domain.models.order import Order
from risk.kill_switch import KillSwitch


class TradingGuards:
    def __init__(self, kill_switch: KillSwitch) -> None:
        self._kill_switch = kill_switch

    def allow_new_order(self, order: Order) -> bool:
        """Минимальная проверка; расширяется списком PreTradeCheck."""
        _ = order
        return not self._kill_switch.armed
