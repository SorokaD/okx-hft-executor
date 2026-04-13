"""Простой рабочий baseline loop: strategy -> order -> position -> exit."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from app.bootstrap import ExecutorContext
from domain.value_objects.instrument_id import InstrumentId
from persistence.sqlite_store import SqliteMvpStore, TradeResult
from services.id_generation import new_client_order_id
from strategy.random_baseline import RandomBaselineStrategy


@dataclass(slots=True)
class ActivePosition:
    position_id: str
    side: Literal["long", "short"]
    entry_price: Decimal
    entry_ts: datetime
    size: Decimal
    tp_price: Decimal
    sl_price: Decimal
    timeout_at: datetime


async def run_baseline_loop(
    ctx: ExecutorContext,
    *,
    run_seconds: int | None = None,
    max_loops: int | None = None,
) -> dict[str, int]:
    """Цикл baseline MVP, опционально с лимитами smoke-run."""
    return await run_baseline_loop_with_limits(
        ctx,
        run_seconds=run_seconds,
        max_loops=max_loops,
    )


async def run_baseline_loop_with_limits(
    ctx: ExecutorContext,
    *,
    run_seconds: int | None = None,
    max_loops: int | None = None,
) -> dict[str, int]:
    """Цикл baseline MVP с optional авто-остановкой для smoke-run."""
    log = logging.getLogger(__name__)
    settings = ctx.settings
    strategy = RandomBaselineStrategy()
    store = SqliteMvpStore(settings.sqlite_path)
    inst_id = settings.okx_inst_id
    started_at = ctx.clock.now_utc()
    loop_count = 0
    try:
        tick_size = await ctx.exchange.get_tick_size(inst_id=inst_id)
    except Exception as exc:  # noqa: BLE001
        if inst_id == "BTC-USDT-SWAP":
            tick_size = Decimal("0.1")
            log.warning(
                "Failed to fetch tick size from OKX, fallback tick_size=0.1 for BTC-USDT-SWAP: %s",
                exc,
            )
        else:
            raise
    log.info("starting baseline executor")
    log.info(
        "runtime_mode=%s safe_mode=%s demo_flag=%s",
        settings.runtime_mode.value,
        settings.safe_mode,
        settings.okx_flag_demo,
    )
    log.info(
        "inst_id=%s sqlite_path=%s loop_sleep=%s tick_size=%s",
        inst_id,
        settings.sqlite_path,
        settings.loop_sleep_sec,
        tick_size,
    )
    log.info(
        "strategy_config decision_step=%s cooldown=%s tp_ticks=%s sl_ticks=%s timeout=%s",
        strategy.config.decision_step_sec,
        strategy.config.cooldown_sec,
        strategy.config.take_profit_ticks,
        strategy.config.stop_loss_ticks,
        strategy.config.timeout_sec,
    )
    if run_seconds is not None or max_loops is not None:
        log.info("smoke limits: run_seconds=%s max_loops=%s", run_seconds, max_loops)

    active_position: ActivePosition | None = None
    active_order_id: str | None = None
    active_order_client_id: str | None = None

    try:
        while True:
            now = ctx.clock.now_utc()
            loop_count += 1
            if max_loops is not None and loop_count > max_loops:
                log.info("stop reason: max_loops reached (%s)", max_loops)
                break
            if run_seconds is not None:
                elapsed = (now - started_at).total_seconds()
                if elapsed >= run_seconds:
                    log.info("stop reason: run_seconds reached (%s)", run_seconds)
                    break
            try:
                ticker = await ctx.exchange.get_ticker_last(inst_id=inst_id)
                account = await ctx.exchange.get_account_snapshot()
                _ = account
                executor_healthy = True
                market_data_fresh = _is_market_data_fresh(ticker.ts_ms, now)
            except Exception as exc:  # noqa: BLE001
                executor_healthy = False
                market_data_fresh = False
                log.exception("executor unhealthy: %s", exc)
                store.save_service_event(
                    event_type="error",
                    message="executor unhealthy",
                    payload={"error": str(exc)},
                    level="ERROR",
                )
                await asyncio.sleep(settings.loop_sleep_sec)
                continue

            open_orders = await ctx.exchange.get_open_orders(inst_id=inst_id)
            has_active_order = len(open_orders) > 0 or active_order_id is not None
            positions = await ctx.exchange.get_positions(inst_id=inst_id)
            has_open_position = len(positions) > 0 or active_position is not None

            if active_order_id and active_order_client_id:
                local_order_id = active_order_client_id
                order = await ctx.exchange.get_order(inst_id=inst_id, ord_id=active_order_id)
                if order and order.state == "filled":
                    entry_price = order.avg_px or order.px or ticker.last
                    position_side: Literal["long", "short"] = "long" if order.side == "buy" else "short"
                    active_position = _build_active_position(
                        position_id=new_client_order_id(prefix="pos"),
                        side=position_side,
                        entry_price=entry_price,
                        entry_ts=now,
                        size=order.fill_sz if order.fill_sz > 0 else Decimal(settings.okx_order_size),
                        tick_size=tick_size,
                        strategy=strategy,
                    )
                    active_order_id = None
                    active_order_client_id = None
                    has_active_order = False
                    has_open_position = True
                    log.info(
                        "position opened: id=%s side=%s entry=%s tp=%s sl=%s",
                        active_position.position_id,
                        active_position.side,
                        active_position.entry_price,
                        active_position.tp_price,
                        active_position.sl_price,
                    )
                    store.save_service_event(
                        event_type="entry_filled",
                        message="entry order filled",
                        payload={"position_id": active_position.position_id},
                    )
                    store.save_order(
                        local_order_id=local_order_id,
                        exchange_order_id=order.ord_id,
                        side=order.side,
                        order_type=settings.okx_ord_type,
                        price=float(entry_price),
                        size=float(active_position.size),
                        status=order.state,
                        created_at=now.isoformat(),
                        filled_at=now.isoformat(),
                    )
                    store.save_position_open(
                        position_id=active_position.position_id,
                        side=active_position.side,
                        entry_price=float(active_position.entry_price),
                        entry_ts=active_position.entry_ts.isoformat(),
                        size=float(active_position.size),
                    )
                elif order and order.state in {"canceled", "rejected"}:
                    log.warning("entry order not filled: ord_id=%s state=%s", order.ord_id, order.state)
                    store.save_service_event(
                        event_type="entry_not_filled",
                        message="entry order canceled/rejected",
                        payload={"ord_id": order.ord_id, "state": order.state},
                        level="WARNING",
                    )
                    store.save_order(
                        local_order_id=local_order_id,
                        exchange_order_id=order.ord_id,
                        side=order.side,
                        order_type=settings.okx_ord_type,
                        price=float(order.avg_px or order.px) if (order.avg_px or order.px) else None,
                        size=float(order.sz),
                        status=order.state,
                        created_at=now.isoformat(),
                    )
                    active_order_id = None
                    active_order_client_id = None

            if active_position is None:
                if strategy.should_decide(
                    now=now,
                    has_open_position=has_open_position,
                    has_active_order=has_active_order,
                    executor_healthy=executor_healthy,
                    market_data_fresh=market_data_fresh,
                ):
                    signal = strategy.make_decision(now=now)
                    domain_signal = signal.to_domain_signal(InstrumentId(inst_id))
                    log.info("strategy decided %s signal_id=%s", signal.side.upper(), signal.signal_id)
                    store.save_signal(
                        signal_id=signal.signal_id,
                        strategy_name=signal.strategy_name,
                        side=signal.side,
                        created_at=signal.created_at.isoformat(),
                    )
                    store.save_service_event(
                        event_type="decision",
                        message="strategy made decision",
                        payload={"side": signal.side, "signal_id": signal.signal_id},
                    )

                    order_side = "buy" if signal.side == "long" else "sell"
                    exchange_order_id = await ctx.exchange.place_market_order(
                        side=order_side,
                        size=settings.okx_order_size,
                        cl_ord_id=domain_signal.signal_id,
                    )
                    active_order_id = exchange_order_id
                    active_order_client_id = domain_signal.signal_id
                    log.info(
                        "entry order submitted: side=%s ord_id=%s",
                        order_side,
                        exchange_order_id,
                    )
                    store.save_service_event(
                        event_type="entry_submitted",
                        message="entry order submitted",
                        payload={"ord_id": exchange_order_id, "side": order_side},
                    )
                    store.save_order(
                        local_order_id=domain_signal.signal_id,
                        exchange_order_id=exchange_order_id,
                        side=order_side,
                        order_type=settings.okx_ord_type,
                        price=None,
                        size=float(Decimal(settings.okx_order_size)),
                        status="submitted",
                        created_at=now.isoformat(),
                    )
                else:
                    if int(now.timestamp()) % strategy.config.decision_step_sec == 0:
                        store.save_service_event(
                            event_type="decision_skipped",
                            message="decision skipped",
                            payload={
                                "has_open_position": has_open_position,
                                "has_active_order": has_active_order,
                                "executor_healthy": executor_healthy,
                                "market_data_fresh": market_data_fresh,
                            },
                        )
            else:
                reason = _check_exit_reason(active_position, ticker.last, now)
                if reason:
                    exit_side = "sell" if active_position.side == "long" else "buy"
                    exit_order_id = await ctx.exchange.place_market_order(
                        side=exit_side,
                        size=str(active_position.size),
                        cl_ord_id=new_client_order_id(prefix="exit"),
                        reduce_only=True,
                    )
                    log.info(
                        "%s triggered, exit submitted ord_id=%s price=%s",
                        reason,
                        exit_order_id,
                        ticker.last,
                    )
                    store.save_service_event(
                        event_type=f"{reason.lower()}_exit",
                        message=f"{reason} exit submitted",
                        payload={"ord_id": exit_order_id, "position_id": active_position.position_id},
                    )
                    exit_order = await ctx.exchange.get_order(inst_id=inst_id, ord_id=exit_order_id)
                    exit_price = (
                        exit_order.avg_px if exit_order and exit_order.avg_px else ticker.last
                    )
                    gross_pnl = _calc_gross_pnl(active_position, exit_price)
                    holding = (now - active_position.entry_ts).total_seconds()
                    trade = TradeResult(
                        position_id=active_position.position_id,
                        gross_pnl=float(gross_pnl),
                        fees=0.0,
                        net_pnl=float(gross_pnl),
                        holding_seconds=holding,
                    )
                    store.save_position_close(
                        position_id=active_position.position_id,
                        exit_price=float(exit_price),
                        exit_ts=now.isoformat(),
                        exit_reason=reason,
                    )
                    store.save_trade_result(trade)
                    store.save_service_event(
                        event_type="position_closed",
                        message="position closed",
                        payload={
                            "position_id": active_position.position_id,
                            "reason": reason,
                            "gross_pnl": float(gross_pnl),
                        },
                    )
                    log.info(
                        "position closed: id=%s reason=%s gross_pnl=%s cooldown=%ss",
                        active_position.position_id,
                        reason,
                        gross_pnl,
                        strategy.config.cooldown_sec,
                    )
                    strategy.on_position_closed(now)
                    active_position = None
                    active_order_id = None
                    active_order_client_id = None

            await asyncio.sleep(settings.loop_sleep_sec)
    finally:
        summary = store.get_counts_summary()
        log.info("Run finished")
        log.info("signals: %s", summary["signals"])
        log.info("orders: %s", summary["orders"])
        log.info("positions: %s", summary["positions"])
        log.info("trade_results: %s", summary["trade_results"])
        log.info("service_events: %s", summary["service_events"])
        store.close()
    return summary


def _is_market_data_fresh(ts_ms: int, now: datetime) -> bool:
    tick_ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return now - tick_ts <= timedelta(seconds=10)


def _build_active_position(
    *,
    position_id: str,
    side: Literal["long", "short"],
    entry_price: Decimal,
    entry_ts: datetime,
    size: Decimal,
    tick_size: Decimal,
    strategy: RandomBaselineStrategy,
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
        side=side,
        entry_price=entry_price,
        entry_ts=entry_ts,
        size=size,
        tp_price=tp,
        sl_price=sl,
        timeout_at=entry_ts + timedelta(seconds=strategy.config.timeout_sec),
    )


def _check_exit_reason(position: ActivePosition, price: Decimal, now: datetime) -> str | None:
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


def _calc_gross_pnl(position: ActivePosition, exit_price: Decimal) -> Decimal:
    if position.side == "long":
        return (exit_price - position.entry_price) * position.size
    return (position.entry_price - exit_price) * position.size
