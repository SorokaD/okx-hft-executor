"""Движок PnL: gross и net для long/short round-trip."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal


def calc_gross_pnl(
    *,
    side: Literal["long", "short"],
    entry_price: Decimal,
    exit_price: Decimal,
    size: Decimal,
) -> Decimal:
    if side == "long":
        return (exit_price - entry_price) * size
    return (entry_price - exit_price) * size


def calc_net_pnl(*, gross_pnl: Decimal, total_fee: Decimal) -> Decimal:
    return gross_pnl - total_fee
