# Аналитические SQL-запросы

Схема: `okx_exec`. Период и стратегию подставляйте в `WHERE`.

Переменные для примеров:

```sql
-- baseline на BTC swap, последние 7 дней
\set strategy 'random_baseline_v1'
\set inst 'BTC-USDT-SWAP'
```

## Обзор по стратегии

```sql
SELECT
    strategy_name,
    count(*) AS trades,
    sum(net_pnl) AS total_net_pnl,
    avg(net_pnl) AS avg_net_pnl,
    sum(CASE WHEN win_flag THEN 1 ELSE 0 END) AS wins,
    round(100.0 * avg(CASE WHEN win_flag THEN 1.0 ELSE 0.0 END), 2) AS win_rate_pct,
    avg(holding_seconds) AS avg_hold_sec
FROM okx_exec.trade_results
WHERE strategy_name = 'random_baseline_v1'
  AND exit_ts >= now() - interval '7 days'
GROUP BY strategy_name;
```

## Fill rate входов

```sql
SELECT
    strategy_name,
    count(*) FILTER (WHERE status = 'filled') AS filled,
    count(*) FILTER (WHERE status = 'canceled') AS canceled,
    count(*) FILTER (WHERE status = 'submitted') AS submitted,
    count(*) AS total_entry_orders,
    round(
        100.0 * count(*) FILTER (WHERE status = 'filled')
        / nullif(count(*), 0),
        2
    ) AS fill_rate_pct
FROM okx_exec.orders
WHERE strategy_name = 'random_baseline_v1'
  AND position_action = 'open'
  AND ts_created >= now() - interval '7 days'
GROUP BY strategy_name;
```

## Сигналы vs исполненные сделки

```sql
WITH sig AS (
    SELECT count(*) AS signals
    FROM okx_exec.strategy_signals
    WHERE strategy_name = 'random_baseline_v1'
      AND decision_type = 'entry'
      AND ts_decision >= now() - interval '7 days'
),
tr AS (
    SELECT count(*) AS trades
    FROM okx_exec.trade_results
    WHERE strategy_name = 'random_baseline_v1'
      AND exit_ts >= now() - interval '7 days'
)
SELECT signals, trades,
       round(100.0 * trades / nullif(signals, 0), 2) AS signal_to_trade_pct
FROM sig, tr;
```

## Почему ордера не сработали (execution_attempts)

```sql
SELECT
    action_type,
    status,
    error_code,
    count(*) AS cnt
FROM okx_exec.execution_attempts
WHERE strategy_name = 'random_baseline_v1'
  AND ts_event >= now() - interval '24 hours'
GROUP BY 1, 2, 3
ORDER BY cnt DESC;
```

## Ошибки OKX 50102 (время)

```sql
SELECT date_trunc('hour', ts_event) AS hour,
       count(*) AS errors
FROM okx_exec.execution_attempts
WHERE error_code = '50102'
   OR error_message ILIKE '%Timestamp request expired%'
GROUP BY 1
ORDER BY 1 DESC;
```

## Распределение exit_reason

```sql
SELECT exit_reason, count(*), avg(net_pnl), sum(net_pnl)
FROM okx_exec.trade_results
WHERE strategy_name = 'random_baseline_v1'
  AND exit_ts >= now() - interval '30 days'
GROUP BY exit_reason
ORDER BY count(*) DESC;
```

## Reprice: сколько ордеров на один сигнал

```sql
SELECT signal_id, count(*) AS order_rows,
       count(*) FILTER (WHERE status = 'canceled') AS canceled,
       count(*) FILTER (WHERE status = 'filled') AS filled
FROM okx_exec.orders
WHERE signal_id IS NOT NULL
  AND strategy_name = 'random_baseline_v1'
  AND ts_created >= now() - interval '7 days'
GROUP BY signal_id
HAVING count(*) > 1
ORDER BY order_rows DESC
LIMIT 20;
```

## Сравнение двух стратегий (baseline vs model)

```sql
SELECT
    strategy_name,
    count(*) AS trades,
    sum(net_pnl) AS net_pnl,
    avg(holding_seconds) AS avg_hold
FROM okx_exec.trade_results
WHERE inst_id = 'BTC-USDT-SWAP'
  AND exit_ts >= now() - interval '30 days'
  AND strategy_name IN ('random_baseline_v1', 'mean_reversion_v1')
GROUP BY strategy_name
ORDER BY strategy_name;
```

## Открытые позиции (журнал)

```sql
SELECT position_id, strategy_name, side, entry_price, entry_ts,
       now() - entry_ts AS age
FROM okx_exec.positions
WHERE status = 'open'
ORDER BY entry_ts;
```

## Reconciliation за сутки

```sql
SELECT mismatch_type, resolution_status, count(*)
FROM okx_exec.reconciliation_events
WHERE ts_event >= now() - interval '1 day'
GROUP BY 1, 2;
```

## Maker vs taker (когда появятся fills)

```sql
SELECT liquidity_side, count(*), sum(fee) AS total_fees
FROM okx_exec.order_fills
WHERE strategy_name = 'random_baseline_v1'
  AND ts_fill >= now() - interval '7 days'
GROUP BY liquidity_side;
```

## По run_id (один деплой)

```sql
SELECT r.run_id, r.started_at, r.finished_at, r.stop_reason,
       (SELECT count(*) FROM okx_exec.trade_results t WHERE t.run_id = r.run_id) AS trades
FROM okx_exec.executor_runs r
WHERE r.strategy_name = 'random_baseline_v1'
ORDER BY r.started_at DESC
LIMIT 10;
```

## SQLite (пока PG пустой)

Аналог fill rate на VPS:

```sql
SELECT status, count(*) FROM orders GROUP BY status;
```

Через docker — см. [sqlite_mvp.md](sqlite_mvp.md).
