-- =============================================================================
-- Патч: выравнивание старых таблиц (созданных вручную по скриншотам) с DDL 001.
--
-- Проблема: CREATE TABLE IF NOT EXISTS не добавляет новые колонки в существующие таблицы.
-- Симптом: ERROR column "strategy_name" does not exist при 002_indexes.
--
-- Если данных нет — проще: RESET=1 bash migrations/postgres/apply_all.sh
--
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/postgres/004_align_legacy_schema.sql
-- затем снова 002_hypertables_indexes.sql или 002_indexes_only.sql
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS okx_exec;

-- helper: add column if missing
CREATE OR REPLACE FUNCTION okx_exec._add_column_if_missing(
    p_table TEXT,
    p_column TEXT,
    p_definition TEXT
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'okx_exec'
          AND table_name = p_table
          AND column_name = p_column
    ) THEN
        EXECUTE format(
            'ALTER TABLE okx_exec.%I ADD COLUMN %I %s',
            p_table,
            p_column,
            p_definition
        );
    END IF;
END;
$$;

-- order_fills (часто без strategy_name в ручной схеме)
SELECT okx_exec._add_column_if_missing('order_fills', 'strategy_name', 'TEXT NOT NULL DEFAULT ''unknown''');
SELECT okx_exec._add_column_if_missing('order_fills', 'run_id', 'BIGINT');
SELECT okx_exec._add_column_if_missing('order_fills', 'raw_fill_json', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');

-- orders
SELECT okx_exec._add_column_if_missing('orders', 'strategy_name', 'TEXT NOT NULL DEFAULT ''unknown''');
SELECT okx_exec._add_column_if_missing('orders', 'parent_order_id_local', 'TEXT');
SELECT okx_exec._add_column_if_missing('orders', 'position_action', 'TEXT');
SELECT okx_exec._add_column_if_missing('orders', 'raw_request_json', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');
SELECT okx_exec._add_column_if_missing('orders', 'raw_response_json', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');

-- positions
SELECT okx_exec._add_column_if_missing('positions', 'strategy_name', 'TEXT NOT NULL DEFAULT ''unknown''');
SELECT okx_exec._add_column_if_missing('positions', 'model_name', 'TEXT');
SELECT okx_exec._add_column_if_missing('positions', 'status', 'TEXT NOT NULL DEFAULT ''open''');
SELECT okx_exec._add_column_if_missing('positions', 'qty_open', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('positions', 'updated_at', 'TIMESTAMPTZ NOT NULL DEFAULT now()');

-- trade_results
SELECT okx_exec._add_column_if_missing('trade_results', 'strategy_name', 'TEXT NOT NULL DEFAULT ''unknown''');
SELECT okx_exec._add_column_if_missing('trade_results', 'win_flag', 'BOOLEAN NOT NULL DEFAULT FALSE');
SELECT okx_exec._add_column_if_missing('trade_results', 'extra_json', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');

-- execution_attempts
SELECT okx_exec._add_column_if_missing('execution_attempts', 'strategy_name', 'TEXT NOT NULL DEFAULT ''unknown''');
SELECT okx_exec._add_column_if_missing('execution_attempts', 'request_payload', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');
SELECT okx_exec._add_column_if_missing('execution_attempts', 'response_payload', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');

-- reconciliation_events
SELECT okx_exec._add_column_if_missing('reconciliation_events', 'strategy_name', 'TEXT');

-- service_events
SELECT okx_exec._add_column_if_missing('service_events', 'strategy_name', 'TEXT NOT NULL DEFAULT ''system''');
SELECT okx_exec._add_column_if_missing('service_events', 'component', 'TEXT NOT NULL DEFAULT ''executor''');
SELECT okx_exec._add_column_if_missing('service_events', 'payload_json', 'JSONB NOT NULL DEFAULT ''{}''::jsonb');

-- strategy_signals: signal_id мог быть UUID — executor использует TEXT
-- (ручная миграция типов не делается автоматически; при несовпадении — reset)

DROP FUNCTION okx_exec._add_column_if_missing(TEXT, TEXT, TEXT);

\echo '004_align_legacy_schema: done. Re-run 002_indexes_only.sql or 002_hypertables_indexes.sql'
