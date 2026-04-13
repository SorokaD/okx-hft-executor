"""Атрибуция slippage и сравнение с benchmark (mid, arrival price, vwap)."""

from __future__ import annotations

from decimal import Decimal

from domain.models.fill import Fill


class ExecutionQuality:
    def slippage_vs_mid(self, fill: Fill, mid_at_order: Decimal) -> Decimal:
        _ = fill
        _ = mid_at_order
        return Decimal("0")
