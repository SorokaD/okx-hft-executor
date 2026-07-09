-- =============================================================================
-- 006: daily trade summary view for baseline / ML comparison
-- =============================================================================

CREATE OR REPLACE VIEW okx_exec.v_trade_daily_summary AS
SELECT
    date_trunc('day', exit_ts AT TIME ZONE 'UTC') AS trade_day,
    strategy_name,
    run_id,
    inst_id,
    COUNT(*)::BIGINT AS trades_count,
    AVG(CASE WHEN gross_pnl > 0 THEN 1.0 ELSE 0.0 END) AS winrate_gross,
    AVG(CASE WHEN net_pnl > 0 THEN 1.0 ELSE 0.0 END) AS winrate_net,
    SUM(gross_pnl) AS gross_pnl_sum,
    SUM(net_pnl) AS net_pnl_sum,
    SUM(fees_total) AS total_fee_sum,
    AVG(fees_total) AS avg_fee_per_trade,
    AVG(holding_seconds) AS avg_hold_sec,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY holding_seconds) AS median_hold_sec,
    COUNT(*) FILTER (WHERE COALESCE(final_exit_reason, exit_reason) = 'tp') AS tp_count,
    COUNT(*) FILTER (WHERE COALESCE(final_exit_reason, exit_reason) = 'sl') AS sl_count,
    COUNT(*) FILTER (WHERE COALESCE(final_exit_reason, exit_reason) = 'timeout') AS timeout_count,
    COUNT(*) FILTER (WHERE exit_market_fallback_used IS TRUE) AS market_fallback_count,
    CASE
        WHEN COUNT(*) = 0 THEN 0
        ELSE COUNT(*) FILTER (WHERE exit_market_fallback_used IS TRUE)::NUMERIC / COUNT(*)
    END AS market_fallback_ratio,
    CASE
        WHEN COUNT(*) = 0 THEN 0
        ELSE COUNT(*) FILTER (WHERE entry_liquidity = 'maker')::NUMERIC / COUNT(*)
    END AS maker_entry_ratio,
    CASE
        WHEN COUNT(*) = 0 THEN 0
        ELSE COUNT(*) FILTER (WHERE exit_liquidity = 'maker')::NUMERIC / COUNT(*)
    END AS maker_exit_ratio,
    AVG(entry_wait_sec) AS avg_entry_wait_sec,
    AVG(exit_wait_sec) AS avg_exit_wait_sec,
    AVG(entry_reprice_count) AS avg_entry_reprice_count,
    AVG(exit_reprice_count) AS avg_exit_reprice_count
FROM okx_exec.trade_results
GROUP BY 1, 2, 3, 4;

COMMENT ON VIEW okx_exec.v_trade_daily_summary IS
    'Дневная аналитика по strategy_name/run_id/inst_id для сравнения baseline и ML.';
