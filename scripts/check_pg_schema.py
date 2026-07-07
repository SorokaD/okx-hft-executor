"""Quick check: PostgreSQL connection and okx_exec schema."""
from __future__ import annotations

from config.settings import get_settings
import psycopg


def main() -> None:
    settings = get_settings()
    dsn = settings.get_database_url()
    if not dsn:
        print("postgres: not configured")
        return
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT current_database(), current_setting('search_path')"
        ).fetchone()
        print(f"connected db={row[0]} search_path={row[1]}")
        schema = conn.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'okx_exec'"
        ).fetchone()
        print(f"okx_exec schema exists: {bool(schema)}")
        count = conn.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'okx_exec'
            """
        ).fetchone()[0]
        print(f"okx_exec tables: {count}")
        runs = conn.execute(
            """
            SELECT table_schema, table_name FROM information_schema.tables
            WHERE table_name = 'executor_runs'
            """
        ).fetchall()
        print(f"executor_runs locations: {runs}")


if __name__ == "__main__":
    main()
