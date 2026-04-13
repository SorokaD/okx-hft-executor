"""
Типизированные настройки из окружения (pydantic-settings).

Имена переменных согласованы с `.env.example`; секреты не логируются.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(str, Enum):
    """Режим работы процесса (влияет на выбор адаптеров в bootstrap)."""

    LIVE = "live"
    PAPER = "paper"
    REPLAY = "replay"


class Settings(BaseSettings):
    """Глобальные настройки исполнителя."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: str = Field(default="development", validation_alias="OKX_HFT_ENV")
    runtime_mode: RuntimeMode = Field(default=RuntimeMode.PAPER, validation_alias="OKX_HFT_RUNTIME_MODE")
    log_level: str = Field(default="INFO", validation_alias="OKX_HFT_LOG_LEVEL")

    okx_api_key: SecretStr | None = Field(default=None, validation_alias="OKX_API_KEY")
    okx_api_secret: SecretStr | None = Field(default=None, validation_alias="OKX_API_SECRET")
    okx_api_passphrase: SecretStr | None = Field(default=None, validation_alias="OKX_API_PASSPHRASE")
    okx_flag_demo: bool = Field(default=True, validation_alias="OKX_FLAG_DEMO")

    control_host: str = Field(default="127.0.0.1", validation_alias="OKX_HFT_CONTROL_HOST")
    control_port: int = Field(default=8080, validation_alias="OKX_HFT_CONTROL_PORT")

    metrics_enabled: bool = Field(default=False, validation_alias="OKX_HFT_METRICS_ENABLED")


@lru_cache
def get_settings() -> Settings:
    """Кэшированный singleton настроек процесса."""
    return Settings()
