from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.position_state import (
    build_active_position_from_okx,
    check_exit_reason,
    should_use_market_exit,
)
from exchange.okx.models import OkxPosition
from strategy.random_baseline.config import RandomBaselineConfig
from strategy.random_baseline.service import RandomBaselineStrategy


def _strategy() -> RandomBaselineStrategy:
    return RandomBaselineStrategy(config=RandomBaselineConfig(timeout_sec=300))


def test_build_active_position_from_okx_long() -> None:
    strategy = _strategy()
    now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    okx_pos = OkxPosition(
        inst_id="BTC-USDT-SWAP",
        pos=Decimal("0.01"),
        avg_px=Decimal("61642.9"),
        pos_id="123",
        c_time_ms=int(now.timestamp() * 1000) - 3600_000,
    )
    active = build_active_position_from_okx(
        okx_pos=okx_pos,
        strategy_name="random_baseline_v1",
        tick_size=Decimal("0.1"),
        strategy=strategy,
        now=now,
    )
    assert active is not None
    assert active.side == "long"
    assert active.entry_price == Decimal("61642.9")
    assert active.timeout_at == active.entry_ts + timedelta(seconds=300)


def test_check_exit_reason_timeout_after_five_minutes() -> None:
    strategy = _strategy()
    now = datetime(2026, 6, 16, 12, 10, tzinfo=timezone.utc)
    entry_ts = now - timedelta(seconds=301)
    position = build_active_position_from_okx(
        okx_pos=OkxPosition(
            inst_id="BTC-USDT-SWAP",
            pos=Decimal("0.01"),
            avg_px=Decimal("61642.9"),
            c_time_ms=int(entry_ts.timestamp() * 1000),
        ),
        strategy_name="random_baseline_v1",
        tick_size=Decimal("0.1"),
        strategy=strategy,
        now=now,
    )
    assert position is not None
    assert check_exit_reason(position, Decimal("61650"), now) == "timeout"


def test_should_use_market_exit_after_grace() -> None:
    strategy = _strategy()
    now = datetime(2026, 6, 16, 12, 10, tzinfo=timezone.utc)
    entry_ts = now - timedelta(seconds=400)
    position = build_active_position_from_okx(
        okx_pos=OkxPosition(
            inst_id="BTC-USDT-SWAP",
            pos=Decimal("0.01"),
            avg_px=Decimal("61642.9"),
            c_time_ms=int(entry_ts.timestamp() * 1000),
        ),
        strategy_name="random_baseline_v1",
        tick_size=Decimal("0.1"),
        strategy=strategy,
        now=now,
    )
    assert position is not None
    config = RandomBaselineConfig(
        exit_market_fallback_enabled=True,
        exit_maker_max_attempts=10,
        exit_market_grace_sec=60,
    )
    assert should_use_market_exit(position=position, now=now, config=config) is True


def test_should_use_market_exit_after_attempts() -> None:
    strategy = _strategy()
    now = datetime(2026, 6, 16, 12, 1, tzinfo=timezone.utc)
    position = build_active_position_from_okx(
        okx_pos=OkxPosition(
            inst_id="BTC-USDT-SWAP",
            pos=Decimal("0.01"),
            avg_px=Decimal("61642.9"),
            c_time_ms=int(now.timestamp() * 1000),
        ),
        strategy_name="random_baseline_v1",
        tick_size=Decimal("0.1"),
        strategy=strategy,
        now=now,
    )
    assert position is not None
    position.exit_maker_attempts = 10
    config = RandomBaselineConfig(
        exit_market_fallback_enabled=True,
        exit_maker_max_attempts=10,
        exit_market_grace_sec=3600,
    )
    assert should_use_market_exit(position=position, now=now, config=config) is True


def test_is_exit_order_price_stale_long_sell() -> None:
    from app.position_state import is_exit_order_price_stale

    strategy = _strategy()
    now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    position = build_active_position_from_okx(
        okx_pos=OkxPosition(
            inst_id="BTC-USDT-SWAP",
            pos=Decimal("0.01"),
            avg_px=Decimal("61642.9"),
            c_time_ms=int(now.timestamp() * 1000),
        ),
        strategy_name="random_baseline_v1",
        tick_size=Decimal("0.1"),
        strategy=strategy,
        now=now,
    )
    assert position is not None
    assert is_exit_order_price_stale(
        position=position,
        order_side="sell",
        order_price=Decimal("61809.9"),
        best_bid=Decimal("61925.9"),
        best_ask=Decimal("61926.0"),
        stale_ticks=3,
        tick_size=Decimal("0.1"),
    )


def test_is_entry_order_price_stale_buy() -> None:
    from app.position_state import is_entry_order_price_stale

    assert is_entry_order_price_stale(
        order_side="buy",
        order_price=Decimal("62970.0"),
        best_bid=Decimal("63096.6"),
        best_ask=Decimal("63097.9"),
        stale_ticks=3,
        tick_size=Decimal("0.1"),
    )


def test_clamp_maker_price_to_limits() -> None:
    from app.position_state import clamp_maker_price_to_limits

    assert clamp_maker_price_to_limits(
        side="sell",
        price=Decimal("63174.0"),
        buy_lmt=Decimal("66370.2"),
        sell_lmt=Decimal("63209.7"),
        tick_size=Decimal("0.1"),
    ) == Decimal("63209.7")
