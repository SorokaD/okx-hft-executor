# Деплой на хост (Hybrid модель)

Документ описывает продакшен-подобный деплой сервиса в варианте:

- `executor` — процесс strategy manager и торговые стратегии;
- `control-api` — удалённое управление стратегиями без SSH.

**Пошаговый runbook для VPS (Docker, `.env`, права на `data/`, live mode):**  
→ [deployment_vps_runbook.md](deployment_vps_runbook.md)

**Security baseline (SSH, UFW, Fail2Ban):**  
→ [SECURITY_BASELINE_VPS_SSH_AND_NETWORK.md](SECURITY_BASELINE_VPS_SSH_AND_NETWORK.md)

---

## 1. Предпосылки

- Linux VPS с **Docker** и **Docker Compose v2** (`docker compose`).
- Открытый исходящий доступ к `https://www.okx.com`.
- Закрытый доступ к порту control-api (UFW / VPN / reverse proxy).
- Пользователь на хосте **не root** (например `okx-hft-executor`), деплой из каталога с `docker-compose.yml`.

---

## 2. Подготовка конфигурации

1. Создать `.env` (шаблон [.env.example](../.env.example)); **не коммитить** в git.
2. Задать ключевые параметры.

**Безопасный первый запуск (без заявок на биржу):**

```env
OKX_HFT_RUNTIME_MODE=paper
OKX_HFT_SAFE_MODE=1
OKX_HFT_CONTROL_API_TOKEN=<long-random-token>
OKX_HFT_STRATEGIES_JSON=[{"strategy_name":"random_baseline_v1","inst_id":"BTC-USDT-SWAP","mode":"enabled"}]
```

**Live на OKX demo (реальные заявки):**

```env
OKX_HFT_RUNTIME_MODE=live
OKX_HFT_SAFE_MODE=0
OKX_FLAG_DEMO=1
OKX_API_KEY=...
OKX_API_SECRET=...
OKX_API_PASSPHRASE=...
OKX_HFT_CONTROL_API_TOKEN=<long-random-token>
```

В `docker-compose.yml` для обоих сервисов задано:

```yaml
OKX_SQLITE_PATH: /app/data/baseline_mvp.sqlite3
```

SQLite лежит в volume `./data` на хосте. Перед первым запуском выставить права на `data/` для пользователя `app` в контейнере (см. [deployment_vps_runbook.md §4](deployment_vps_runbook.md#4-права-на-каталог-data-обязательно)).

---

## 3. Запуск

```bash
cd /path/to/okx-hft-executor
mkdir -p data
# права на data — см. runbook
docker compose up -d --build
docker compose ps
```

Логи:

```bash
docker compose logs -f executor
docker compose logs -f control-api
```

Остановка:

```bash
docker compose down
```

---

## 4. Сервисы в `docker-compose.yml`

| Сервис | Entrypoint | Порты |
|--------|------------|-------|
| `executor` | `python -m app.main` | наружу не публикуется |
| `control-api` | `uvicorn control.app:app` | `8080:8080` |

> `control-api` использует отдельный `entrypoint` в compose (не `ENTRYPOINT` образа), иначе uvicorn-аргументы попадают в `app.main`.

---

## 5. Проверки после старта

- `executor` и `control-api` в статусе **healthy** (`docker compose ps`).
- control-api:

```bash
curl http://<host>:8080/health/liveness
curl -H "X-API-Key: <token>" http://<host>:8080/strategies
```

- В логах executor при live: `exchange.okx.rest_client`, `runtime_mode=live`.

---

## 6. Добавление и отключение стратегий без остановки сервиса

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

Подробнее: [control_api.md](control_api.md).

---

## 7. Обновление версии

```bash
git pull
docker compose up -d --build
```

После изменения только `.env`:

```bash
docker compose up -d
```

---

## 8. Операционные рекомендации

- Отдельный OS-пользователь для деплоя; SSH только по ключу ([security baseline](SECURITY_BASELINE_VPS_SSH_AND_NETWORK.md)).
- Backup каталога `./data` (SQLite).
- UFW: `22/tcp` + `8080` только с доверенных IP.
- Сначала `paper` + `safe_mode=1`, затем live на demo.
- Журнал изменений стратегий (кто/когда enable/disable).
- Логи Docker: `json-file`, ротация `10m` × `5` (см. compose).
