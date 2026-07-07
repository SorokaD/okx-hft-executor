"""In-memory position/order state and pure helpers for the baseline loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol

from exchange.okx.models import OkxPosition
from strategy.contracts import StrategyPlugin


class ExitFallbackConfig(Protocol):
    exit_market_fallback_enabled: bool
    exit_maker_max_attempts: int
    exit_market_grace_sec: int


@dataclass(slots=True)
class ActivePosition:
    position_id: str
    strategy_name: str
    side: Literal["long", "short"]
    entry_price: Decimal
    entry_ts: datetime
    size: Decimal
    tp_price: Decimal
    sl_price: Decimal
    timeout_at: datetime
    exit_maker_attempts: int = 0


@dataclass(slots=True)
class ActiveOrder:
    order_id: str
    client_id: str
    strategy_name: str
    side: Literal["buy", "sell"]
    purpose: Literal["entry", "exit"]
    created_at: datetime
    last_reprice_at: datetime
    reduce_only: bool
    size: str


def build_active_position(
    *,
    position_id: str,
    strategy_name: str,
    side: Literal["long", "short"],
    entry_price: Decimal,
    entry_ts: datetime,
    size: Decimal,
    tick_size: Decimal,
    strategy: StrategyPlugin,
    exit_maker_attempts: int = 0,
) -> ActivePosition:
    tp_delta = tick_size * Decimal(strategy.config.take_profit_ticks)
    sl_delta = tick_size * Decimal(strategy.config.stop_loss_ticks)
    if side == "long":
        tp = entry_price + tp_delta
        sl = entry_price - sl_delta
    else:
        tp = entry_price - tp_delta
        sl = entry_price + sl_delta
    return ActivePosition(
        position_id=position_id,
        strategy_name=strategy_name,
        side=side,
        entry_price=entry_price,
        entry_ts=entry_ts,
        size=size,
        tp_price=tp,
        sl_price=sl,
        timeout_at=entry_ts + timedelta(seconds=strategy.config.timeout_sec),
        exit_maker_attempts=exit_maker_attempts,
    )


def build_active_position_from_okx(
    *,
    okx_pos: OkxPosition,
    strategy_name: str,
    tick_size: Decimal,
    strategy: StrategyPlugin,
    now: datetime,
    position_id: str | None = None,
) -> ActivePosition | None:
    if okx_pos.avg_px is None or okx_pos.pos == 0:
        return None
    side: Literal["long", "short"] = "long" if okx_pos.pos > 0 else "short"
    entry_ts = (
        datetime.fromtimestamp(okx_pos.c_time_ms / 1000, tz=now.tzinfo)
        if okx_pos.c_time_ms is not None
        else now
    )
    stable_pid = position_id or (
        f"pos-ex-{okx_pos.pos_id}" if okx_pos.pos_id else f"pos-ex-{okx_pos.inst_id}"
    )
    return build_active_position(
        position_id=stable_pid,
        strategy_name=strategy_name,
        side=side,
        entry_price=okx_pos.avg_px,
        entry_ts=entry_ts,
        size=abs(okx_pos.pos),
        tick_size=tick_size,
        strategy=strategy,
    )


def check_exit_reason(position: ActivePosition, price: Decimal, now: datetime) -> str | None:
    if now >= position.timeout_at:
        return "timeout"
    if position.side == "long":
        if price >= position.tp_price:
            return "tp"
        if price <= position.sl_price:
            return "sl"
        return None
    if price <= position.tp_price:
        return "tp"
    if price >= position.sl_price:
        return "sl"
    return None


def should_use_market_exit(
    *,
    position: ActivePosition,
    now: datetime,
    config: ExitFallbackConfig,
) -> bool:
    if not config.exit_market_fallback_enabled:
        return False
    if position.exit_maker_attempts >= config.exit_maker_max_attempts:
        return True
    grace_deadline = position.timeout_at + timedelta(seconds=config.exit_market_grace_sec)
    return now >= grace_deadline


def calc_gross_pnl(position: ActivePosition, exit_price: Decimal) -> Decimal:
    if position.side == "long":
        return (exit_price - position.entry_price) * position.size
    return (position.entry_price - exit_price) * position.size


def maker_price_for_side(
    *,
    side: Literal["buy", "sell"],
    best_bid: Decimal,
    best_ask: Decimal,
    tick_size: Decimal,
) -> Decimal:
    if side == "buy":
        return best_bid.quantize(tick_size)
    return best_ask.quantize(tick_size)


def clamp_maker_price_to_limits(
    *,
    side: Literal["buy", "sell"],
    price: Decimal,
    buy_lmt: Decimal,
    sell_lmt: Decimal,
    tick_size: Decimal,
) -> Decimal:
    """Зажимает post-only цену в динамический price band OKX."""
    if side == "buy":
        clamped = min(price, buy_lmt)
    else:
        clamped = max(price, sell_lmt)
    return clamped.quantize(tick_size)


def is_entry_order_price_stale(
    *,
    order_side: Literal["buy", "sell"],
    order_price: Decimal,
    best_bid: Decimal,
    best_ask: Decimal,
    stale_ticks: int,
    tick_size: Decimal,
) -> bool:
    """True, если entry-maker завис далеко от touch и его нужно переставить немедленно."""
    if stale_ticks <= 0:
        return False
    gap = tick_size * Decimal(stale_ticks)
    if order_side == "buy":
        return best_bid - order_price > gap
    return order_price - best_ask > gap


def expected_exit_side(position: ActivePosition) -> Literal["buy", "sell"]:
    return "sell" if position.side == "long" else "buy"


def is_probable_exit_order(*, position: ActivePosition, order_side: str) -> bool:
    return order_side == expected_exit_side(position)


def is_exit_order_price_stale(
    *,
    position: ActivePosition,
    order_side: str,
    order_price: Decimal,
    best_bid: Decimal,
    best_ask: Decimal,
    stale_ticks: int,
    tick_size: Decimal,
) -> bool:
    """True, если exit-maker завис далеко от touch и его нужно переставить немедленно."""
    if stale_ticks <= 0:
        return False
    gap = tick_size * Decimal(stale_ticks)
    if position.side == "long" and order_side == "sell":
        return best_ask - order_price > gap
    if position.side == "short" and order_side == "buy":
        return order_price - best_bid > gap
    return False
