from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from persistence.executor_store import ExecutorStore
from persistence.sqlite_store import TradeResult


@pytest.fixture
def settings(tmp_path, monkeypatch) -> Settings:
    monkeypatch.setenv("OKX_SQLITE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("OKX_HFT_POSTGRES_ENABLED", "0")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_LINK", raising=False)
    return Settings()


def test_executor_store_sqlite_only(settings: Settings) -> None:
    store = ExecutorStore.create(
        settings,
        strategy_name="random_baseline_v1",
        inst_id="BTC-USDT-SWAP",
    )
    store.set_strategy_params(take_profit_ticks=10, stop_loss_ticks=5, timeout_sec=60)
    store.save_signal(
        signal_id="sig-1",
        strategy_name="random_baseline_v1",
        side="long",
        created_at="2026-01-01T00:00:00+00:00",
    )
    store.save_order(
        local_order_id="sig-1",
        strategy_name="random_baseline_v1",
        exchange_order_id="ex-1",
        side="buy",
        order_type="post_only",
        price=100.0,
        size=0.01,
        status="submitted",
        created_at="2026-01-01T00:00:01+00:00",
        signal_id="sig-1",
    )
    summary = store.get_counts_summary()
    assert summary["signals"] == 1
    assert summary["orders"] == 1
    store.close()


def test_executor_store_enqueues_postgres_when_configured(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OKX_SQLITE_PATH", str(tmp_path / "pg.sqlite3"))
    monkeypatch.setenv("OKX_HFT_POSTGRES_ENABLED", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch.delenv("POSTGRES_LINK", raising=False)
    settings = Settings()
    journal = MagicMock()
    journal.start_run.return_value = 42
    journal.run_id = 42

    with patch("persistence.executor_store.PostgresJournal", return_value=journal):
        store = ExecutorStore.create(
            settings,
            strategy_name="random_baseline_v1",
            inst_id="BTC-USDT-SWAP",
        )

    import asyncio

    async def _run() -> None:
        await store.open()
        store.save_signal(
            signal_id="sig-2",
            strategy_name="random_baseline_v1",
            side="short",
            created_at="2026-01-01T00:00:00+00:00",
        )
        store.save_position_open(
            position_id="pos-1",
            strategy_name="random_baseline_v1",
            side="short",
            entry_price=100.0,
            entry_ts="2026-01-01T00:00:05+00:00",
            size=0.01,
        )
        store.save_position_close(
            position_id="pos-1",
            exit_price=99.0,
            exit_ts="2026-01-01T00:01:00+00:00",
            exit_reason="tp",
        )
        store.save_trade_result(
            TradeResult(
                position_id="pos-1",
                strategy_name="random_baseline_v1",
                gross_pnl=0.01,
                fees=0.0,
                net_pnl=0.01,
                holding_seconds=55.0,
            )
        )
        await store.aclose()

    asyncio.run(_run())
    journal.enqueue_signal.assert_called_once()
    journal.enqueue_position_open.assert_called_once()
    journal.enqueue_position_close.assert_called_once()
    journal.enqueue_trade_result.assert_called_once()
