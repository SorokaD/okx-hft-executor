# Обзор проекта `okx-hft-executor`

`okx-hft-executor` — сервис исполнения торговых стратегий для OKX с локальным журналированием
сделок и событий в SQLite. Текущая версия ориентирована на baseline execution и управление
несколькими стратегиями через strategy manager.

## Что делает сервис

- поднимает runtime-менеджер стратегий;
- запускает стратегии параллельно (сейчас торговая логика baseline);
- исполняет заявки через OKX REST или stub (по режиму);
- сопровождает позицию (TP/SL/timeout, maker reprice, reconciliation);
- сохраняет сигналы, ордера, позиции, PnL и service events в БД;
- принимает команды включения/выключения стратегий через очередь команд.

## Ключевые подсистемы

- `app/main.py` — вход в процесс, запуск strategy manager или служебных команд.
- `app/strategy_manager.py` — управление жизненным циклом стратегий (enable/disable/restart).
- `app/orchestrator.py` — baseline-оркестрация `signal -> order -> position -> exit`.
- `strategy/contracts.py` — единый контракт стратегии (plugin API).
- `strategy/registry.py` — реестр `strategy_name -> factory`.
- `exchange/okx/rest_client.py` — интеграция с OKX v5 REST.
- `persistence/sqlite_store.py` — схема и операции хранения runtime-данных.
- `control/app.py` — удаленный Control API для управления без SSH.

## Модель масштабирования

Проект построен в гибридной модели:

- изоляция по контейнерам (`executor` + `control-api`);
- параллельные стратегии внутри `executor` через strategy manager;
- стратегия маркируется `strategy_name` во всех ключевых таблицах:
  - `signals`
  - `orders`
  - `positions`
  - `trade_results`
  - `service_events`

Это позволяет безопасно добавлять новые стратегии и управлять ими без остановки сервиса.

## Как добавить новую стратегию

1. Создать модуль стратегии в `strategy/<name>/service.py`.
2. Реализовать контракт из `strategy/contracts.py`.
3. Зарегистрировать стратегию в `strategy/registry.py`.
4. Добавить ее в `OKX_HFT_STRATEGIES_JSON`.

После этого strategy manager и control-api изменений не требуют.

## Runtime-режимы

- `live` — боевая торговля;
- `paper` — бумажный/демо-контур;
- `replay` — воспроизведение (развитие в roadmap).

Детали: `docs/runtime_modes.md`.

## Управление стратегиями

Варианты управления:

- локально/удаленно через команду внутри контейнера (`python -m app.main --strategy-*`);
- удаленно через HTTP (`control-api`) с токеном `X-API-Key`.

Команды поддерживают:

- `enable`
- `disable` (`drain` или `force`)
- `restart`
- просмотр статуса (`list` / `GET /strategies`)

## Для кого документ

Этот файл — верхнеуровневая карта. Для практической эксплуатации смотри:

- `docs/getting_started.md` — старт и базовые команды;
- `docs/deployment_hybrid.md` — деплой на хост и операционные шаги;
- `docs/control_api.md` — удаленное управление стратегиями;
- `docs/trade_lifecycle.md` — жизненный цикл сделки.
