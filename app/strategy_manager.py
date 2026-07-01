from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.bootstrap import ExecutorContext, build_executor_context
from app.orchestrator import StrategyLoopControl, run_baseline_loop
from config.settings import Settings, StrategyMode
from persistence.sqlite_store import SqliteMvpStore


@dataclass(slots=True)
class StrategyRuntime:
    strategy_name: str
    inst_id: str
    task: asyncio.Task[None]
    control: StrategyLoopControl


class StrategyManager:
    """Менеджер стратегий: запускает, останавливает и обрабатывает команды."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._log = logging.getLogger(__name__)
        self._store = SqliteMvpStore(settings.sqlite_path)
        self._runtimes: dict[str, StrategyRuntime] = {}
        self._stop_event = asyncio.Event()

    async def run_forever(self) -> None:
        self._bootstrap_registry()
        await self._start_enabled_strategies()
        self._log.info("strategy manager started")
        try:
            while not self._stop_event.is_set():
                await self._sync_finished_tasks()
                await self._process_commands()
                await asyncio.sleep(2.0)
        finally:
            await self._shutdown_all()
            self._store.close()

    def stop(self) -> None:
        self._stop_event.set()

    def _bootstrap_registry(self) -> None:
        for cfg in self._settings.get_strategy_runtime_configs():
            desired = "enabled" if cfg.mode == StrategyMode.ENABLED else "disabled"
            runtime = "stopped"
            self._store.upsert_strategy_registry(
                strategy_name=cfg.strategy_name,
                inst_id=cfg.inst_id,
                desired_state=desired,
                runtime_state=runtime,
            )

    async def _start_enabled_strategies(self) -> None:
        for cfg in self._settings.get_strategy_runtime_configs():
            if cfg.mode != StrategyMode.ENABLED:
                continue
            await self._start_strategy(strategy_name=cfg.strategy_name, inst_id=cfg.inst_id)

    async def _start_strategy(self, *, strategy_name: str, inst_id: str) -> None:
        if strategy_name in self._runtimes:
            return
        strategy_settings = self._settings.model_copy(
            update={
                "strategy_name": strategy_name,
                "okx_inst_id": inst_id,
            }
        )
        ctx = build_executor_context(strategy_settings)
        control = StrategyLoopControl()
        task = asyncio.create_task(
            self._run_strategy_task(
                strategy_name=strategy_name,
                inst_id=inst_id,
                ctx=ctx,
                control=control,
            )
        )
        self._runtimes[strategy_name] = StrategyRuntime(
            strategy_name=strategy_name,
            inst_id=inst_id,
            task=task,
            control=control,
        )
        self._store.set_strategy_desired_state(strategy_name=strategy_name, desired_state="enabled")
        self._store.set_strategy_runtime_state(strategy_name=strategy_name, runtime_state="running")
        self._log.info("strategy started: %s (%s)", strategy_name, inst_id)

    async def _run_strategy_task(
        self,
        *,
        strategy_name: str,
        inst_id: str,
        ctx: ExecutorContext,
        control: StrategyLoopControl,
    ) -> None:
        try:
            await run_baseline_loop(
                ctx,
                strategy_name_override=strategy_name,
                inst_id_override=inst_id,
                control=control,
            )
            self._store.set_strategy_runtime_state(strategy_name=strategy_name, runtime_state="stopped")
        except asyncio.CancelledError:
            self._store.set_strategy_runtime_state(strategy_name=strategy_name, runtime_state="stopped")
            raise
        except Exception as exc:  # noqa: BLE001
            self._store.set_strategy_runtime_state(strategy_name=strategy_name, runtime_state="error")
            self._store.save_service_event(
                strategy_name=strategy_name,
                event_type="strategy_crashed",
                message="strategy task crashed",
                payload={"error": str(exc)},
                level="ERROR",
            )

    async def _process_commands(self) -> None:
        commands = self._store.claim_pending_strategy_commands()
        for command in commands:
            cid = int(command["id"])
            strategy_name = str(command["strategy_name"])
            command_type = str(command["command_type"]).lower()
            command_mode = command["command_mode"]
            try:
                if command_type == "enable":
                    inst_id = self._resolve_inst_id(strategy_name)
                    await self._start_strategy(strategy_name=strategy_name, inst_id=inst_id)
                elif command_type == "disable":
                    await self._disable_strategy(
                        strategy_name=strategy_name,
                        mode=str(command_mode or "drain"),
                    )
                elif command_type == "restart":
                    await self._disable_strategy(strategy_name=strategy_name, mode="force")
                    inst_id = self._resolve_inst_id(strategy_name)
                    await self._start_strategy(strategy_name=strategy_name, inst_id=inst_id)
                else:
                    raise ValueError(f"Unsupported strategy command: {command_type}")
                self._store.finish_strategy_command(command_id=cid, status="done")
            except Exception as exc:  # noqa: BLE001
                self._store.finish_strategy_command(
                    command_id=cid,
                    status="failed",
                    error_text=str(exc),
                )

    async def _disable_strategy(self, *, strategy_name: str, mode: str) -> None:
        runtime = self._runtimes.get(strategy_name)
        self._store.set_strategy_desired_state(strategy_name=strategy_name, desired_state="disabled")
        if runtime is None:
            self._store.set_strategy_runtime_state(strategy_name=strategy_name, runtime_state="stopped")
            return
        if mode == "force":
            runtime.control.request_force_stop()
            runtime.task.cancel()
            await asyncio.gather(runtime.task, return_exceptions=True)
        else:
            runtime.control.request_drain_stop()
            await runtime.task
        self._runtimes.pop(strategy_name, None)
        self._store.set_strategy_runtime_state(strategy_name=strategy_name, runtime_state="stopped")
        self._log.info("strategy disabled: %s mode=%s", strategy_name, mode)

    async def _sync_finished_tasks(self) -> None:
        dead: list[str] = []
        for name, runtime in self._runtimes.items():
            if runtime.task.done():
                dead.append(name)
        for name in dead:
            runtime = self._runtimes.pop(name)
            await asyncio.gather(runtime.task, return_exceptions=True)

    async def _shutdown_all(self) -> None:
        names = list(self._runtimes.keys())
        for strategy_name in names:
            await self._disable_strategy(strategy_name=strategy_name, mode="force")

    def _resolve_inst_id(self, strategy_name: str) -> str:
        for cfg in self._settings.get_strategy_runtime_configs():
            if cfg.strategy_name == strategy_name:
                return cfg.inst_id
        rows = self._store.list_strategies_registry()
        for row in rows:
            if row["strategy_name"] == strategy_name:
                return row["inst_id"]
        return self._settings.okx_inst_id
