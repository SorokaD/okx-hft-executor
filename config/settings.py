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
    runtime_mode: RuntimeMode = Field(
        default=RuntimeMode.PAPER,
        validation_alias="OKX_HFT_RUNTIME_MODE",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="OKX_HFT_LOG_LEVEL",
    )

    okx_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OKX_API_KEY",
    )
    okx_api_secret: SecretStr | None = Field(
        default=None,
        validation_alias="OKX_API_SECRET",
    )
    okx_api_passphrase: SecretStr | None = Field(
        default=None,
        validation_alias="OKX_API_PASSPHRASE",
    )
    okx_flag_demo: bool = Field(default=True, validation_alias="OKX_FLAG_DEMO")
    okx_base_url: str = Field(
        default="https://www.okx.com",
        validation_alias="OKX_BASE_URL",
    )
    okx_inst_id: str = Field(default="BTC-USDT-SWAP", validation_alias="OKX_INST_ID")
    okx_td_mode: str = Field(default="cross", validation_alias="OKX_TD_MODE")
    okx_ord_type: str = Field(default="post_only", validation_alias="OKX_ORD_TYPE")
    okx_order_size: str = Field(default="1", validation_alias="OKX_ORDER_SIZE")
    okx_maker_reprice_sec: int = Field(
        default=3,
        validation_alias="OKX_MAKER_REPRICE_SEC",
    )
    okx_maker_max_wait_sec: int = Field(
        default=20,
        validation_alias="OKX_MAKER_MAX_WAIT_SEC",
    )

    control_host: str = Field(
        default="127.0.0.1",
        validation_alias="OKX_HFT_CONTROL_HOST",
    )
    control_port: int = Field(default=8080, validation_alias="OKX_HFT_CONTROL_PORT")

    metrics_enabled: bool = Field(
        default=False,
        validation_alias="OKX_HFT_METRICS_ENABLED",
    )
    sqlite_path: str = Field(
        default="data/baseline_mvp.sqlite3",
        validation_alias="OKX_SQLITE_PATH",
    )
    loop_sleep_sec: float = Field(default=1.0, validation_alias="OKX_LOOP_SLEEP_SEC")
    safe_mode: bool = Field(default=False, validation_alias="OKX_HFT_SAFE_MODE")
    enable_real_okx_in_paper: bool = Field(
        default=False,
        validation_alias="OKX_ENABLE_REAL_OKX_IN_PAPER",
    )


@lru_cache
def get_settings() -> Settings:
    """Кэшированный singleton настроек процесса."""
    return Settings()
