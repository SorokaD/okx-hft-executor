"""Количество базового актива с явной точностью (value object)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Quantity:
    amount: Decimal
