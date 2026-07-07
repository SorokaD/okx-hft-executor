"""Apply okx_exec migrations via psycopg (no psql required)."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from config.settings import get_settings

_ROOT = Path(__file__).resolve().parent.parent
_FILES = (
    _ROOT / "migrations/postgres/001_okx_exec_schema.sql",
    _ROOT / "migrations/postgres/002_indexes_only.sql",
    _ROOT / "migrations/postgres/003_triggers.sql",
)


def main() -> int:
    settings = get_settings()
    dsn = settings.get_database_url()
    if not dsn:
        print("ERROR: postgres not configured in .env")
        return 1
    with psycopg.connect(dsn, autocommit=True) as conn:
        for path in _FILES:
            print(f"applying {path.name}...")
            conn.execute(path.read_text(encoding="utf-8"))
            print("  ok")
        row = conn.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'okx_exec'
            """
        ).fetchone()
        print(f"okx_exec tables: {row[0] if row else 0}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
