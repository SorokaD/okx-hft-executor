-- =============================================================================
-- 005: execution metrics + fee attribution on trade_results (idempotent)
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS okx_exec;

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

-- Fees
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_fee', 'NUMERIC(20, 8) NOT NULL DEFAULT 0');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_fee', 'NUMERIC(20, 8) NOT NULL DEFAULT 0');
SELECT okx_exec._add_column_if_missing('trade_results', 'fee_ccy', 'TEXT');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_liquidity', 'TEXT');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_liquidity', 'TEXT');
SELECT okx_exec._add_column_if_missing('trade_results', 'fee_source', 'TEXT NOT NULL DEFAULT ''missing''');
SELECT okx_exec._add_column_if_missing('trade_results', 'fee_status', 'TEXT NOT NULL DEFAULT ''pending''');
SELECT okx_exec._add_column_if_missing('trade_results', 'close_source', 'TEXT');

-- Entry execution quality
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_order_count', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_reprice_count', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_cancel_count', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_wait_sec', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_filled_px', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_first_px', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_last_px', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'entry_slippage_ticks', 'NUMERIC(20, 8)');

-- Exit execution quality
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_order_count', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_reprice_count', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_cancel_count', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_wait_sec', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_filled_px', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_first_px', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_last_px', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_slippage_ticks', 'NUMERIC(20, 8)');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_market_fallback_used', 'BOOLEAN NOT NULL DEFAULT FALSE');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_market_fallback_reason', 'TEXT');
SELECT okx_exec._add_column_if_missing('trade_results', 'exit_maker_attempts', 'INTEGER');
SELECT okx_exec._add_column_if_missing('trade_results', 'timeout_triggered', 'BOOLEAN NOT NULL DEFAULT FALSE');
SELECT okx_exec._add_column_if_missing('trade_results', 'final_exit_reason', 'TEXT');

CREATE INDEX IF NOT EXISTS idx_trade_results_strategy_close_source
    ON okx_exec.trade_results (strategy_name, close_source);

CREATE INDEX IF NOT EXISTS idx_trade_results_final_exit_reason
    ON okx_exec.trade_results (strategy_name, final_exit_reason);

DROP FUNCTION okx_exec._add_column_if_missing(TEXT, TEXT, TEXT);
