from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TradeResult:
    position_id: str
    strategy_name: str
    gross_pnl: float
    fees: float
    net_pnl: float
    holding_seconds: float


class SqliteMvpStore:
    """Простое SQLite-хранилище событий/результатов baseline MVP."""

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                side TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                local_order_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL DEFAULT 'unknown',
                exchange_order_id TEXT,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                price REAL,
                size REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                filled_at TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                position_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL DEFAULT 'unknown',
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                entry_ts TEXT NOT NULL,
                exit_ts TEXT,
                size REAL NOT NULL,
                exit_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS trade_results (
                position_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL DEFAULT 'unknown',
                gross_pnl REAL NOT NULL,
                fees REAL NOT NULL,
                net_pnl REAL NOT NULL,
                holding_seconds REAL NOT NULL,
                FOREIGN KEY(position_id) REFERENCES positions(position_id)
            );

            CREATE TABLE IF NOT EXISTS service_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                level TEXT NOT NULL,
                strategy_name TEXT NOT NULL DEFAULT 'system',
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                payload TEXT
            );

            CREATE TABLE IF NOT EXISTS strategies_registry (
                strategy_name TEXT PRIMARY KEY,
                inst_id TEXT NOT NULL,
                desired_state TEXT NOT NULL,
                runtime_state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS strategy_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                command_type TEXT NOT NULL,
                command_mode TEXT,
                created_at TEXT NOT NULL,
                processed_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error_text TEXT
            );
            """
        )
        self._ensure_schema_columns()
        self._conn.commit()

    def _ensure_schema_columns(self) -> None:
        """Добавляет новые колонки в существующую БД без ручных миграций."""
        self._ensure_column(
            table_name="orders",
            column_name="strategy_name",
            column_sql="TEXT NOT NULL DEFAULT 'unknown'",
        )
        self._ensure_column(
            table_name="positions",
            column_name="strategy_name",
            column_sql="TEXT NOT NULL DEFAULT 'unknown'",
        )
        self._ensure_column(
            table_name="trade_results",
            column_name="strategy_name",
            column_sql="TEXT NOT NULL DEFAULT 'unknown'",
        )
        self._ensure_column(
            table_name="service_events",
            column_name="strategy_name",
            column_sql="TEXT NOT NULL DEFAULT 'system'",
        )

    def _ensure_column(self, *, table_name: str, column_name: str, column_sql: str) -> None:
        cols = self._conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {str(col["name"]) for col in cols}
        if column_name in existing:
            return
        self._conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def save_signal(
        self,
        *,
        signal_id: str,
        strategy_name: str,
        side: str,
        created_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO signals(signal_id, strategy_name, side, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (signal_id, strategy_name, side, created_at),
        )
        self._conn.commit()

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
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO orders(
                local_order_id, strategy_name, exchange_order_id, side, order_type, price,
                size, status, created_at, filled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                local_order_id,
                strategy_name,
                exchange_order_id,
                side,
                order_type,
                price,
                size,
                status,
                created_at,
                filled_at,
            ),
        )
        self._conn.commit()

    def save_position_open(
        self,
        *,
        position_id: str,
        strategy_name: str,
        side: str,
        entry_price: float,
        entry_ts: str,
        size: float,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO positions(
                position_id, strategy_name, side, entry_price, entry_ts, size
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (position_id, strategy_name, side, entry_price, entry_ts, size),
        )
        self._conn.commit()

    def save_position_close(
        self,
        *,
        position_id: str,
        exit_price: float,
        exit_ts: str,
        exit_reason: str,
    ) -> None:
        self._conn.execute(
            """
            UPDATE positions
            SET exit_price = ?, exit_ts = ?, exit_reason = ?
            WHERE position_id = ?
            """,
            (exit_price, exit_ts, exit_reason, position_id),
        )
        self._conn.commit()

    def list_open_positions(
        self,
        *,
        strategy_name: str | None = None,
    ) -> list[sqlite3.Row]:
        if strategy_name is None:
            rows = self._conn.execute(
                """
                SELECT position_id, strategy_name, side, entry_price, entry_ts, size
                FROM positions
                WHERE exit_ts IS NULL
                ORDER BY entry_ts ASC
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT position_id, strategy_name, side, entry_price, entry_ts, size
                FROM positions
                WHERE exit_ts IS NULL AND strategy_name = ?
                ORDER BY entry_ts ASC
                """,
                (strategy_name,),
            ).fetchall()
        return list(rows)

    def close_open_position_reconciled(
        self,
        *,
        position_id: str,
        exit_ts: str,
        exit_reason: str,
    ) -> None:
        self._conn.execute(
            """
            UPDATE positions
            SET exit_price = entry_price, exit_ts = ?, exit_reason = ?
            WHERE position_id = ? AND exit_ts IS NULL
            """,
            (exit_ts, exit_reason, position_id),
        )
        self._conn.commit()

    def save_trade_result(self, result: TradeResult) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO trade_results(
                position_id, strategy_name, gross_pnl, fees, net_pnl, holding_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.position_id,
                result.strategy_name,
                result.gross_pnl,
                result.fees,
                result.net_pnl,
                result.holding_seconds,
            ),
        )
        self._conn.commit()

    def save_service_event(
        self,
        *,
        strategy_name: str = "system",
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
        level: str = "INFO",
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO service_events(ts, level, strategy_name, event_type, message, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                level,
                strategy_name,
                event_type,
                message,
                json.dumps(payload or {}),
            ),
        )
        self._conn.commit()

    def get_counts_summary(self) -> dict[str, int]:
        """Возвращает короткий summary записей для smoke-проверки."""
        tables = (
            "signals",
            "orders",
            "positions",
            "trade_results",
            "service_events",
            "strategies_registry",
            "strategy_commands",
        )
        summary: dict[str, int] = {}
        for table in tables:
            row = self._conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            summary[table] = int(row["c"]) if row else 0
        return summary

    def upsert_strategy_registry(
        self,
        *,
        strategy_name: str,
        inst_id: str,
        desired_state: str,
        runtime_state: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO strategies_registry(
                strategy_name, inst_id, desired_state, runtime_state, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (strategy_name, inst_id, desired_state, runtime_state, _utc_now()),
        )
        self._conn.commit()

    def set_strategy_runtime_state(self, *, strategy_name: str, runtime_state: str) -> None:
        self._conn.execute(
            """
            UPDATE strategies_registry
            SET runtime_state = ?, updated_at = ?
            WHERE strategy_name = ?
            """,
            (runtime_state, _utc_now(), strategy_name),
        )
        self._conn.commit()

    def set_strategy_desired_state(self, *, strategy_name: str, desired_state: str) -> None:
        self._conn.execute(
            """
            UPDATE strategies_registry
            SET desired_state = ?, updated_at = ?
            WHERE strategy_name = ?
            """,
            (desired_state, _utc_now(), strategy_name),
        )
        self._conn.commit()

    def list_strategies_registry(self) -> list[dict[str, str]]:
        rows = self._conn.execute(
            """
            SELECT strategy_name, inst_id, desired_state, runtime_state, updated_at
            FROM strategies_registry
            ORDER BY strategy_name
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def enqueue_strategy_command(
        self,
        *,
        strategy_name: str,
        command_type: str,
        command_mode: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO strategy_commands(strategy_name, command_type, command_mode, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (strategy_name, command_type, command_mode, _utc_now()),
        )
        self._conn.commit()

    def claim_pending_strategy_commands(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT id, strategy_name, command_type, command_mode, created_at
            FROM strategy_commands
            WHERE status = 'pending'
            ORDER BY id ASC
            """
        ).fetchall()
        command_list = [dict(r) for r in rows]
        if not command_list:
            return []
        ids = [int(c["id"]) for c in command_list]
        placeholders = ",".join(["?"] * len(ids))
        self._conn.execute(
            f"UPDATE strategy_commands SET status = 'processing' WHERE id IN ({placeholders})",
            ids,
        )
        self._conn.commit()
        return command_list

    def finish_strategy_command(
        self,
        *,
        command_id: int,
        status: str,
        error_text: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE strategy_commands
            SET status = ?, processed_at = ?, error_text = ?
            WHERE id = ?
            """,
            (status, _utc_now(), error_text, command_id),
        )
        self._conn.commit()
