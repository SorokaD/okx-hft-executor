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
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                payload TEXT
            );
            """
        )
        self._conn.commit()

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
                local_order_id, exchange_order_id, side, order_type, price,
                size, status, created_at, filled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                local_order_id,
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
        side: str,
        entry_price: float,
        entry_ts: str,
        size: float,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO positions(
                position_id, side, entry_price, entry_ts, size
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (position_id, side, entry_price, entry_ts, size),
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

    def save_trade_result(self, result: TradeResult) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO trade_results(
                position_id, gross_pnl, fees, net_pnl, holding_seconds
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                result.position_id,
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
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
        level: str = "INFO",
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO service_events(ts, level, event_type, message, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                level,
                event_type,
                message,
                json.dumps(payload or {}),
            ),
        )
        self._conn.commit()

    def get_counts_summary(self) -> dict[str, int]:
        """Возвращает короткий summary записей для smoke-проверки."""
        tables = ("signals", "orders", "positions", "trade_results", "service_events")
        summary: dict[str, int] = {}
        for table in tables:
            row = self._conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            summary[table] = int(row["c"]) if row else 0
        return summary
