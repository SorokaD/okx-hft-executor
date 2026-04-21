# Тесты

## Назначение

Проверка корректности доменных инвариантов, интеграции портов (mock exchange), воспроизводимости сценариев через replay.

## Структура

| Каталог | Назначение |
|---------|------------|
| `unit/` | Изолированные модули без сети и БД. |
| `integration/` | Сборка графа с подменёнными адаптерами, возможен testcontainers. |
| `replay/` | Детерминированные прогоны по записанным событиям. |
| `fixtures/` | JSON/NDJSON записи ответов API и WS. |

## Принципы

- домен и execution тестируются с подменённым `Clock` и `ExchangeClient`;
- не ходить в live OKX из CI;
- критические переходы `OrderStateMachine` и `reconciliation` покрываются явными таблицами кейсов.

## Запуск

Сначала установите dev-зависимости: `pip install -e ".[dev]"` (см. [docs/getting_started.md](../docs/getting_started.md)).

```bash
make test
# или
python -m pytest tests/ -q
```
