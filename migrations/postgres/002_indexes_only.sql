-- =============================================================================
-- Только схема + индексы БЕЗ TimescaleDB (если extension недоступен).
-- Вместо 002_hypertables_indexes.sql
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_executor_runs_strategy_started
    ON okx_exec.executor_runs (strategy_name, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_signals_strategy_ts
    ON okx_exec.strategy_signals (strategy_name, ts_decision DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_signals_inst_ts
    ON okx_exec.strategy_signals (inst_id, ts_decision DESC);

CREATE INDEX IF NOT EXISTS idx_execution_attempts_strategy_ts
    ON okx_exec.execution_attempts (strategy_name, ts_event DESC);

CREATE INDEX IF NOT EXISTS idx_execution_attempts_signal
    ON okx_exec.execution_attempts (signal_id, ts_event DESC);

CREATE INDEX IF NOT EXISTS idx_execution_attempts_action_status
    ON okx_exec.execution_attempts (action_type, status, ts_event DESC);

CREATE INDEX IF NOT EXISTS idx_orders_strategy_ts
    ON okx_exec.orders (strategy_name, ts_created DESC);

CREATE INDEX IF NOT EXISTS idx_orders_signal
    ON okx_exec.orders (signal_id, ts_created DESC);

CREATE INDEX IF NOT EXISTS idx_orders_status_strategy
    ON okx_exec.orders (status, strategy_name, ts_created DESC);

CREATE INDEX IF NOT EXISTS idx_orders_exchange_ord
    ON okx_exec.orders (order_id_exchange)
    WHERE order_id_exchange IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_cl_ord_id
    ON okx_exec.orders (cl_ord_id)
    WHERE cl_ord_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_order_fills_strategy_ts
    ON okx_exec.order_fills (strategy_name, ts_fill DESC);

CREATE INDEX IF NOT EXISTS idx_order_fills_order_local
    ON okx_exec.order_fills (order_id_local, ts_fill DESC);

CREATE INDEX IF NOT EXISTS idx_positions_strategy_status
    ON okx_exec.positions (strategy_name, status, entry_ts DESC);

CREATE INDEX IF NOT EXISTS idx_positions_inst_open
    ON okx_exec.positions (inst_id, status)
    WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_trade_results_strategy_exit
    ON okx_exec.trade_results (strategy_name, exit_ts DESC);

CREATE INDEX IF NOT EXISTS idx_trade_results_inst_exit
    ON okx_exec.trade_results (inst_id, exit_ts DESC);

CREATE INDEX IF NOT EXISTS idx_reconciliation_strategy_ts
    ON okx_exec.reconciliation_events (strategy_name, ts_event DESC);

CREATE INDEX IF NOT EXISTS idx_service_events_strategy_ts
    ON okx_exec.service_events (strategy_name, ts_event DESC);

CREATE INDEX IF NOT EXISTS idx_service_events_type_ts
    ON okx_exec.service_events (event_type, ts_event DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_commands_pending
    ON okx_exec.strategy_commands (status, created_at)
    WHERE status IN ('pending', 'processing');
