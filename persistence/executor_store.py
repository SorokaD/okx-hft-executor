"""Двойная запись: SQLite (ops) + PostgreSQL (аналитика) без блокировки торгового цикла."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from config.settings import Settings
from execution.trade_lifecycle import TradeLifecycleTracker
from persistence.postgres_journal import PostgresJournal, RunFinishParams, RunStartParams, StrategyParams
from persistence.sqlite_store import SqliteMvpStore, TradeResult

log = logging.getLogger(__name__)

_RECONCILE_EVENT_TYPES = frozenset(
    {
        "startup_reconcile_failed",
        "position_reconciled",
        "position_closed_sync",
        "exit_sync_lost",
    }
)

_ATTEMPT_EVENT_TYPES: dict[str, tuple[str, str]] = {
    "loop_iteration_error": ("loop_error", "error"),
    "error": ("health_check", "error"),
    "decision_skipped": ("skip_decision", "skipped"),
}


@dataclass(slots=True)
class PositionMeta:
    side: str
    entry_price: float
    entry_ts: str
    size: float
    entry_signal_id: str | None = None
    entry_order_id_local: str | None = None
    exit_order_id_local: str | None = None
    exit_price: float | None = None
    exit_ts: str | None = None
    exit_reason: str | None = None


class ExecutorStore:
    """
    Фасад над SqliteMvpStore и PostgresJournal.

    Торговый цикл вызывает те же методы, что и раньше; PG-запись — fire-and-forget.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        strategy_name: str,
        inst_id: str,
        td_mode: str,
        journal: PostgresJournal | None = None,
    ) -> None:
        self._settings = settings
        self._strategy_name = strategy_name
        self._inst_id = inst_id
        self._td_mode = td_mode
        self._sqlite = SqliteMvpStore(settings.sqlite_path)
        self._journal = journal
        self._run_id: int | None = None
        self._strategy_params = StrategyParams()
        self._position_meta: dict[str, PositionMeta] = {}
        self._submitted_orders: set[str] = set()
        self._last_order_by_purpose: dict[str, str] = {}
        self._trade_lifecycle: TradeLifecycleTracker | None = None

    @classmethod
    def create(
        cls,
        settings: Settings,
        *,
        strategy_name: str,
        inst_id: str,
        td_mode: str = "isolated",
    ) -> ExecutorStore:
        journal: PostgresJournal | None = None
        if settings.postgres_is_configured():
            dsn = settings.get_database_url()
            assert dsn is not None
            journal = PostgresJournal(
                dsn,
                schema=settings.postgres_schema,
                queue_size=settings.postgres_queue_size,
            )
            log.info(
                "postgres journal enabled schema=%s queue_size=%s",
                settings.postgres_schema,
                settings.postgres_queue_size,
            )
        else:
            log.info("postgres journal disabled (not configured or OKX_HFT_POSTGRES_ENABLED=0)")
        return cls(
            settings,
            strategy_name=strategy_name,
            inst_id=inst_id,
            td_mode=td_mode,
            journal=journal,
        )

    @property
    def sqlite(self) -> SqliteMvpStore:
        return self._sqlite

    @property
    def run_id(self) -> int | None:
        return self._run_id

    def set_strategy_params(
        self,
        *,
        take_profit_ticks: int | None = None,
        stop_loss_ticks: int | None = None,
        timeout_sec: int | None = None,
    ) -> None:
        self._strategy_params = StrategyParams(
            take_profit_ticks=take_profit_ticks,
            stop_loss_ticks=stop_loss_ticks,
            timeout_sec=timeout_sec,
        )

    async def open(self, *, extra_json: dict[str, Any] | None = None) -> None:
        if self._journal is None:
            return
        params = RunStartParams(
            runtime_mode=self._settings.runtime_mode.value,
            environment_name=self._settings.env,
            strategy_name=self._strategy_name,
            inst_id=self._inst_id,
            extra_json=extra_json or {},
        )
        self._run_id = await asyncio.to_thread(self._journal.start_run, params)
        log.info("postgres executor_run started run_id=%s", self._run_id)

    async def aclose(
        self,
        *,
        status: str = "stopped",
        stop_reason: str | None = None,
    ) -> None:
        if self._journal is not None and self._run_id is not None:
            finish = RunFinishParams(
                run_id=self._run_id,
                status=status,
                stop_reason=stop_reason,
            )
            self._journal.finish_run(finish)
            await asyncio.to_thread(self._journal.stop)
            dropped = self._journal.dropped_events
            if dropped:
                log.warning("postgres journal dropped_events=%s", dropped)
        self._sqlite.close()

    def close(self) -> None:
        self._sqlite.close()

    def begin_trade_lifecycle(self, signal_id: str, *, tick_size: Any = None) -> None:
        from decimal import Decimal

        ts = Decimal(str(tick_size)) if tick_size is not None else None
        self._trade_lifecycle = TradeLifecycleTracker()
        self._trade_lifecycle.begin(signal_id, tick_size=ts)

    def get_trade_lifecycle(self) -> TradeLifecycleTracker | None:
        return self._trade_lifecycle

    def clear_trade_lifecycle(self) -> None:
        self._trade_lifecycle = None

    def get_counts_summary(self) -> dict[str, int]:
        return self._sqlite.get_counts_summary()

    def list_open_positions(self, *, strategy_name: str | None = None) -> list[Any]:
        return self._sqlite.list_open_positions(strategy_name=strategy_name)

    def close_open_position_reconciled(
        self,
        *,
        position_id: str,
        exit_ts: str,
        exit_reason: str,
    ) -> None:
        self._sqlite.close_open_position_reconciled(
            position_id=position_id,
            exit_ts=exit_ts,
            exit_reason=exit_reason,
        )
        if self._journal is not None and self._run_id is not None:
            meta = self._position_meta.get(position_id)
            exit_price = meta.entry_price if meta else 0.0
            self._journal.enqueue_position_close(
                position_id=position_id,
                exit_price=exit_price,
                exit_ts=exit_ts,
                exit_reason=exit_reason,
                status="reconciled",
            )

    def upsert_strategy_registry(self, **kwargs: Any) -> None:
        self._sqlite.upsert_strategy_registry(**kwargs)

    def set_strategy_runtime_state(self, **kwargs: Any) -> None:
        self._sqlite.set_strategy_runtime_state(**kwargs)

    def set_strategy_desired_state(self, **kwargs: Any) -> None:
        self._sqlite.set_strategy_desired_state(**kwargs)

    def list_strategies_registry(self) -> list[dict[str, str]]:
        return self._sqlite.list_strategies_registry()

    def enqueue_strategy_command(self, **kwargs: Any) -> None:
        self._sqlite.enqueue_strategy_command(**kwargs)

    def claim_pending_strategy_commands(self) -> list[dict[str, Any]]:
        return self._sqlite.claim_pending_strategy_commands()

    def finish_strategy_command(self, **kwargs: Any) -> None:
        self._sqlite.finish_strategy_command(**kwargs)

    def save_signal(
        self,
        *,
        signal_id: str,
        strategy_name: str,
        side: str,
        created_at: str,
        market_snapshot: dict[str, Any] | None = None,
    ) -> None:
        self._sqlite.save_signal(
            signal_id=signal_id,
            strategy_name=strategy_name,
            side=side,
            created_at=created_at,
        )
        if self._journal is not None and self._run_id is not None:
            self._journal.enqueue_signal(
                run_id=self._run_id,
                signal_id=signal_id,
                strategy_name=strategy_name,
                inst_id=self._inst_id,
                side=side,
                ts_decision=created_at,
                take_profit_ticks=self._strategy_params.take_profit_ticks,
                stop_loss_ticks=self._strategy_params.stop_loss_ticks,
                timeout_sec=self._strategy_params.timeout_sec,
                market_snapshot=market_snapshot,
            )

    def record_cancel_attempt(
        self,
        *,
        order_id_local: str,
        exchange_order_id: str | None,
        strategy_name: str,
        purpose: str,
    ) -> None:
        if self._journal is None or self._run_id is None:
            return
        self._journal.enqueue_execution_attempt(
            run_id=self._run_id,
            inst_id=self._inst_id,
            strategy_name=strategy_name,
            action_type="cancel_order",
            status="ok",
            signal_id=order_id_local if purpose == "entry" else None,
            request_payload={
                "cl_ord_id": order_id_local,
                "ord_id": exchange_order_id,
                "purpose": purpose,
            },
        )

    def save_order(
        self,
        *,
        local_order_id: str,
        strategy_name: str,
        exchange_order_id: str | None,
        side: str,
        order_type: str,
        price: float | None,
        size: float,
        status: str,
        created_at: str,
        filled_at: str | None = None,
        signal_id: str | None = None,
        position_id: str | None = None,
        parent_order_id_local: str | None = None,
        position_action: str | None = None,
        reduce_only: bool = False,
    ) -> None:
        self._sqlite.save_order(
            local_order_id=local_order_id,
            strategy_name=strategy_name,
            exchange_order_id=exchange_order_id,
            side=side,
            order_type=order_type,
            price=price,
            size=size,
            status=status,
            created_at=created_at,
            filled_at=filled_at,
        )
        if self._journal is None or self._run_id is None:
            return

        inferred_action = position_action
        if inferred_action is None:
            if reduce_only or local_order_id.startswith("exit"):
                inferred_action = "close"
            else:
                inferred_action = "open"

        if status == "submitted" and local_order_id not in self._submitted_orders:
            self._submitted_orders.add(local_order_id)
            self._journal.enqueue_order_insert(
                run_id=self._run_id,
                order_id_local=local_order_id,
                strategy_name=strategy_name,
                inst_id=self._inst_id,
                side=side,
                ord_type=order_type,
                price=price,
                size=size,
                status=status,
                exchange_order_id=exchange_order_id,
                signal_id=signal_id or (local_order_id if inferred_action == "open" else None),
                position_id=position_id,
                parent_order_id_local=parent_order_id_local,
                position_action=inferred_action,
                reduce_only=reduce_only,
                td_mode=self._td_mode,
                ts_created=created_at,
            )
            self._journal.enqueue_execution_attempt(
                run_id=self._run_id,
                inst_id=self._inst_id,
                strategy_name=strategy_name,
                action_type="submit_order",
                status="ok",
                signal_id=signal_id or (local_order_id if inferred_action == "open" else None),
                side=side,
                request_payload={
                    "cl_ord_id": local_order_id,
                    "ord_type": order_type,
                    "px": price,
                    "sz": size,
                    "reduce_only": reduce_only,
                },
                response_payload={"ord_id": exchange_order_id},
            )
            if inferred_action == "open":
                self._last_order_by_purpose["entry"] = local_order_id
            elif inferred_action == "close":
                self._last_order_by_purpose["exit"] = local_order_id
                if position_id and position_id in self._position_meta:
                    self._position_meta[position_id].exit_order_id_local = local_order_id
        else:
            self._journal.enqueue_order_update(
                order_id_local=local_order_id,
                status=status,
                exchange_order_id=exchange_order_id,
                price=price,
                filled_size=size if status == "filled" else None,
                filled_at=filled_at,
            )
            if status == "filled" and filled_at:
                self._journal.enqueue_order_fill(
                    run_id=self._run_id,
                    order_id_local=local_order_id,
                    exchange_order_id=exchange_order_id,
                    inst_id=self._inst_id,
                    strategy_name=strategy_name,
                    side=side,
                    fill_price=price or 0.0,
                    fill_size=size,
                    ts_fill=filled_at,
                )
            if status in {"canceled", "rejected"}:
                self._journal.enqueue_execution_attempt(
                    run_id=self._run_id,
                    inst_id=self._inst_id,
                    strategy_name=strategy_name,
                    action_type="order_final",
                    status=status,
                    side=side,
                    response_payload={"ord_id": exchange_order_id, "state": status},
                )

    def save_position_open(
        self,
        *,
        position_id: str,
        strategy_name: str,
        side: str,
        entry_price: float,
        entry_ts: str,
        size: float,
        entry_signal_id: str | None = None,
        entry_order_id_local: str | None = None,
    ) -> None:
        self._sqlite.save_position_open(
            position_id=position_id,
            strategy_name=strategy_name,
            side=side,
            entry_price=entry_price,
            entry_ts=entry_ts,
            size=size,
        )
        entry_signal = entry_signal_id or self._last_order_by_purpose.get("entry")
        entry_order = entry_order_id_local or entry_signal
        self._position_meta[position_id] = PositionMeta(
            side=side,
            entry_price=entry_price,
            entry_ts=entry_ts,
            size=size,
            entry_signal_id=entry_signal,
            entry_order_id_local=entry_order,
        )
        if self._journal is not None and self._run_id is not None:
            self._journal.enqueue_position_open(
                run_id=self._run_id,
                position_id=position_id,
                strategy_name=strategy_name,
                inst_id=self._inst_id,
                side=side,
                entry_price=entry_price,
                entry_ts=entry_ts,
                size=size,
                take_profit_ticks=self._strategy_params.take_profit_ticks,
                stop_loss_ticks=self._strategy_params.stop_loss_ticks,
                timeout_sec=self._strategy_params.timeout_sec,
                entry_signal_id=entry_signal,
                entry_order_id_local=entry_order,
            )

    def save_position_close(
        self,
        *,
        position_id: str,
        exit_price: float,
        exit_ts: str,
        exit_reason: str,
        close_source: str | None = None,
    ) -> None:
        self._sqlite.save_position_close(
            position_id=position_id,
            exit_price=exit_price,
            exit_ts=exit_ts,
            exit_reason=exit_reason,
        )
        meta = self._position_meta.get(position_id)
        if meta is not None:
            meta.exit_reason = exit_reason
            meta.exit_price = exit_price
            meta.exit_ts = exit_ts
        if self._journal is not None and self._run_id is not None:
            status = "reconciled" if exit_reason in {"sync_lost", "reconciled", "reconcile"} else "closed"
            self._journal.enqueue_position_close(
                position_id=position_id,
                exit_price=exit_price,
                exit_ts=exit_ts,
                exit_reason=exit_reason,
                status=status,
            )

    def save_trade_result(self, result: TradeResult) -> None:
        self._sqlite.save_trade_result(result)
        if self._journal is None or self._run_id is None:
            return
        meta = self._position_meta.get(result.position_id)
        if meta is None:
            log.warning("trade_result without position meta: %s", result.position_id)
            return
        trade_id = f"trade-{result.position_id}"
        exit_price = result.exit_avg_px or (meta.exit_price if meta.exit_price is not None else meta.entry_price)
        exit_ts = result.closed_at or meta.exit_ts or meta.entry_ts
        entry_ts = result.opened_at or meta.entry_ts
        metrics = result.execution_metrics or {}
        self._journal.enqueue_trade_result(
            run_id=self._run_id,
            trade_id=trade_id,
            position_id=result.position_id,
            inst_id=result.inst_id or self._inst_id,
            strategy_name=result.strategy_name,
            side=result.position_side or meta.side,
            entry_price=result.entry_avg_px or meta.entry_price,
            exit_price=exit_price,
            qty=result.size or meta.size,
            gross_pnl=result.gross_pnl,
            fees=result.fees,
            net_pnl=result.net_pnl,
            holding_seconds=result.holding_seconds,
            entry_ts=entry_ts,
            exit_ts=exit_ts,
            exit_reason=result.exit_reason or meta.exit_reason,
            entry_signal_id=result.signal_id or meta.entry_signal_id,
            entry_order_id_local=meta.entry_order_id_local,
            exit_order_id_local=meta.exit_order_id_local,
            entry_fee=result.entry_fee,
            exit_fee=result.exit_fee,
            fee_ccy=result.fee_ccy,
            entry_liquidity=result.entry_liquidity,
            exit_liquidity=result.exit_liquidity,
            fee_source=result.fee_source,
            fee_status=result.fee_status,
            close_source=result.close_source,
            execution_metrics=metrics,
        )

    def save_service_event(
        self,
        *,
        strategy_name: str = "system",
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
        level: str = "INFO",
    ) -> None:
        self._sqlite.save_service_event(
            strategy_name=strategy_name,
            event_type=event_type,
            message=message,
            payload=payload,
            level=level,
        )
        if self._journal is None or self._run_id is None:
            return
        self._journal.enqueue_service_event(
            run_id=self._run_id,
            strategy_name=strategy_name,
            event_type=event_type,
            message=message,
            level=level,
            inst_id=self._inst_id,
            payload=payload,
        )
        if event_type in _RECONCILE_EVENT_TYPES:
            self._journal.enqueue_reconciliation(
                run_id=self._run_id,
                inst_id=self._inst_id,
                strategy_name=strategy_name if strategy_name != "system" else self._strategy_name,
                severity=_level_to_severity(level),
                mismatch_type=event_type,
                message=message,
                local_entity_id=(payload or {}).get("position_id"),
                payload=payload,
            )
        attempt = _ATTEMPT_EVENT_TYPES.get(event_type)
        if attempt is not None:
            action_type, status = attempt
            self._journal.enqueue_execution_attempt(
                run_id=self._run_id,
                inst_id=self._inst_id,
                strategy_name=strategy_name if strategy_name != "system" else self._strategy_name,
                action_type=action_type,
                status=status,
                error_message=(payload or {}).get("error"),
                response_payload=payload or {},
            )


def _level_to_severity(level: str) -> str:
    normalized = level.upper()
    if normalized in {"ERROR", "CRITICAL"}:
        return "error"
    if normalized == "WARNING":
        return "warning"
    return "info"
