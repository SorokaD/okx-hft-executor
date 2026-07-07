#!/usr/bin/env bash
# Применить все миграции okx_exec.
#
# Usage:
#   export DATABASE_URL='postgresql://executor_rw:PASSWORD@HOST:5432/okx_hft'
#   bash migrations/postgres/apply_all.sh
#
# Fresh install (УДАЛЯЕТ данные):
#   RESET=1 bash migrations/postgres/apply_all.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: set DATABASE_URL (postgresql://user:pass@host:port/dbname)" >&2
  exit 2
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql not found in PATH" >&2
  exit 2
fi

run_sql() {
  local file="$1"
  echo "==> Applying $(basename "$file")"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
}

if [[ "${RESET:-0}" == "1" ]]; then
  echo "WARNING: RESET=1 — dropping schema okx_exec"
  run_sql "$SCRIPT_DIR/000_reset_okx_exec.sql"
fi

run_sql "$SCRIPT_DIR/001_okx_exec_schema.sql"

if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -tAc "SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'" | grep -q 1; then
  echo "TimescaleDB detected"
  run_sql "$SCRIPT_DIR/002_hypertables_indexes.sql"
else
  echo "TimescaleDB not available — applying indexes only"
  run_sql "$SCRIPT_DIR/002_indexes_only.sql"
fi

run_sql "$SCRIPT_DIR/003_triggers.sql"

echo "OK: okx_exec schema ready"
