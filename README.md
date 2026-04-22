# okx-hft-executor

Рабочий baseline MVP для OKX (в т.ч. demo): стратегия принимает решение, выставляет **maker post-only** вход/выход, сопровождает позицию по TP/SL/timeout и пишет журнал в SQLite.

## С нуля до запущенного процесса

**Пошаговый гайд (окружение, `.env`, когда идут реальные запросы к OKX, команды, проверка, типовые сбои):** [docs/getting_started.md](docs/getting_started.md).

## Роль в системе

- Принимает или участвует в расчёте торговых сигналов (`strategy`).
- Проверяет ограничения и guard-ы (`risk`).
- Управляет жизненным циклом заявок и позиции (`execution`).
- Общается с биржей через изолированный слой (`exchange`).
- Пишет журнал и снимки состояния (`persistence`).
- Считает PnL, комиссии, качество исполнения (`accounting`).
- Обеспечивает наблюдаемость и операционные хуки (`observability`, `control`).

Подробные принципы и границы репозитория: [docs/architecture.md](docs/architecture.md).  

## High-level архитектура

```mermaid
flowchart TB
  subgraph ingress [Вход]
    S[strategy]
  end
  subgraph core [Ядро]
    R[risk]
    E[execution]
  end
  subgraph ports [Порты]
    X[exchange]
    P[persistence]
    O[observability]
  end
  S --> R
  R --> E
  E --> X
  E --> P
  E --> O
```

- **Domain-first**: язык системы зафиксирован в `domain/` (сигнал, ордер, fill, позиция, PnL-снимок, риск-событие, рынок).
- **Режимы** live / paper / replay подключаются подменой реализаций портов в `app/bootstrap.py`, а не ветвлением по всему коду ([docs/runtime_modes.md](docs/runtime_modes.md)).
- **Reconciliation** — обязательная часть устойчивого исполнения ([docs/reconciliation.md](docs/reconciliation.md)).

## Основные блоки

| Пакет | Назначение |
|-------|------------|
| [app](app/README.md) | Точка входа, bootstrap, оркестрация |
| [config](config/README.md) | Настройки и лимиты |
| [domain](domain/README.md) | Модели, enum, события, value objects |
| [strategy](strategy/README.md) | Сигналы, вход/выход, фильтры режима |
| [execution](execution/README.md) | Движок, менеджеры, state machine, reconciliation |
| [risk](risk/README.md) | Pre-trade, runtime, kill switch, guards |
| [exchange](exchange/README.md) | Порты и OKX-адаптеры |
| [persistence](persistence/README.md) | Репозитории, unit of work |
| [accounting](accounting/README.md) | PnL, fees, funding, execution quality |
| [services](services/README.md) | Clock, id, health helpers |
| [observability](observability/README.md) | Логи, метрики, tracing, алерты |
| [control](control/README.md) | Health / операционные хуки |
| [docs](docs/architecture.md) | Архитектура и процессы |
| [tests](tests/README.md) | unit / integration / replay |

## Как читать структуру

1. [docs/project_structure.md](docs/project_structure.md) — дерево каталогов.
2. [docs/trade_lifecycle.md](docs/trade_lifecycle.md) — цепочка от сигнала до persistence и reconciliation.
3. README в корне каждого пакета — границы ответственности и анти-паттерны.

## Что работает сейчас (MVP)

- baseline strategy (`strategy/random_baseline`) с decision step 30 сек;
- интеграция с OKX v5 REST (`exchange/okx/rest_client.py`), при необходимости — заглушка (`stub_client`);
- вход и выход **post-only (maker)** с перестановкой по bid/ask;
- локальный контроль выхода по TP/SL/timeout;
- cooldown после закрытия;
- сверка позиции с биржей при расхождении (см. [docs/reconciliation.md](docs/reconciliation.md) и событие `position_reconciled` в SQLite);
- persistence в SQLite (`signals`, `orders`, `positions`, `trade_results`, `service_events`).

Подробно: [docs/baseline_demo_mvp.md](docs/baseline_demo_mvp.md).

## Локальный запуск (кратко)

Полная инструкция: [docs/getting_started.md](docs/getting_started.md).

**Windows (PowerShell):**

```powershell
cd D:\path\to\okx-hft-executor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
# настройте .env (см. getting_started.md: safe_mode vs реальный OKX)
python -m app.main
```

**Linux / macOS:**

```bash
cd okx-hft-executor
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m app.main
```

Остановить интерактивный запуск: `Ctrl+C`.

Короткий smoke-run с авто-остановкой:

```bash
python -m app.main --run-seconds 60
# или
python -m app.main --max-loops 120
```

Проверка OKX API без запуска торгового цикла:

```bash
python -m app.main --check-okx
```

Разработка с линтерами и тестами:

```bash
pip install -e ".[dev]"
pytest tests/ -q
# опционально: make test (Unix) или команды из Makefile вручную на Windows
```

## Переменные окружения

Шаблон со всеми именами: [.env.example](.env.example). Секреты не коммитить.

Критично для поведения «реальные ордера / заглушка»:

- `OKX_HFT_RUNTIME_MODE` — `live` | `paper` | `replay`
- `OKX_HFT_SAFE_MODE` — при `1` всегда заглушка, без HTTP к бирже по ордерам
- `OKX_ENABLE_REAL_OKX_IN_PAPER` — при `paper` и `0` используется заглушка (если не включён safe_mode выше)

Таблица режимов и примеры: [docs/getting_started.md](docs/getting_started.md#stub-vs-okx-rest-reference).

Поведение baseline и логи: [docs/baseline_demo_mvp.md](docs/baseline_demo_mvp.md).
