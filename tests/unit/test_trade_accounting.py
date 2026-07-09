"""Tests for gross/net PnL and fee estimation."""
from __future__ import annotations

from decimal import Decimal

from accounting.fee_engine import estimate_fees, fees_from_okx_fills
from accounting.pnl_engine import calc_gross_pnl, calc_net_pnl
from exchange.okx.models import OkxFill
from execution.trade_finalize import build_trade_result, normalize_exit_reason
from execution.trade_lifecycle import TradeLifecycleTracker
from app.position_state import ActivePosition
from datetime import datetime, timezone


def test_gross_pnl_long() -> None:
    gross = calc_gross_pnl(
        side="long",
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        size=Decimal("2"),
    )
    assert gross == Decimal("20")


def test_gross_pnl_short() -> None:
    gross = calc_gross_pnl(
        side="short",
        entry_price=Decimal("100"),
        exit_price=Decimal("90"),
        size=Decimal("1"),
    )
    assert gross == Decimal("10")


def test_net_pnl_after_fees() -> None:
    fees = estimate_fees(
        entry_px=Decimal("100"),
        exit_px=Decimal("110"),
        size=Decimal("1"),
        entry_order_type="post_only",
        exit_order_type="post_only",
        fee_rate_maker=Decimal("0.0002"),
        fee_rate_taker=Decimal("0.0005"),
    )
    gross = Decimal("10")
    net = calc_net_pnl(gross_pnl=gross, total_fee=fees.total_fee)
    assert net < gross
    assert fees.entry_fee > 0
    assert fees.exit_fee > 0
    assert fees.fee_source == "estimated_config"


def test_fees_from_okx_fills() -> None:
    entry = OkxFill(
        fill_id="f1",
        ord_id="o1",
        cl_ord_id="sig-1",
        inst_id="BTC-USDT-SWAP",
        side="buy",
        fill_px=Decimal("100"),
        fill_sz=Decimal("1"),
        fee=Decimal("-0.02"),
        fee_ccy="USDT",
        exec_type="M",
    )
    exit_fill = OkxFill(
        fill_id="f2",
        ord_id="o2",
        cl_ord_id="exit-1",
        inst_id="BTC-USDT-SWAP",
        side="sell",
        fill_px=Decimal("101"),
        fill_sz=Decimal("1"),
        fee=Decimal("-0.0202"),
        fee_ccy="USDT",
        exec_type="T",
    )
    breakdown = fees_from_okx_fills(entry_fills=[entry], exit_fills=[exit_fill])
    assert breakdown.fee_source == "okx_fill"
    assert breakdown.entry_liquidity == "maker"
    assert breakdown.exit_liquidity == "taker"
    assert breakdown.total_fee == Decimal("0.0402")


def test_trade_result_market_fallback_metrics() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pos = ActivePosition(
        position_id="pos-1",
        strategy_name="random_baseline_v1",
        side="long",
        entry_price=Decimal("100"),
        entry_ts=now,
        size=Decimal("1"),
        tp_price=Decimal("110"),
        sl_price=Decimal("90"),
        timeout_at=now,
    )
    lc = TradeLifecycleTracker()
    lc.begin("sig-abc", tick_size=Decimal("0.1"))
    lc.on_exit_trigger("timeout")
    lc.on_exit_submit(99.0, order_type="market", market_fallback=True, ts=now)
    lc.on_exit_fill(99.0, exchange_ord_id="ex-2", cl_ord_id="exit-mkt-1", order_type="market", ts=now, close_source="executor_market_fallback")
    fees = estimate_fees(
        entry_px=Decimal("100"),
        exit_px=Decimal("99"),
        size=Decimal("1"),
        entry_order_type="post_only",
        exit_order_type="market",
        fee_rate_maker=Decimal("0.0002"),
        fee_rate_taker=Decimal("0.0005"),
    )
    trade = build_trade_result(
        position=pos,
        lifecycle=lc,
        exit_price=Decimal("99"),
        closed_at=now,
        inst_id="BTC-USDT-SWAP",
        fees=fees,
        exit_reason="timeout",
        close_source="executor_market_fallback",
    )
    assert trade.exit_reason == "timeout"
    assert trade.close_source == "executor_market_fallback"
    assert trade.signal_id == "sig-abc"
    metrics = trade.execution_metrics or {}
    assert metrics.get("exit_market_fallback_used") is True
    assert metrics.get("timeout_triggered") is True


def test_signal_id_preserved_through_reprices() -> None:
    lc = TradeLifecycleTracker()
    lc.begin("rb-original-signal", tick_size=Decimal("0.1"))
    lc.on_entry_submit(100.0, touch_px=100.0, ts=datetime.now(timezone.utc))
    lc.on_reprice("entry", 100.1, datetime.now(timezone.utc))
    lc.on_reprice("entry", 100.2, datetime.now(timezone.utc))
    assert lc.entry_signal_id == "rb-original-signal"
    assert lc.entry_reprice_count == 2
    assert lc.entry_order_count == 3


def test_normalize_exit_reason() -> None:
    assert normalize_exit_reason("sync_lost") == "reconcile"
    assert normalize_exit_reason("tp") == "tp"
    assert normalize_exit_reason("maker_exit") == "unknown"
