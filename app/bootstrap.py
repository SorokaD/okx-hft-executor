"""
Composition root: создание реализаций портов и сервисов по настройкам.

Содержит минимальный каркас `ExecutorContext`; по мере роста проекта сюда
добавляются фабрики для live/paper/replay без разрастания `main.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import Settings
from exchange.protocols import ExchangeClient
from observability.logging_config import configure_logging_placeholder
from services.clock import SystemClock


@dataclass(frozen=True, slots=True)
class ExecutorContext:
    """Собранные зависимости процесса исполнителя (будет расширяться)."""

    settings: Settings
    clock: SystemClock
    exchange: ExchangeClient


def build_executor_context(settings: Settings) -> ExecutorContext:
    """Собирает контекст исполнения. Сейчас используются заглушки exchange."""
    configure_logging_placeholder(settings)
    # Импорт внутри функции избегает циклов при росте графа.
    from exchange.okx.stub_client import OkxStubExchangeClient

    clock = SystemClock()
    exchange: ExchangeClient = OkxStubExchangeClient(settings=settings)
    return ExecutorContext(settings=settings, clock=clock, exchange=exchange)
