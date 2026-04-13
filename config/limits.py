"""
Числовые лимиты и пороги по умолчанию для risk / execution.

Значения могут быть переопределены из Settings или внешнего конфига;
здесь — безопасные заглушки и типизированная структура для расширения.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DefaultRiskLimits:
    """Каркас лимитов pre-trade; реальная логика в пакете `risk`."""

    max_orders_per_minute: int = 60
    max_open_orders: int = 20
    max_notional_usd: float = 100_000.0
