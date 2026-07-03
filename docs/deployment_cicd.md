# CI/CD: автодеплой на VPS при push в `main`

Деплой через **GitHub Actions** → SSH на VPS → `git pull` + `docker compose up -d --build`.

Файл workflow: [.github/workflows/deploy-vps.yml](../.github/workflows/deploy-vps.yml)

---

## 1. Когда срабатывает

| Событие | Условие |
|---------|---------|
| `push` в ветку **`main`** | изменились файлы в коде сервиса (см. `paths` в workflow) |
| `workflow_dispatch` | ручной запуск в GitHub → Actions → Deploy VPS → Run workflow |

**Не запускается** при правках только:

- `docs/**`
- `README.md`, `AGENTS.md`, `*.md` (кроме попадания в `paths`)
- `tests/**` (тесты не в `paths` — добавьте при необходимости)

### Изменить список папок

В `.github/workflows/deploy-vps.yml` блок `on.push.paths`:

```yaml
paths:
  - app/**
  - docker-compose.yml
  # добавьте свои пути
```

Для **монорепозитория** (если executor в подпапке):

```yaml
paths:
  - okx-hft-executor/app/**
  - okx-hft-executor/docker-compose.yml
```

И в `script` деплоя: `cd "${DEPLOY_PATH}"` должен указывать на эту подпапку.

---

## 2. Однократная настройка на VPS

Сервер уже с Docker и клоном репозитория (см. [deployment_vps_runbook.md](deployment_vps_runbook.md)).

```bash
cd /opt/okx-hft-executor/okx-hft-executor
git remote -v   # origin → ваш GitHub
test -f .env && chmod 600 .env
```

`.env` **остаётся только на сервере**, в git не коммитить.

Пользователь `okx-hft-executor` должен иметь право:

```bash
# без sudo для docker (после usermod -aG docker)
docker compose up -d --build
```

Если docker только через `sudo` — в workflow в `script` замените на `sudo docker compose ...`.

---

## 3. Deploy-ключ для GitHub Actions

На **вашем ПК** (отдельный ключ, не личный):

```powershell
ssh-keygen -t ed25519 -C "github-actions-deploy-okx-hft" -f $env:USERPROFILE\.ssh\okx-hft-deploy -N '""'
```

Публичный ключ на **VPS**:

```powershell
type $env:USERPROFILE\.ssh\okx-hft-deploy.pub | ssh okx-hft-executor@<VPS_IP> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

На сервере ограничьте ключ (опционально, в `~/.ssh/authorized_keys`):

```text
command="",restrict ssh-ed25519 AAAA... github-actions-deploy
```

Для простого старта достаточно обычной строки ключа.

---

## 4. Секреты в GitHub

Репозиторий → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret | Пример значения |
|--------|-----------------|
| `VPS_SSH_HOST` | IP или hostname VPS |
| `VPS_SSH_USER` | `okx-hft-executor` |
| `VPS_SSH_PRIVATE_KEY` | содержимое `okx-hft-deploy` (приватный ключ, целиком) |
| `VPS_DEPLOY_PATH` | `/opt/okx-hft-executor/okx-hft-executor` |

---

## 5. Что делает workflow

1. Checkout (для метаданных; код на сервер тянется через `git fetch`).
2. SSH на VPS:
   - `git fetch` + `git reset --hard origin/main`
   - проверка `.env`
   - `docker compose up -d --build`
   - `docker compose ps`
   - smoke: `python -m app.main --dry-run` в контейнере executor

---

## 6. Проверка

1. Пуш в `main` с изменением, например, `app/orchestrator.py`.
2. GitHub → **Actions** → run **Deploy VPS** → зелёный статус.
3. На VPS:

```bash
cd /opt/okx-hft-executor/okx-hft-executor
git log -1 --oneline
sudo docker compose ps
```

---

## 7. CI без деплоя (опционально)

Добавьте отдельный workflow `ci.yml` на каждый PR:

```yaml
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]" && pytest
```

Деплой только из `main` после merge.

---

## 8. Безопасность

- Отдельный deploy-ключ, не ваш личный.
- SSH на VPS только по ключу ([SECURITY_BASELINE](SECURITY_BASELINE_VPS_SSH_AND_NETWORK.md)).
- Секреты OKX только в `.env` на сервере.
- `concurrency` в workflow — не два деплоя одновременно на один хост.

---

## 9. Откат

```bash
ssh okx-hft-executor@<VPS_IP>
cd /opt/okx-hft-executor/okx-hft-executor
git log --oneline -5
git reset --hard <commit-sha>
docker compose up -d --build
```

---

## 10. GitLab / другой CI

Тот же `script` из workflow можно запустить в GitLab CI `deploy` job с `only: changes` и переменными `VPS_*`.
