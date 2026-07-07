"""
Composition root: создание реализаций портов и сервисов по настройкам.

Содержит минимальный каркас `ExecutorContext`; по мере роста проекта сюда
добавляются фабрики для live/paper/replay без разрастания `main.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import RuntimeMode, Settings
from config.strategy_config import StrategyDeploymentConfig
from exchange.protocols import ExchangeClient
from observability.logging_config import configure_logging_placeholder
from services.clock import SystemClock


@dataclass(frozen=True, slots=True)
class ExecutorContext:
    """Собранные зависимости процесса исполнителя (будет расширяться)."""

    settings: Settings
    clock: SystemClock
    exchange: ExchangeClient
    deployment: StrategyDeploymentConfig | None = None


def build_executor_context(
    settings: Settings,
    *,
    deployment: StrategyDeploymentConfig | None = None,
) -> ExecutorContext:
    """Собирает контекст исполнения baseline MVP."""
    configure_logging_placeholder(settings)
    # Импорт внутри функции избегает циклов при росте графа.
    use_stub = (
        settings.runtime_mode == RuntimeMode.REPLAY
        or settings.safe_mode
        or (settings.runtime_mode == RuntimeMode.PAPER and not settings.enable_real_okx_in_paper)
    )
    if use_stub:
        from exchange.okx.stub_client import OkxStubExchangeClient

        exchange: ExchangeClient = OkxStubExchangeClient(
            settings=settings,
            deployment=deployment,
        )
    else:
        from exchange.okx.rest_client import OkxRestClient

        exchange = OkxRestClient(settings=settings, deployment=deployment)

    clock = SystemClock()
    return ExecutorContext(
        settings=settings,
        clock=clock,
        exchange=exchange,
        deployment=deployment,
    )
