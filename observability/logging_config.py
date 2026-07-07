"""Настройка логирования процесса (каркас расширения до structlog/json)."""

from __future__ import annotations

import logging

from config.settings import Settings


def configure_logging_placeholder(settings: Settings) -> None:
    """Точка расширения: форматтеры, корреляционные поля, уровень из настроек."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.getLogger("okx_hft_executor").setLevel(level)
