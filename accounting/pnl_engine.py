"""Движок PnL: агрегация по потоку исполнений (каркас)."""

from __future__ import annotations

from decimal import Decimal

from domain.models.fill import Fill


class PnlEngine:
    def realized_from_fills(self, fills: list[Fill]) -> Decimal:
        """Заглушка; реальная логика зависит от режима позиции (net/hedge)."""
        _ = fills
        return Decimal("0")
