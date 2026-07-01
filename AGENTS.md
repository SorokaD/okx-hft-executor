# AGENTS.md

## Project Overview

This repository is `okx-hft-executor`.

It is the execution component of the OKX HFT pet project. The executor is responsible for receiving trading signals, deciding whether a trade is allowed, placing/canceling orders through OKX API, tracking order lifecycle, managing open positions, applying risk controls, and persisting execution data into PostgreSQL/TimescaleDB.

This is not a research notebook repository. Code in this repository may affect trading behavior. Treat all changes as safety-critical.

The default development assumption is:

- no real-money trading, just demo mode;
- demo/sandbox mode first;
- dry-run mode when possible;
- explicit risk checks before order placement;
- full persistence of signals, orders, fills, positions, decisions, errors, and PnL.

## Core Principles

### 1. Safety first

Never make changes that can accidentally enable live trading.

Live trading must require explicit configuration. Do not default to live mode.

Safe defaults:

- `dry_run = true`
- `runtime_mode = demo`
- `safe_mode = true`
- small order size
- no hidden auto-retry loops for order placement
- no uncontrolled infinite trading loops

If a task involves real order placement, position closing, leverage, margin mode, or account configuration, be conservative and make the behavior explicit.

### 2. Deterministic execution

The executor should behave predictably.

Avoid hidden randomness in execution logic. If randomness is needed for a baseline strategy, it must be seeded and clearly isolated from production trading logic.

### 3. Idempotency

Order placement and cancellation must be idempotent where possible.

Use stable `clOrdId` / client order identifiers. Do not generate duplicate client order IDs for the same logical decision unless the design explicitly requires a new attempt.

Before adding new execution flows, check how the project stores:

- signal id;
- decision id;
- order id;
- client order id;
- exchange order id;
- fill id;
- position id.

Do not break existing identity relationships.

### 4. Persist everything important

The executor must persist enough data to reconstruct what happened.

Important entities include:

- incoming signal;
- decision;
- risk check result;
- order request;
- order response;
- exchange error;
- fill/trade;
- position;
- realized/unrealized PnL;
- executor heartbeat;
- configuration snapshot used during execution.

Do not remove logging or persistence unless explicitly requested.

### 5. No silent failures

Never swallow exceptions silently.

If an exchange request fails, the error should be logged with enough context:

- instrument id;
- side;
- order type;
- size;
- price if applicable;
- tdMode;
- clOrdId;
- raw OKX response code/message;
- correlation id / decision id if available.

Prefer explicit typed errors over generic exceptions.

### 6. Test first for trading logic

Any change to trading logic should include or update tests.

Examples of trading logic:

- entry decision;
- exit decision;
- TP/SL logic;
- risk limits;
- position state transitions;
- order lifecycle;
- retry behavior;
- PnL calculation;
- fee calculation;
- break-even calculation;
- client order id generation.

If tests are missing, add small focused tests before large refactoring.

## Repository Responsibilities

This repository owns:

- executor runtime;
- OKX REST/WebSocket execution integration;
- order placement and cancellation;
- position tracking;
- risk checks before trading;
- execution persistence;
- execution monitoring/heartbeat;
- demo/live runtime configuration;
- baseline executor strategies for comparison.

This repository does not own:

- raw market data collection;
- order book reconstruction;
- research notebooks;
- model training;
- feature generation pipelines;
- Airflow DAGs for market data;
- Superset/Grafana dashboards, except small exporter/metrics hooks if needed.

Those responsibilities belong to other repositories such as:

- `okx-hft-collector`
- `okx-hft-clickhouse` or TimescaleDB-related storage repo
- `okx-hft-research`
- `okx-hft-airflow-dags`
- `okx-hft-ops`

## Expected Architecture

Prefer this style of structure:

```text
okx-hft-executor/
  src/
    okx_hft_executor/
      config/
        settings.py
      exchange/
        okx/
          rest_client.py
          models.py
          errors.py
      execution/
        executor.py
        order_manager.py
        position_manager.py
        lifecycle.py
      risk/
        checks.py
        limits.py
      strategy/
        base.py
        baseline_random.py
        model_signal.py
      persistence/
        db.py
        repositories.py
        models.py
      observability/
        logging.py
        metrics.py
        heartbeat.py
      utils/
        ids.py
        time.py
  tests/
  migrations/
  scripts/
  README.md
  AGENTS.md