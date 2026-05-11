"""HTTP control plane для удаленного управления стратегиями."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel

from config.settings import get_settings
from persistence.sqlite_store import SqliteMvpStore
from services.health import process_alive


class EnableStrategyRequest(BaseModel):
    inst_id: str | None = None


def _verify_token(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    token = (
        settings.control_api_token.get_secret_value()
        if settings.control_api_token
        else ""
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="control api token is not configured",
        )
    if x_api_key != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )


def _store() -> SqliteMvpStore:
    settings = get_settings()
    return SqliteMvpStore(settings.sqlite_path)


app = FastAPI(title="OKX HFT Control API", version="0.1.0")


@app.get("/health/liveness")
def get_liveness() -> dict[str, object]:
    status_obj = process_alive()
    return asdict(status_obj)


@app.get("/strategies", dependencies=[Depends(_verify_token)])
def list_strategies() -> dict[str, object]:
    store = _store()
    try:
        rows = store.list_strategies_registry()
        return {"items": rows}
    finally:
        store.close()


@app.post(
    "/strategies/{strategy_name}/enable",
    dependencies=[Depends(_verify_token)],
)
def enable_strategy(strategy_name: str, body: EnableStrategyRequest) -> dict[str, str]:
    store = _store()
    try:
        inst_id = body.inst_id
        if inst_id:
            store.upsert_strategy_registry(
                strategy_name=strategy_name,
                inst_id=inst_id,
                desired_state="enabled",
                runtime_state="stopped",
            )
        store.enqueue_strategy_command(
            strategy_name=strategy_name,
            command_type="enable",
        )
        return {
            "status": "queued",
            "command": "enable",
            "strategy_name": strategy_name,
        }
    finally:
        store.close()


@app.post(
    "/strategies/{strategy_name}/disable",
    dependencies=[Depends(_verify_token)],
)
def disable_strategy(
    strategy_name: str,
    mode: Literal["drain", "force"] = Query(default="drain"),
) -> dict[str, str]:
    store = _store()
    try:
        store.enqueue_strategy_command(
            strategy_name=strategy_name,
            command_type="disable",
            command_mode=mode,
        )
        return {
            "status": "queued",
            "command": "disable",
            "mode": mode,
            "strategy_name": strategy_name,
        }
    finally:
        store.close()


@app.post(
    "/strategies/{strategy_name}/restart",
    dependencies=[Depends(_verify_token)],
)
def restart_strategy(strategy_name: str) -> dict[str, str]:
    store = _store()
    try:
        store.enqueue_strategy_command(
            strategy_name=strategy_name,
            command_type="restart",
        )
        return {
            "status": "queued",
            "command": "restart",
            "strategy_name": strategy_name,
        }
    finally:
        store.close()
