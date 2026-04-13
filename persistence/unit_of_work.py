"""
Unit of Work: транзакционная граница для согласованной записи событий.

Реализации появятся при выборе конкретной СУБД или event store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    @abstractmethod
    async def commit(self) -> None:
        """Фиксация изменений."""

    @abstractmethod
    async def rollback(self) -> None:
        """Откат при ошибке."""
