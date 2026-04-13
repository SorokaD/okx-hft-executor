# Дерево проекта

Актуальная схема каталогов (имена на английском; документация — на русском). При добавлении значимых пакетов этот файл следует обновлять.

```
okx-hft-executor/
├── README.md
├── pyproject.toml
├── Makefile
├── .env.example
├── .gitignore
│
├── app/                      # Точка входа, bootstrap, оркестрация run-loop
├── config/                   # Настройки pydantic-settings, лимиты, профили
├── domain/                   # Домен: модели, enum, события, value objects
│   ├── models/
│   ├── enums/
│   ├── events/
│   └── value_objects/
├── strategy/                 # Сигналы, вход/выход, фильтры режима
├── execution/                # Движок исполнения, менеджеры, reconciliation, state machine
├── risk/                     # Pre-trade / runtime risk, kill switch, guards
├── exchange/                 # Порты + реализация OKX (REST, WS, auth, rate limit)
│   └── okx/
├── persistence/              # Репозитории, unit of work, storage-модели
├── accounting/               # PnL, комиссии, funding, качество исполнения
├── services/                 # Общие сервисы: clock, id, health helpers
├── observability/            # Логирование, метрики, tracing hooks, алерты
├── control/                  # Health, pause/resume/flatten (опциональный веб-слой)
│
├── docs/                     # Архитектура и процессы
│   ├── architecture.md
│   ├── project_structure.md
│   ├── runtime_modes.md
│   ├── trade_lifecycle.md
│   ├── reconciliation.md
│   └── roadmap.md
│
└── tests/                    # unit / integration / replay / fixtures
    ├── unit/
    ├── integration/
    ├── replay/
    └── fixtures/
```

## Как ориентироваться

1. **Домен** (`domain/`) — сначала смотреть сюда: что считается сигналом, ордером, исполнением, позицией.
2. **Исполнение** (`execution/`) — как намерение превращается в действия и состояния.
3. **Биржа** (`exchange/`) — всё, что касается wire-формата OKX; не должно «протекать» в стратегию.
4. **Риск** (`risk/`) — все проверки и аварийные остановы до и во время торговли.
5. **Документация** (`docs/`) — смысловые связи между блоками и операционные сценарии.

## README по пакетам

В корне каждого основного пакета есть `README.md` с назначением блока, границами и сценариями расширения.
