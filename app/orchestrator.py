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


@dataclass(slots=True)
class ActiveOrder:
    order_id: str
    client_id: str
    side: Literal["buy", "sell"]
    purpose: Literal["entry", "exit"]
    created_at: datetime
    last_reprice_at: datetime
    reduce_only: bool
    size: str


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
    active_order: ActiveOrder | None = None

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

            try:
                open_orders = await ctx.exchange.get_open_orders(inst_id=inst_id)
                has_active_order = len(open_orders) > 0 or active_order is not None
                positions = await ctx.exchange.get_positions(inst_id=inst_id)
                has_open_position = len(positions) > 0 or active_position is not None

                okx_inst_positions = [p for p in positions if p.inst_id == inst_id]
                if not okx_inst_positions and positions:
                    okx_inst_positions = list(positions)
                if active_position is None and okx_inst_positions:
                    okx_pos = okx_inst_positions[0]
                    if okx_pos.avg_px is not None:
                        reconciled_side: Literal["long", "short"] = (
                            "long" if okx_pos.pos > 0 else "short"
                        )
                        reconciled_size = abs(okx_pos.pos)
                        entry_ts = (
                            datetime.fromtimestamp(
                                okx_pos.c_time_ms / 1000, tz=timezone.utc
                            )
                            if okx_pos.c_time_ms is not None
                            else now
                        )
                        stable_pid = (
                            f"pos-ex-{okx_pos.pos_id}"
                            if okx_pos.pos_id
                            else f"pos-ex-{inst_id}"
                        )
                        active_position = _build_active_position(
                            position_id=stable_pid,
                            side=reconciled_side,
                            entry_price=okx_pos.avg_px,
                            entry_ts=entry_ts,
                            size=reconciled_size,
                            tick_size=tick_size,
                            strategy=strategy,
                        )
                        has_open_position = True
                        log.warning(
                            "reconciled active_position from exchange: id=%s side=%s entry=%s size=%s",
                            stable_pid,
                            reconciled_side,
                            okx_pos.avg_px,
                            reconciled_size,
                        )
                        store.save_position_open(
                            position_id=active_position.position_id,
                            side=active_position.side,
                            entry_price=float(active_position.entry_price),
                            entry_ts=active_position.entry_ts.isoformat(),
                            size=float(active_position.size),
                        )
                        store.save_service_event(
                            event_type="position_reconciled",
                            message="restored in-memory position from exchange snapshot",
                            payload={
                                "position_id": stable_pid,
                                "side": reconciled_side,
                                "entry_price": str(okx_pos.avg_px),
                                "pos_id": okx_pos.pos_id,
                            },
                            level="WARNING",
                        )
                    else:
                        log.debug(
                            "reconcile skipped: OKX reports non-zero pos but avgPx missing inst_id=%s",
                            inst_id,
                        )

                if active_order is not None:
                    local_order_id = active_order.client_id
                    order = await ctx.exchange.get_order(inst_id=inst_id, ord_id=active_order.order_id)
                    if order and order.state == "filled":
                        fill_price = order.avg_px or order.px or ticker.last
                        if active_order.purpose == "entry":
                            position_side: Literal["long", "short"] = (
                                "long" if order.side == "buy" else "short"
                            )
                            active_position = _build_active_position(
                                position_id=new_client_order_id(prefix="pos"),
                                side=position_side,
                                entry_price=fill_price,
                                entry_ts=now,
                                size=order.fill_sz if order.fill_sz > 0 else Decimal(settings.okx_order_size),
                                tick_size=tick_size,
                                strategy=strategy,
                            )
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
                            store.save_position_open(
                                position_id=active_position.position_id,
                                side=active_position.side,
                                entry_price=float(active_position.entry_price),
                                entry_ts=active_position.entry_ts.isoformat(),
                                size=float(active_position.size),
                            )
                        else:
                            if active_position is not None:
                                gross_pnl = _calc_gross_pnl(active_position, fill_price)
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
                                    exit_price=float(fill_price),
                                    exit_ts=now.isoformat(),
                                    exit_reason="maker_exit",
                                )
                                store.save_trade_result(trade)
                                store.save_service_event(
                                    event_type="position_closed",
                                    message="position closed",
                                    payload={
                                        "position_id": active_position.position_id,
                                        "gross_pnl": float(gross_pnl),
                                    },
                                )
                                log.info(
                                    "position closed: id=%s gross_pnl=%s cooldown=%ss",
                                    active_position.position_id,
                                    gross_pnl,
                                    strategy.config.cooldown_sec,
                                )
                                strategy.on_position_closed(now)
                                active_position = None
                                has_open_position = False
                        active_order = None
                        has_active_order = False
                        store.save_order(
                            local_order_id=local_order_id,
                            exchange_order_id=order.ord_id,
                            side=order.side,
                            order_type="post_only",
                            price=float(fill_price),
                            size=float(order.fill_sz if order.fill_sz > 0 else order.sz),
                            status=order.state,
                            created_at=now.isoformat(),
                            filled_at=now.isoformat(),
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
                        active_order = None
                    elif order and order.state in {"live", "partially_filled"}:
                        reprice_elapsed = (now - active_order.last_reprice_at).total_seconds()
                        max_wait_elapsed = (now - active_order.created_at).total_seconds()
                        if (
                            reprice_elapsed >= settings.okx_maker_reprice_sec
                            and max_wait_elapsed <= settings.okx_maker_max_wait_sec
                        ):
                            try:
                                await ctx.exchange.cancel_order_by_client_id(
                                    inst_id=inst_id,
                                    cl_ord_id=active_order.client_id,
                                )
                            except RuntimeError as exc:
                                if _is_okx_cancel_already_done_error(exc):
                                    log.info(
                                        "cancel skipped during reprice (already final): clOrdId=%s",
                                        active_order.client_id,
                                    )
                                    continue
                                raise
                            best_bid, best_ask = await ctx.exchange.get_best_bid_ask(inst_id=inst_id)
                            reprice = _maker_price_for_side(
                                side=active_order.side,
                                best_bid=best_bid,
                                best_ask=best_ask,
                                tick_size=tick_size,
                            )
                            new_client_id = new_client_order_id(
                                prefix="entry" if active_order.purpose == "entry" else "exit"
                            )
                            try:
                                new_order_id = await ctx.exchange.place_limit_post_only(
                                    side=active_order.side,
                                    size=active_order.size,
                                    price=reprice,
                                    cl_ord_id=new_client_id,
                                    reduce_only=active_order.reduce_only,
                                )
                            except RuntimeError as exc:
                                # OKX: 51169 no position to reduce; 51170 reduce-only wrong side vs exchange book.
                                if active_order.purpose == "exit" and _is_okx_reduce_sync_error(exc):
                                    log.warning(
                                        "exit reprice skipped: exchange rejected reduce-only (ord_id=%s): %s",
                                        active_order.order_id,
                                        exc,
                                    )
                                    store.save_service_event(
                                        event_type="exit_sync_lost",
                                        message="exit reprice rejected: reduce-only sync error",
                                        payload={
                                            "ord_id": active_order.order_id,
                                            "error": str(exc),
                                        },
                                        level="WARNING",
                                    )
                                    active_order = None
                                    if active_position is not None:
                                        try:
                                            exchange_positions = await ctx.exchange.get_positions(
                                                inst_id=inst_id
                                            )
                                        except Exception as sync_exc:  # noqa: BLE001
                                            log.warning(
                                                "exit sync check failed after reprice reject: %s",
                                                sync_exc,
                                            )
                                            has_active_order = False
                                            continue
                                        if exchange_positions:
                                            log.warning(
                                                "exit sync mismatch: exchange still reports %s open position(s), keep local position",
                                                len(exchange_positions),
                                            )
                                            has_open_position = True
                                            has_active_order = False
                                            continue
                                        store.save_position_close(
                                            position_id=active_position.position_id,
                                            exit_price=float(ticker.last),
                                            exit_ts=now.isoformat(),
                                            exit_reason="sync_lost",
                                        )
                                        store.save_service_event(
                                            event_type="position_closed_sync",
                                            message="position closed via sync reconcile",
                                            payload={
                                                "position_id": active_position.position_id,
                                                "reason": "exit_reprice_rejected",
                                            },
                                        )
                                        strategy.on_position_closed(now)
                                        active_position = None
                                        has_open_position = False
                                    has_active_order = False
                                    continue
                                raise
                            log.info(
                                "maker reprice: purpose=%s old_ord=%s new_ord=%s px=%s",
                                active_order.purpose,
                                active_order.order_id,
                                new_order_id,
                                reprice,
                            )
                            active_order = ActiveOrder(
                                order_id=new_order_id,
                                client_id=new_client_id,
                                side=active_order.side,
                                purpose=active_order.purpose,
                                created_at=active_order.created_at,
                                last_reprice_at=now,
                                reduce_only=active_order.reduce_only,
                                size=active_order.size,
                            )
                        elif max_wait_elapsed > settings.okx_maker_max_wait_sec:
                            log.warning(
                                "maker order timeout: purpose=%s ord_id=%s wait=%ss",
                                active_order.purpose,
                                active_order.order_id,
                                settings.okx_maker_max_wait_sec,
                            )
                            try:
                                await ctx.exchange.cancel_order_by_client_id(
                                    inst_id=inst_id,
                                    cl_ord_id=active_order.client_id,
                                )
                            except RuntimeError as exc:
                                if not _is_okx_cancel_already_done_error(exc):
                                    raise
                            active_order = None

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

                        order_side: Literal["buy", "sell"] = (
                            "buy" if signal.side == "long" else "sell"
                        )
                        best_bid, best_ask = await ctx.exchange.get_best_bid_ask(inst_id=inst_id)
                        maker_px = _maker_price_for_side(
                            side=order_side,
                            best_bid=best_bid,
                            best_ask=best_ask,
                            tick_size=tick_size,
                        )
                        exchange_order_id = await ctx.exchange.place_limit_post_only(
                            side=order_side,
                            size=settings.okx_order_size,
                            price=maker_px,
                            cl_ord_id=domain_signal.signal_id,
                        )
                        active_order = ActiveOrder(
                            order_id=exchange_order_id,
                            client_id=domain_signal.signal_id,
                            side=order_side,
                            purpose="entry",
                            created_at=now,
                            last_reprice_at=now,
                            reduce_only=False,
                                size=settings.okx_order_size,
                        )
                        log.info(
                            "entry maker order submitted: side=%s ord_id=%s px=%s",
                            order_side,
                            exchange_order_id,
                            maker_px,
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
                            order_type="post_only",
                            price=float(maker_px),
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
                        best_bid, best_ask = await ctx.exchange.get_best_bid_ask(inst_id=inst_id)
                        maker_px = _maker_price_for_side(
                            side=exit_side,
                            best_bid=best_bid,
                            best_ask=best_ask,
                            tick_size=tick_size,
                        )
                        exit_client_id = new_client_order_id(prefix="exit")
                        try:
                            exit_order_id = await ctx.exchange.place_limit_post_only(
                                side=exit_side,
                                size=str(active_position.size),
                                price=maker_px,
                                cl_ord_id=exit_client_id,
                                reduce_only=True,
                            )
                        except RuntimeError as exc:
                            if _is_okx_reduce_sync_error(exc):
                                log.warning(
                                    "exit submit skipped: exchange rejected reduce-only for %s: %s",
                                    active_position.position_id,
                                    exc,
                                )
                                store.save_service_event(
                                    event_type="exit_sync_lost",
                                    message="exit submit rejected: reduce-only sync error",
                                    payload={
                                        "position_id": active_position.position_id,
                                        "reason": reason,
                                        "error": str(exc),
                                    },
                                    level="WARNING",
                                )
                                try:
                                    exchange_positions = await ctx.exchange.get_positions(
                                        inst_id=inst_id
                                    )
                                except Exception as sync_exc:  # noqa: BLE001
                                    log.warning(
                                        "exit sync check failed after submit reject: %s",
                                        sync_exc,
                                    )
                                    continue
                                if exchange_positions:
                                    log.warning(
                                        "exit sync mismatch: exchange still reports %s open position(s), keep local position",
                                        len(exchange_positions),
                                    )
                                    has_open_position = True
                                    continue
                                store.save_position_close(
                                    position_id=active_position.position_id,
                                    exit_price=float(ticker.last),
                                    exit_ts=now.isoformat(),
                                    exit_reason="sync_lost",
                                )
                                store.save_service_event(
                                    event_type="position_closed_sync",
                                    message="position closed via sync reconcile",
                                    payload={
                                        "position_id": active_position.position_id,
                                        "reason": reason,
                                    },
                                )
                                strategy.on_position_closed(now)
                                active_position = None
                                has_open_position = False
                                continue
                            raise
                        active_order = ActiveOrder(
                            order_id=exit_order_id,
                            client_id=exit_client_id,
                            side=exit_side,
                            purpose="exit",
                            created_at=now,
                            last_reprice_at=now,
                            reduce_only=True,
                            size=str(active_position.size),
                        )
                        log.info(
                            "%s triggered, exit maker submitted ord_id=%s px=%s",
                            reason,
                            exit_order_id,
                            maker_px,
                        )
                        store.save_service_event(
                            event_type=f"{reason.lower()}_exit",
                            message=f"{reason} exit submitted",
                            payload={"ord_id": exit_order_id, "position_id": active_position.position_id},
                        )
                        store.save_order(
                            local_order_id=exit_client_id,
                            exchange_order_id=exit_order_id,
                            side=exit_side,
                            order_type="post_only",
                            price=float(maker_px),
                            size=float(active_position.size),
                            status="submitted",
                            created_at=now.isoformat(),
                        )

            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "baseline iteration failed (retrying): %s: %s",
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                store.save_service_event(
                    event_type="loop_iteration_error",
                    message="baseline iteration failed",
                    payload={"error": str(exc), "error_type": type(exc).__name__},
                    level="ERROR",
                )
                _backoff = min(30.0, max(settings.loop_sleep_sec * 5.0, 5.0))
                await asyncio.sleep(_backoff)
                continue

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


def _maker_price_for_side(
    *,
    side: Literal["buy", "sell"],
    best_bid: Decimal,
    best_ask: Decimal,
    tick_size: Decimal,
) -> Decimal:
    if side == "buy":
        return best_bid.quantize(tick_size)
    return best_ask.quantize(tick_size)


def _is_okx_reduce_sync_error(exc: Exception) -> bool:
    """OKX reduce-only rejects when local view and exchange position disagree."""
    text = str(exc)
    return "sCode=51169" in text or "sCode=51170" in text


def _is_okx_cancel_already_done_error(exc: Exception) -> bool:
    text = str(exc)
    return "sCode=51400" in text
