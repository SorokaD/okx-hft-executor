# Baseline Demo MVP

Документ описывает рабочий MVP: случайная baseline-стратегия открывает и закрывает сделки на OKX demo.

## Что уже работает

- baseline decision раз в 30 секунд;
- вход market order в OKX demo;
- локальный мониторинг TP/SL/timeout;
- выход market order;
- cooldown 20 секунд после закрытия;
- сохранение сигналов, ордеров, позиций, PnL и service events в SQLite.

## Быстрый запуск

1. Скопируйте `.env.example` в `.env`.
2. Заполните `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE`.
3. Убедитесь, что `OKX_FLAG_DEMO=1`.
4. Запустите:

```bash
python -m app.main
```

## Ключевые env

- `OKX_HFT_SAFE_MODE=1` — безопасный paper-run без реальных ордеров;
- `OKX_ENABLE_REAL_OKX_IN_PAPER=0` — по умолчанию paper использует stub-клиент;
- `OKX_INST_ID=BTC-USDT-SWAP`
- `OKX_ORDER_SIZE=1`
- `OKX_TD_MODE=cross`
- `OKX_ORD_TYPE=market`
- `OKX_LOOP_SLEEP_SEC=1`
- `OKX_SQLITE_PATH=data/baseline_mvp.sqlite3`

## Как понять, что система торгует

По логам:

- `strategy decided LONG/SHORT`
- `entry order submitted`
- `position opened`
- `tp/sl/timeout triggered`
- `position closed`

В SQLite (`OKX_SQLITE_PATH`):

- таблицы `signals`, `orders`, `positions`, `trade_results`, `service_events`.

## Smoke-run (авто-остановка)

Для короткой проверки запуска:

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

### A) Safe paper локально

- `OKX_HFT_RUNTIME_MODE=paper`
- `OKX_HFT_SAFE_MODE=1`
- запуск: `python -m app.main --run-seconds 60`

Ожидание: loop, логи, SQLite и service events работают без реальных заявок.

### B) Demo запуск в OKX

- `OKX_HFT_RUNTIME_MODE=live`
- `OKX_FLAG_DEMO=1`
- валидные demo credentials

Ожидание: сервис реально отправляет ордера в OKX demo.

### C) Короткий smoke test

- любой режим
- `python -m app.main --max-loops 60`

Ожидание: быстрый прогон после изменений с итоговым summary.

## Ограничения MVP

- только REST polling (без private/public ws);
- только один инструмент;
- market-only вход/выход;
- комиссии пока сохраняются как `0.0`.

