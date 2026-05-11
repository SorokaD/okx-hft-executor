# Деплой на хост (Hybrid модель)

Документ описывает продакшен-подобный деплой сервиса в варианте:

- `executor` — процесс strategy manager и торговые стратегии;
- `control-api` — удаленное управление стратегиями без SSH.

## 1. Предпосылки

- Linux/VPS/сервер с Docker и Docker Compose.
- Открытый исходящий доступ к `https://www.okx.com`.
- Закрытый доступ к порту control-api (через firewall/VPN/reverse proxy).

## 2. Подготовка конфигурации

1. Скопировать `.env.example` в `.env`.
2. Задать ключевые параметры:

```env
OKX_HFT_RUNTIME_MODE=paper
OKX_HFT_SAFE_MODE=1
OKX_HFT_CONTROL_API_TOKEN=<long-random-token>
OKX_SQLITE_PATH=/app/data/baseline_mvp.sqlite3
OKX_HFT_STRATEGIES_JSON=[{"strategy_name":"random_baseline_v1","inst_id":"BTC-USDT-SWAP","mode":"enabled"}]
```

Для реальных запросов к OKX отключить safe mode и заполнить `OKX_API_*`.

## 3. Запуск

```bash
docker compose up -d --build
docker compose ps
```

Логи:

```bash
docker compose logs -f executor
docker compose logs -f control-api
```

## 4. Проверки после старта

- `executor` должен быть в `healthy`.
- `control-api` должен отвечать на:

```bash
curl http://<host>:8080/health/liveness
```

и на защищенный endpoint:

```bash
curl -H "X-API-Key: <token>" http://<host>:8080/strategies
```

## 5. Добавление и отключение стратегий без остановки сервиса

Включить стратегию:

```bash
curl -X POST \
  -H "X-API-Key: <token>" \
  -H "Content-Type: application/json" \
  -d '{"inst_id":"ETH-USDT-SWAP"}' \
  http://<host>:8080/strategies/mean_reversion_v1/enable
```

Отключить мягко (`drain`):

```bash
curl -X POST \
  -H "X-API-Key: <token>" \
  "http://<host>:8080/strategies/mean_reversion_v1/disable?mode=drain"
```

Отключить принудительно (`force`):

```bash
curl -X POST \
  -H "X-API-Key: <token>" \
  "http://<host>:8080/strategies/mean_reversion_v1/disable?mode=force"
```

## 6. Обновление версии сервиса

```bash
git pull
docker compose up -d --build
```

Если нужны изменения env-переменных, сначала обновить `.env`, затем повторить `up -d --build`.

## 7. Операционные рекомендации

- Использовать отдельного пользователя/роль для деплоя.
- Настроить backup директории `./data`.
- Ограничить доступ к `8080` по IP или VPN.
- Перед live-режимом протестировать на `paper` и `safe_mode=1`.
- Вести журнал изменений конфигурации стратегий (кто/когда включал/выключал).
