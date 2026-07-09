# Baseline Demo MVP

Документ описывает рабочий MVP: случайная baseline-стратегия на **REST polling** выставляет maker **post-only** заявки на вход и выход, сопровождает позицию по TP/SL/timeout и пишет журнал в SQLite.

Первый запуск с нуля: **[getting_started.md](getting_started.md)**.

## Что уже работает

- baseline decision раз в 30 секунд (`strategy/random_baseline`);
- вход и выход через **post-only** лимитки (maker), перестановка по таймерам `OKX_MAKER_REPRICE_SEC` / `OKX_MAKER_MAX_WAIT_SEC`;
- локальный мониторинг TP/SL/timeout по последней цене тикера;
- cooldown после закрытия;
- при расхождении памяти и биржи: восстановление открытой позиции из snapshot `GET /account/positions` (событие `position_reconciled` в `service_events`);
- обработка части ошибок reduce-only при сверке (`exit_sync_lost`, закрытие с `sync_lost` при пустой позиции на бирже — см. код оркестратора);
- сохранение сигналов, ордеров, позиций, PnL и service events в SQLite.

## Быстрый запуск

1. Скопируйте `.env.example` в `.env` (см. [getting_started.md](getting_started.md)).
2. Для **реальной торговли на OKX** (demo или иначе): заполните `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE`, выставите `OKX_HFT_SAFE_MODE=0` и нужный `OKX_HFT_RUNTIME_MODE` / `OKX_ENABLE_REAL_OKX_IN_PAPER` по [таблице в getting_started.md](getting_started.md#stub-vs-okx-rest-reference).
3. Запустите:

```bash
python -m app.main
```

## Ключевые переменные окружения

Имена и значения по умолчанию — в `config/settings.py` и [.env.example](../.env.example). Кратко:

| Переменная | Смысл |
|------------|--------|
| `OKX_HFT_RUNTIME_MODE` | `live` / `paper` / `replay` — влияет на выбор клиента в `bootstrap` |
| `OKX_HFT_SAFE_MODE` | `1` — **всегда** stub, без сетевых ордеров |
| `OKX_ENABLE_REAL_OKX_IN_PAPER` | при `paper` и `0` — stub; при `paper` и `1` — реальный REST (если не мешает safe_mode) |
| `OKX_FLAG_DEMO` | заголовок demo для OKX API |
| `OKX_INST_ID` | например `BTC-USDT-SWAP` |
| `OKX_TD_MODE` | `cross` / `isolated` — как в кабинете OKX |
| `OKX_ORD_TYPE` | в MVP используется post-only maker-путь (`post_only`) |
| `OKX_ORDER_SIZE` | размер в контрактах (строка) |
| `OKX_LOOP_SLEEP_SEC` | пауза между итерациями главного цикла |
| `OKX_SQLITE_PATH` | путь к SQLite (по умолчанию `data/baseline_mvp.sqlite3`) |
| `OKX_HTTP_TIMEOUT_SEC` | таймаут HTTP к OKX |

## Как понять, что система торгует

По логам:

- `starting baseline executor`
- `strategy decided LONG/SHORT`
- `entry maker order submitted` / `entry order submitted` (формулировки в логах см. `app/orchestrator.py`)
- `position opened` (после fill входа)
- `tp` / `sl` / `timeout` и выход maker
- `position closed`

В SQLite (`OKX_SQLITE_PATH`):

- таблицы `signals`, `orders`, `positions`, `trade_results`, `service_events`;
- при восстановлении позиции после рестарта/рассинхрона: `position_reconciled`.

## Smoke-run (авто-остановка)

```bash
python -m app.main --run-seconds 60
```

или

```bash
python -m app.main --max-loops 120
```

После завершения приложение печатает summary:

```text
Run finished
signals: N
orders: N
positions: N
trade_results: N
service_events: N
```

## Быстрый check OKX без торговли

```bash
python -m app.main --check-okx
```

Команда проверяет:

- доступность account endpoint;
- доступность ticker;
- получение tick size.

## Три практичных сценария

### A) Локально без биржи (stub)

- `OKX_HFT_RUNTIME_MODE=paper`
- `OKX_HFT_SAFE_MODE=1` **или** `OKX_ENABLE_REAL_OKX_IN_PAPER=0`
- запуск: `python -m app.main --run-seconds 60`

Ожидание: цикл и SQLite работают, заявки на OKX не уходят.

### B) OKX demo с реальными заявками

- `OKX_FLAG_DEMO=1`
- валидные **demo** credentials
- **`OKX_HFT_SAFE_MODE=0`**
- либо `OKX_HFT_RUNTIME_MODE=live`, либо `paper` + `OKX_ENABLE_REAL_OKX_IN_PAPER=1`

Ожидание: HTTP к OKX, реальные post-only ордера на demo-счёте.

### C) Короткий smoke после правок кода

```bash
python -m app.main --max-loops 60
```

## Ограничения MVP

- только REST polling (без private/public WebSocket в этом контуре);
- один инструмент (`OKX_INST_ID`);
- комиссии в `trade_results`: `entry_fee`, `exit_fee`, `fees_total`, `net_pnl`; источник в `fee_source` (`okx_fill` / `estimated_config`);
- нет отдельного HTTP control plane в обязательном пути запуска (см. optional extra `control` в `pyproject.toml`).
