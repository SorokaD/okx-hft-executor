-- =============================================================================
-- OKX HFT Executor — схема аналитики и журнала исполнения (PostgreSQL + TimescaleDB)
--
-- Схема: okx_exec
-- ID: TEXT для executor (rb-*, exit-*, pos-*), UUID где указано явно.
--
-- Порядок применения:
--   001_okx_exec_schema.sql
--   002_hypertables_indexes.sql
--   003_triggers.sql
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS okx_exec;

-- ---------------------------------------------------------------------------
-- Control plane (сейчас дублируется в SQLite на VPS; в PG — для аналитики/ops)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.strategies_registry (
    strategy_name   TEXT        PRIMARY KEY,
    inst_id         TEXT        NOT NULL,
    desired_state   TEXT        NOT NULL CHECK (desired_state IN ('enabled', 'disabled')),
    runtime_state   TEXT        NOT NULL CHECK (runtime_state IN ('running', 'stopped', 'error')),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE okx_exec.strategies_registry IS
    'Реестр стратегий: желаемое и фактическое runtime-состояние.';

CREATE TABLE IF NOT EXISTS okx_exec.strategy_commands (
    command_id      BIGSERIAL   PRIMARY KEY,
    strategy_name   TEXT        NOT NULL,
    command_type    TEXT        NOT NULL,
    command_mode    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    error_text      TEXT
);

COMMENT ON TABLE okx_exec.strategy_commands IS
    'Очередь команд control-api (enable/disable/restart).';

-- ---------------------------------------------------------------------------
-- Запуск процесса executor
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.executor_runs (
    run_id              BIGSERIAL   PRIMARY KEY,
    run_uuid            UUID        NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    runtime_mode        TEXT        NOT NULL,
    environment_name    TEXT,
    host_name           TEXT,
    process_id          INTEGER,
    app_version         TEXT,
    strategy_name       TEXT,
    model_name          TEXT,
    inst_id             TEXT,
    status              TEXT        NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'stopped', 'error', 'draining')),
    stop_reason         TEXT,
    extra_json          JSONB       NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE okx_exec.executor_runs IS
    'Запуски процесса executor: аудит, группировка событий по run.';

-- ---------------------------------------------------------------------------
-- Решения стратегии
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.strategy_signals (
    signal_id           TEXT        NOT NULL,
    run_id              BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    ts_decision         TIMESTAMPTZ NOT NULL DEFAULT now(),
    strategy_name       TEXT        NOT NULL,
    model_name          TEXT,
    inst_id             TEXT        NOT NULL,
    side                TEXT        NOT NULL CHECK (side IN ('long', 'short', 'buy', 'sell')),
    decision_type       TEXT        NOT NULL DEFAULT 'entry'
        CHECK (decision_type IN ('entry', 'exit', 'skip', 'flatten')),
    confidence_score    NUMERIC(20, 8),
    take_profit_ticks   INTEGER,
    stop_loss_ticks     INTEGER,
    timeout_sec         INTEGER,
    market_snapshot     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    features_json       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    reason_code         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ts_decision, signal_id)
);

COMMENT ON TABLE okx_exec.strategy_signals IS
    'Сигналы стратегии: бизнес-решение открыть/закрыть/не открывать позицию.';

-- ---------------------------------------------------------------------------
-- Попытки действий executor (центр аналитики submit/skip/error)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.execution_attempts (
    attempt_id          BIGSERIAL   NOT NULL,
    attempt_uuid        UUID        NOT NULL DEFAULT gen_random_uuid(),
    run_id              BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    signal_id           TEXT,
    ts_event            TIMESTAMPTZ NOT NULL DEFAULT now(),
    inst_id             TEXT        NOT NULL,
    strategy_name       TEXT        NOT NULL,
    action_type         TEXT        NOT NULL,
    side                TEXT,
    status              TEXT        NOT NULL,
    skip_reason         TEXT,
    reject_reason       TEXT,
    error_code          TEXT,
    error_message       TEXT,
    request_payload     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    response_payload    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_event, attempt_id)
);

COMMENT ON TABLE okx_exec.execution_attempts IS
    'Попытки действий executor: submit, cancel, skip, reconcile, API error.';

