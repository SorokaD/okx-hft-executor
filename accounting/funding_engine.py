"""Учёт funding payments по perpetual (каркас; данные из отдельного потока)."""

from __future__ import annotations

from decimal import Decimal


class FundingEngine:
    def apply_funding(self, notional: Decimal, rate: Decimal) -> Decimal:
        _ = notional
        _ = rate
        return Decimal("0")
