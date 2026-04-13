"""Интерфейсы репозиториев для доменных сущностей (каркас)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.order import Order


class OrderRepository(ABC):
    @abstractmethod
    async def save(self, order: Order) -> None:
        ...

    @abstractmethod
    async def get_by_client_id(self, client_order_id: str) -> Order | None:
        ...
