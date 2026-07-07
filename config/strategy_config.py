"""Загрузка конфигурации стратегий из YAML (не из .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from config.settings import StrategyMode, StrategyRuntimeConfig, _PROJECT_ROOT

_RESERVED_KEYS = frozenset({"enabled", "inst_id", "execution"})


class StrategyExecutionConfig(BaseModel):
    """Параметры исполнения ордеров для одной стратегии."""

    td_mode: str = "isolated"
    ord_type: str = "post_only"
    order_size: str = "0.01"
    maker_reprice_sec: int = 3
    maker_max_wait_sec: int = 20


class StrategyDeploymentConfig(BaseModel):
    """Развёртывание одной стратегии: инструмент, режим, execution + params."""

    strategy_name: str
    enabled: bool = True
    inst_id: str
    execution: StrategyExecutionConfig = Field(default_factory=StrategyExecutionConfig)
    params: dict[str, Any] = Field(default_factory=dict)

    @property
    def mode(self) -> StrategyMode:
        return StrategyMode.ENABLED if self.enabled else StrategyMode.DISABLED

    def to_runtime_config(self) -> StrategyRuntimeConfig:
        return StrategyRuntimeConfig(
            strategy_name=self.strategy_name,
            inst_id=self.inst_id,
            mode=self.mode,
        )


class StrategiesConfig(BaseModel):
    """Файл config/strategies.yaml."""

    default_strategy: str | None = None
    deployments: dict[str, StrategyDeploymentConfig] = Field(default_factory=dict)

    @classmethod
    def from_yaml_file(cls, path: Path) -> StrategiesConfig:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"strategies config must be a mapping, got {type(raw).__name__}")

        default_strategy = raw.get("default")
        strategies_raw = raw.get("strategies") or {}
        if not isinstance(strategies_raw, dict):
            raise ValueError("strategies key must be a mapping")

        deployments: dict[str, StrategyDeploymentConfig] = {}
        for name, block in strategies_raw.items():
            if not isinstance(block, dict):
                raise ValueError(f"strategy '{name}' must be a mapping")
            data = dict(block)
            execution_raw = data.pop("execution", None) or {}
            if not isinstance(execution_raw, dict):
                raise ValueError(f"strategy '{name}'.execution must be a mapping")
            enabled = bool(data.pop("enabled", True))
            inst_id = data.pop("inst_id", None)
            if not inst_id:
                raise ValueError(f"strategy '{name}' requires inst_id")
            params = {k: v for k, v in data.items() if k not in _RESERVED_KEYS}
            deployments[name] = StrategyDeploymentConfig(
                strategy_name=name,
                enabled=enabled,
                inst_id=str(inst_id),
                execution=StrategyExecutionConfig(**execution_raw),
                params=params,
            )

        return cls(default_strategy=default_strategy, deployments=deployments)

    def get_deployment(self, strategy_name: str) -> StrategyDeploymentConfig:
        dep = self.deployments.get(strategy_name)
        if dep is None:
            known = ", ".join(sorted(self.deployments))
            raise KeyError(
                f"Unknown strategy deployment '{strategy_name}'. Known: {known or '(none)'}"
            )
        return dep

    def get_default_deployment(self) -> StrategyDeploymentConfig:
        if self.default_strategy:
            return self.get_deployment(self.default_strategy)
        for dep in self.deployments.values():
            if dep.enabled:
                return dep
        raise ValueError("No enabled strategy in strategies config")

    def runtime_configs(self) -> list[StrategyRuntimeConfig]:
        return [d.to_runtime_config() for d in self.deployments.values()]


def resolve_strategies_path(settings: object) -> Path:
    """Абсолютный путь к YAML из Settings.strategies_config_path."""
    rel = getattr(settings, "strategies_config_path", "config/strategies.yaml")
    path = Path(str(rel))
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    return path


@lru_cache
def load_strategies_config_cached(resolved_path: str) -> StrategiesConfig:
    return StrategiesConfig.from_yaml_file(Path(resolved_path))


def get_strategies_config(settings: object) -> StrategiesConfig:
    path = resolve_strategies_path(settings)
    if not path.exists():
        raise FileNotFoundError(f"Strategies config not found: {path}")
    return load_strategies_config_cached(str(path.resolve()))


def clear_strategies_config_cache() -> None:
    load_strategies_config_cached.cache_clear()
