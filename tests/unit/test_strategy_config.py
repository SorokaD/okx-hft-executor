from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings, StrategyMode
from config.strategy_config import StrategiesConfig, clear_strategies_config_cache


@pytest.fixture
def strategies_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "strategies.yaml"
    path.write_text(
        """
default: random_baseline_v1

strategies:
  random_baseline_v1:
    enabled: true
    inst_id: BTC-USDT-SWAP
    execution:
      td_mode: isolated
      order_size: "0.02"
    decision_step_sec: 15
    take_profit_ticks: 100

  mean_reversion_v1:
    enabled: false
    inst_id: ETH-USDT-SWAP
""",
        encoding="utf-8",
    )
    clear_strategies_config_cache()
    return path


def test_load_strategies_config(strategies_yaml: Path) -> None:
    cfg = StrategiesConfig.from_yaml_file(strategies_yaml)
    dep = cfg.get_deployment("random_baseline_v1")
    assert dep.inst_id == "BTC-USDT-SWAP"
    assert dep.execution.order_size == "0.02"
    assert dep.params["decision_step_sec"] == 15
    assert dep.params["take_profit_ticks"] == 100

    runtime = cfg.runtime_configs()
    assert len(runtime) == 2
    enabled = [r for r in runtime if r.mode == StrategyMode.ENABLED]
    assert len(enabled) == 1
    assert enabled[0].strategy_name == "random_baseline_v1"


def test_settings_loads_runtime_from_yaml(strategies_yaml: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OKX_HFT_STRATEGIES_CONFIG", str(strategies_yaml))
    clear_strategies_config_cache()
    settings = Settings()
    configs = settings.get_strategy_runtime_configs()
    assert configs[0].strategy_name == "random_baseline_v1"
    assert configs[0].inst_id == "BTC-USDT-SWAP"