-- ---------------------------------------------------------------------------
-- Ордера (каждый submit/reprice — отдельная строка; без UPDATE поверх истории)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.orders (
    order_pk            BIGSERIAL   NOT NULL,
    order_id_local      TEXT        NOT NULL,
    run_id              BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    signal_id           TEXT,
    attempt_id          BIGINT,
    position_id         TEXT,
    trade_id            TEXT,
    inst_id             TEXT        NOT NULL,
    strategy_name       TEXT        NOT NULL,
    exchange_name       TEXT        NOT NULL DEFAULT 'okx',
    order_id_exchange   TEXT,
    cl_ord_id           TEXT,
    parent_order_id_local TEXT,
    side                TEXT        NOT NULL CHECK (side IN ('buy', 'sell')),
    position_action     TEXT        CHECK (position_action IN ('open', 'close', 'reduce', 'unknown')),
    ord_type            TEXT        NOT NULL,
    td_mode             TEXT,
    pos_side            TEXT,
    reduce_only         BOOLEAN     NOT NULL DEFAULT FALSE,
    price               NUMERIC(20, 8),
    size                NUMERIC(20, 8) NOT NULL,
    filled_size         NUMERIC(20, 8) NOT NULL DEFAULT 0,
    avg_fill_price      NUMERIC(20, 8),
    status              TEXT        NOT NULL,
    exchange_code       TEXT,
    exchange_message    TEXT,
    ts_created          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ts_submitted        TIMESTAMPTZ,
    ts_ack              TIMESTAMPTZ,
    ts_first_fill       TIMESTAMPTZ,
    ts_last_fill        TIMESTAMPTZ,
    ts_canceled         TIMESTAMPTZ,
    ts_closed           TIMESTAMPTZ,
    raw_request_json    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    raw_response_json   JSONB       NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_created, order_pk),
    CONSTRAINT uq_orders_local_id UNIQUE (ts_created, order_id_local)
);

COMMENT ON TABLE okx_exec.orders IS
    'Ордера на бирже: полный жизненный цикл; reprice = новая строка.';

-- ---------------------------------------------------------------------------
-- Исполнения (fills)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.order_fills (
    fill_pk             BIGSERIAL   NOT NULL,
    fill_id_exchange    TEXT        NOT NULL,
    order_pk            BIGINT,
    order_id_local      TEXT,
    order_id_exchange   TEXT,
    run_id              BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    inst_id             TEXT        NOT NULL,
    strategy_name       TEXT        NOT NULL,
    side                TEXT        NOT NULL,
    fill_price          NUMERIC(20, 8) NOT NULL,
    fill_size           NUMERIC(20, 8) NOT NULL,
    fill_notional       NUMERIC(20, 8),
    liquidity_side      TEXT,
    fee                 NUMERIC(20, 8),
    fee_ccy             TEXT,
    pnl_realized_exchange NUMERIC(20, 8),
    ts_fill             TIMESTAMPTZ NOT NULL,
    raw_fill_json       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_fill, fill_pk),
    CONSTRAINT uq_order_fills_exchange UNIQUE (ts_fill, fill_id_exchange, inst_id)
);

COMMENT ON TABLE okx_exec.order_fills IS
    'Фактические исполнения ордеров: fees, maker/taker, точный PnL.';

-- ---------------------------------------------------------------------------
-- Позиции
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.positions (
    position_id             TEXT        PRIMARY KEY,
    run_id                  BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    inst_id                 TEXT        NOT NULL,
    strategy_name           TEXT        NOT NULL,
    model_name              TEXT,
    side                    TEXT        NOT NULL CHECK (side IN ('long', 'short')),
    status                  TEXT        NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'closed', 'reconciled', 'sync_lost')),
    qty                     NUMERIC(20, 8) NOT NULL,
    qty_open                NUMERIC(20, 8) NOT NULL,
    entry_signal_id         TEXT,
    entry_order_id_local    TEXT,
    exit_order_id_local     TEXT,
    entry_price             NUMERIC(20, 8),
    exit_price              NUMERIC(20, 8),
    take_profit_ticks       INTEGER,
    stop_loss_ticks         INTEGER,
    timeout_sec             INTEGER,
    max_favorable_price     NUMERIC(20, 8),
    max_adverse_price       NUMERIC(20, 8),
    mfe_ticks               NUMERIC(20, 8),
    mae_ticks               NUMERIC(20, 8),
    entry_ts                TIMESTAMPTZ,
    exit_ts                 TIMESTAMPTZ,
    exit_reason             TEXT,
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE okx_exec.positions IS
    'Локальное состояние позиции: lifecycle, MFE/MAE, связь с сигналами/ордерами.';

