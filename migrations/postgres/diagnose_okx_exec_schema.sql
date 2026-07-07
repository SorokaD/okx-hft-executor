-- =============================================================================
-- Диагностика: сравнить фактические колонки с ожидаемой схемой okx_exec
--
-- psql "$DATABASE_URL" -f migrations/postgres/diagnose_okx_exec_schema.sql
-- =============================================================================

\echo '=== Tables in okx_exec ==='
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'okx_exec'
ORDER BY 1;

\echo ''
\echo '=== order_fills columns (ожидается strategy_name) ==='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'okx_exec' AND table_name = 'order_fills'
ORDER BY ordinal_position;

\echo ''
\echo '=== Missing strategy_name (должно быть пусто) ==='
SELECT t.table_name
FROM information_schema.tables t
WHERE t.table_schema = 'okx_exec'
  AND t.table_type = 'BASE TABLE'
  AND t.table_name IN (
      'order_fills', 'orders', 'positions', 'trade_results',
      'execution_attempts', 'strategy_signals', 'service_events'
  )
  AND NOT EXISTS (
      SELECT 1
      FROM information_schema.columns c
      WHERE c.table_schema = 'okx_exec'
        AND c.table_name = t.table_name
        AND c.column_name = 'strategy_name'
  );

\echo ''
\echo '=== Hypertables (Timescale) ==='
SELECT hypertable_schema, hypertable_name
FROM timescaledb_information.hypertables
WHERE hypertable_schema = 'okx_exec'
ORDER BY 1, 2;
