# Control API

Control API — HTTP-интерфейс удаленного управления стратегиями без SSH.

Сервис поднимается в контейнере `control-api` и работает поверх SQLite-очереди команд.

## Безопасность

- Все endpoint-ы управления требуют заголовок `X-API-Key`.
- Токен берется из `OKX_HFT_CONTROL_API_TOKEN`.
- Если токен не настроен, API управления недоступно (`503`).

## Endpoint-ы

### `GET /health/liveness`

Публичная проверка живости процесса.

Пример:

```bash
curl http://<host>:8080/health/liveness
```

### `GET /strategies`

Список стратегий из `strategies_registry`.

```bash
curl -H "X-API-Key: <token>" http://<host>:8080/strategies
```

### `POST /strategies/{strategy_name}/enable`

Ставит команду включения стратегии в очередь.

Опциональное тело:

```json
{
  "inst_id": "BTC-USDT-SWAP"
}
```

Пример:

```bash
curl -X POST \
  -H "X-API-Key: <token>" \
  -H "Content-Type: application/json" \
  -d '{"inst_id":"BTC-USDT-SWAP"}' \
  http://<host>:8080/strategies/random_baseline_v1/enable
```

### `POST /strategies/{strategy_name}/disable?mode=drain|force`

Ставит команду отключения.

- `drain` — не открывать новые входы, завершить текущий цикл корректно;
- `force` — остановить стратегию принудительно.

```bash
curl -X POST -H "X-API-Key: <token>" \
  "http://<host>:8080/strategies/random_baseline_v1/disable?mode=drain"
```

### `POST /strategies/{strategy_name}/restart`

Ставит команду перезапуска стратегии.

```bash
curl -X POST -H "X-API-Key: <token>" \
  http://<host>:8080/strategies/random_baseline_v1/restart
```

## Ответы API

Команды возвращают статус `queued` — фактическое выполнение происходит асинхронно в strategy manager.

Контролировать применение команд можно через:

- `GET /strategies`
- таблицы `strategies_registry` и `strategy_commands`
- логи контейнера `executor`

## Рекомендуемое прод-окружение

- reverse proxy (Nginx/Caddy) перед `control-api`;
- HTTPS-терминация;
- IP allowlist или VPN;
- rate limiting на `/strategies/*`;
- ротация и централизация логов.
