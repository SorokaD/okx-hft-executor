"""Агрегирование позиции по потоку исполнений и обновлениям с биржи."""

from __future__ import annotations

from domain.models.position import Position
from domain.value_objects.instrument_id import InstrumentId


class PositionManager:
    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}

    def snapshot(self, instrument: InstrumentId) -> Position | None:
        return self._positions.get(instrument.value)
