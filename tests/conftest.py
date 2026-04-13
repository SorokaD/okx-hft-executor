"""Общие фикстуры pytest (каркас)."""

from __future__ import annotations

import pytest

from config.settings import Settings, RuntimeMode


@pytest.fixture
def test_settings() -> Settings:
    """Изолированные настройки без чтения реальных секретов из окружения."""
    return Settings(
        env="test",
        runtime_mode=RuntimeMode.REPLAY,
        log_level="DEBUG",
        okx_flag_demo=True,
    )
