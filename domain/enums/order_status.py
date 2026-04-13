"""Укрупнённые статусы заявки, независимые от строк OKX (нормализация в exchange)."""

from __future__ import annotations

from enum import Enum


class OrderStatus(str, Enum):
    NEW = "new"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"