-- ---------------------------------------------------------------------------
-- Итог сделки
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.trade_results (
    trade_id                TEXT        PRIMARY KEY,
    run_id                  BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    position_id             TEXT        NOT NULL REFERENCES okx_exec.positions (position_id),
    inst_id                 TEXT        NOT NULL,
    strategy_name           TEXT        NOT NULL,
    model_name              TEXT,
    side                    TEXT        NOT NULL,
    entry_signal_id         TEXT,
    entry_order_id_local    TEXT,
    exit_order_id_local     TEXT,
    entry_price             NUMERIC(20, 8) NOT NULL,
    exit_price              NUMERIC(20, 8) NOT NULL,
    qty                     NUMERIC(20, 8) NOT NULL,
    gross_pnl               NUMERIC(20, 8) NOT NULL DEFAULT 0,
    fees_total              NUMERIC(20, 8) NOT NULL DEFAULT 0,
    funding_total           NUMERIC(20, 8) NOT NULL DEFAULT 0,
    slippage_total          NUMERIC(20, 8) NOT NULL DEFAULT 0,
    net_pnl                 NUMERIC(20, 8) NOT NULL DEFAULT 0,
    holding_seconds         NUMERIC(20, 8),
    entry_ts                TIMESTAMPTZ NOT NULL,
    exit_ts                 TIMESTAMPTZ NOT NULL,
    exit_reason             TEXT,
    win_flag                BOOLEAN     NOT NULL DEFAULT FALSE,
    extra_json              JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE okx_exec.trade_results IS
    'Итог завершённой сделки: PnL, fees, holding time, exit reason.';

-- ---------------------------------------------------------------------------
-- Reconciliation
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.reconciliation_events (
    reconciliation_id   BIGSERIAL   NOT NULL,
    run_id              BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    ts_event            TIMESTAMPTZ NOT NULL DEFAULT now(),
    inst_id             TEXT        NOT NULL,
    strategy_name       TEXT,
    severity            TEXT        NOT NULL DEFAULT 'info',
    mismatch_type       TEXT        NOT NULL,
    local_entity_type   TEXT,
    local_entity_id     TEXT,
    exchange_entity_id  TEXT,
    resolution_status   TEXT        NOT NULL DEFAULT 'detected',
    message             TEXT,
    payload_json        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_event, reconciliation_id)
);

COMMENT ON TABLE okx_exec.reconciliation_events IS
    'Сверка локального состояния executor с биржей.';

-- ---------------------------------------------------------------------------
-- Service events (аудит; торговые действия — в execution_attempts)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS okx_exec.service_events (
    event_id            BIGSERIAL   NOT NULL,
    event_uuid          UUID        NOT NULL DEFAULT gen_random_uuid(),
    run_id              BIGINT      REFERENCES okx_exec.executor_runs (run_id),
    ts_event            TIMESTAMPTZ NOT NULL DEFAULT now(),
    severity            TEXT        NOT NULL DEFAULT 'info',
    component           TEXT        NOT NULL DEFAULT 'executor',
    event_type          TEXT        NOT NULL,
    strategy_name       TEXT        NOT NULL DEFAULT 'system',
    inst_id             TEXT,
    signal_id           TEXT,
    attempt_id          BIGINT,
    position_id         TEXT,
    trade_id            TEXT,
    message             TEXT        NOT NULL,
    payload_json        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_event, event_id)
);

COMMENT ON TABLE okx_exec.service_events IS
    'Сервисные события: аудит, диагностика, расследование.';
