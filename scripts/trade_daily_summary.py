"""Print daily trade summary from okx_exec.v_trade_daily_summary."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

import psycopg

from config.settings import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily baseline trade summary from PostgreSQL")
    parser.add_argument("--strategy", default=None, help="Filter by strategy_name")
    parser.add_argument("--inst-id", default=None, help="Filter by inst_id")
    parser.add_argument("--run-id", type=int, default=None, help="Filter by run_id")
    parser.add_argument("--from-day", default=None, help="UTC day start YYYY-MM-DD")
    parser.add_argument("--to-day", default=None, help="UTC day end YYYY-MM-DD (inclusive)")
    args = parser.parse_args()

    settings = get_settings()
    dsn = settings.get_database_url()
    if not dsn:
        print("ERROR: postgres not configured")
        return 1

    schema = settings.postgres_schema
    clauses = ["1=1"]
    params: list[object] = []
    if args.strategy:
        clauses.append("strategy_name = %s")
        params.append(args.strategy)
    if args.inst_id:
        clauses.append("inst_id = %s")
        params.append(args.inst_id)
    if args.run_id is not None:
        clauses.append("run_id = %s")
        params.append(args.run_id)
    if args.from_day:
        clauses.append("trade_day >= %s::timestamptz")
        params.append(args.from_day)
    if args.to_day:
        clauses.append("trade_day <= %s::timestamptz")
        params.append(args.to_day)

    sql = f"""
        SELECT *
        FROM {schema}.v_trade_daily_summary
        WHERE {' AND '.join(clauses)}
        ORDER BY trade_day DESC, strategy_name, inst_id, run_id
    """

    with psycopg.connect(dsn) as conn:
        cur = conn.execute(sql, params)
        colnames = [d.name for d in cur.description]  # type: ignore[union-attr]
        rows = cur.fetchall()

    if not rows:
        print("No rows (apply migration 006 or wait for closed trades).")
        return 0

    print(f"trade_daily_summary @ {datetime.utcnow().isoformat()}Z")
    print("\t".join(colnames))
    for row in rows:
        print("\t".join(str(v) for v in row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
