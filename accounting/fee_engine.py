"""Расчёт и распределение торговых комиссий (каркас)."""

from __future__ import annotations

from decimal import Decimal

from domain.models.fill import Fill


class FeeEngine:
    def total_fees(self, fills: list[Fill]) -> Decimal:
        _ = fills
        return Decimal("0")
