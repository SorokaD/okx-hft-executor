"""
Приём торговых сигналов из внешних источников (очередь, файл, control plane).

Реализации парсят payload и возвращают `domain.models.Signal` или отказ.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.signal import Signal


class SignalIntake(ABC):
    """Порт приёма сигналов; в live может быть message bus, в replay — reader фикстур."""

    @abstractmethod
    async def next_signal(self) -> Signal | None:
        """Возвращает следующий сигнал или None, если источник пуст/закрыт."""
