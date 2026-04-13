"""Идентификатор инструмента в домене (нормализованный символ, не сырой instId OKX)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstrumentId:
    """Например unified symbol после маппинга из ответа биржи."""

    value: str
