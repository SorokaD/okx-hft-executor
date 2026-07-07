# Обзор хранения данных

## Зачем две базы

```mermaid
flowchart TB
  subgraph executor [Executor process]
    OR[orchestrator]
    SM[strategy_manager]
    CA[control-api]
  end
  subgraph sqlite [SQLite на VPS / локально]
    SQ[(baseline_mvp.sqlite3)]
  end
  subgraph pg [PostgreSQL / TimescaleDB]
    PG[(okx_exec schema)]
  end
  OR --> SQ
  SM --> SQ
  CA --> SQ
  OR -.->|планируется| PG
```

| | SQLite | PostgreSQL `okx_exec` |
|--|--------|------------------------|
| **Где** | Файл `data/baseline_mvp.sqlite3` (Docker: `/app/data/`) | Сервер TimescaleDB (отдельный хост) |
| **Зачем** | Быстрый ops-журнал, очередь команд control-api, smoke-run | Полная аналитика, сравнение стратегий, аудит |
| **Объём** | Малый, один файл на VPS | Растёт со временем, hypertables |
| **Кто пишет** | `SqliteMvpStore` в `persistence/sqlite_store.py` | `PostgresStore` — **в разработке** |
| **Кто читает** | control-api, ручная диагностика на VPS | Superset/Grafana/ноутбуки, отчёты |

SQLite **не заменяется** сразу: на VPS control-api и strategy manager завязаны на локальный файл. PostgreSQL — **источник правды для аналитики**, когда dual-write будет подключён.

## Схема PostgreSQL

- Имя схемы: **`okx_exec`**
- Имя БД (пример): **`okx_hft`**
- Расширение: **TimescaleDB** (hypertables по времени для высокочастотных таблиц)

Полный справочник таблиц: [okx_exec_schema.md](okx_exec_schema.md).

## Идентификаторы (важно для JOIN)

Executor генерирует строковые id с префиксом (`services/id_generation.py`):

| Префикс | Пример | Сущность |
|---------|--------|----------|
| `rb-` | `rb-a1b2c3…` | signal (random baseline) |
| `exit-` / `exit-mkt-` | `exit-…` | exit order client id |
| `pos-` | `pos-…` | position (открыта executor) |
| `pos-ex-` | `pos-ex-{okx_pos_id}` | position (восстановлена с биржи) |

В PostgreSQL поля `signal_id`, `position_id`, `order_id_local`, `trade_id` — тип **`TEXT`**, не UUID.

Отдельно:

- `run_id` — `BIGINT`, суррогатный ключ запуска процесса
- `run_uuid`, `attempt_uuid`, `event_uuid` — UUID для глобальной уникальности

## Группировка по стратегии

Каждая торговая таблица содержит как минимум:

- `strategy_name` — например `random_baseline_v1`, `mean_reversion_v1`
- `inst_id` — например `BTC-USDT-SWAP`
- `run_id` — привязка к конкретному запуску после рестарта/деплоя

Сравнение baseline vs модели = фильтр `WHERE strategy_name = '…'` + одинаковый `inst_id` и период.

## Принципы проектирования PG-схемы

1. **Append-only для ордеров** — reprice создаёт **новую строку** в `orders`, старая остаётся со статусом `canceled`. Не повторять ошибку SQLite `INSERT OR REPLACE`.
2. **`execution_attempts`** — каждая попытка submit/cancel/skip/API error. Ответ на вопрос «почему ордер не сработал».
3. **`service_events`** — аудит, не дублировать сюда всё из attempts.
4. **Exchange as source of truth** — расхождения в `reconciliation_events`.
5. **Hypertables** — time-series таблицы партиционируются по `ts_*` для масштабирования.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `OKX_SQLITE_PATH` | Путь к SQLite (см. `.env.example`) |
| `DATABASE_URL` | PostgreSQL connection string (для миграций и будущего `PostgresStore`) |

Пример `DATABASE_URL`:

```text
postgresql://executor_rw:PASSWORD@HOST:5432/okx_hft
```

Секреты — только в `.env` на сервере, не в git.

## Дорожная карта persistence

1. ✅ DDL `migrations/postgres/*`
2. ⬜ `PostgresStore` + dual-write из orchestrator
3. ⬜ Запись `order_fills` из OKX REST/WS
4. ⬜ Fees/funding в `trade_results`
5. ⬜ Materialized views / дашборды
