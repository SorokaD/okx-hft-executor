"""Сборка контекста исполнителя без сети."""

from __future__ import annotations

from app.bootstrap import build_executor_context
from config.settings import Settings, RuntimeMode


def test_build_executor_context() -> None:
    settings = Settings(
        env="test",
        runtime_mode=RuntimeMode.REPLAY,
        log_level="INFO",
        okx_flag_demo=True,
    )
    ctx = build_executor_context(settings)
    assert ctx.settings is settings
    assert ctx.exchange is not None
