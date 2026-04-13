"""
Точка входа процесса (console script `okx-hft-executor`).

Загружает настройки, собирает зависимости и запускает baseline loop.
Реальная торговая петля подключается на следующих этапах разработки.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.bootstrap import ExecutorContext, build_executor_context
from app.orchestrator import run_baseline_loop
from services.id_generation import new_client_order_id
from config.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OKX HFT executor (baseline MVP)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только проверить конфигурацию и выйти.",
    )
    parser.add_argument(
        "--run-seconds",
        type=int,
        default=None,
        help="Ограничить длительность запуска в секундах (smoke-run).",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=None,
        help="Ограничить число итераций цикла (smoke-run).",
    )
    parser.add_argument(
        "--check-okx",
        action="store_true",
        help="Проверить доступность OKX API без запуска baseline loop.",
    )
    parser.add_argument(
        "--check-okx-order",
        action="store_true",
        help="Проверить выставление минимального market order и закрытие.",
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO)
    )
    log = logging.getLogger(__name__)
    log.info(
        "Старт baseline okx-hft-executor, режим=%s",
        settings.runtime_mode.value,
    )

    ctx = build_executor_context(settings)
    if args.dry_run:
        log.info("Dry-run: контекст собран, выход.")
        return

    if args.check_okx:
        asyncio.run(run_okx_check(ctx))
        return
    if args.check_okx_order:
        asyncio.run(run_okx_order_check(ctx))
        return

    asyncio.run(
        run_baseline_loop(
            ctx,
            run_seconds=args.run_seconds,
            max_loops=args.max_loops,
        )
    )


async def run_okx_check(ctx: ExecutorContext) -> None:
    settings = ctx.settings
    log = logging.getLogger(__name__)
    log.info("OKX check started")
    log.info("base_url=%s", settings.okx_base_url)
    log.info("demo_flag=%s", 1 if settings.okx_flag_demo else 0)
    log.info("inst_id=%s", settings.okx_inst_id)

    account_ok = False
    ticker_ok = False
    tick_ok = False

    try:
        await ctx.exchange.get_account_snapshot()
        account_ok = True
    except Exception as exc:  # noqa: BLE001
        log.error("account reachable: no (%s)", exc)

    try:
        ticker = await ctx.exchange.get_ticker_last(inst_id=settings.okx_inst_id)
        ticker_ok = True
        log.info("last_price=%s", ticker.last)
    except Exception as exc:  # noqa: BLE001
        log.error("ticker reachable: no (%s)", exc)

    try:
        tick = await ctx.exchange.get_tick_size(inst_id=settings.okx_inst_id)
        tick_ok = True
        log.info("tick_size=%s", tick)
    except Exception as exc:  # noqa: BLE001
        if settings.okx_inst_id == "BTC-USDT-SWAP":
            log.warning(
                "tick_size fetch failed (%s), fallback tick_size=0.1 for BTC-USDT-SWAP",
                exc,
            )
            tick_ok = True
            log.info("tick_size=%s", "0.1")
        else:
            log.error("tick_size reachable: no (%s)", exc)

    log.info("account reachable: %s", "yes" if account_ok else "no")
    log.info("ticker reachable: %s", "yes" if ticker_ok else "no")
    if account_ok and ticker_ok and tick_ok:
        log.info("OKX check success")
    else:
        log.warning("OKX check finished with issues")


async def run_okx_order_check(ctx: ExecutorContext) -> None:
    """Короткая проверка: open tiny order -> close tiny order."""
    settings = ctx.settings
    log = logging.getLogger(__name__)
    log.info("OKX order check started")
    log.info(
        "base_url=%s demo_flag=%s inst_id=%s td_mode=%s size=%s",
        settings.okx_base_url,
        1 if settings.okx_flag_demo else 0,
        settings.okx_inst_id,
        settings.okx_td_mode,
        settings.okx_order_size,
    )
    try:
        open_cl = new_client_order_id(prefix="chk-open")
        open_ord = await ctx.exchange.place_market_order(
            side="buy",
            size=settings.okx_order_size,
            cl_ord_id=open_cl,
        )
        log.info("order open submitted: ord_id=%s cl_ord_id=%s", open_ord, open_cl)

        close_cl = new_client_order_id(prefix="chk-close")
        close_ord = await ctx.exchange.place_market_order(
            side="sell",
            size=settings.okx_order_size,
            cl_ord_id=close_cl,
            reduce_only=True,
        )
        log.info("order close submitted: ord_id=%s cl_ord_id=%s", close_ord, close_cl)
        log.info("OKX order check success")
    except Exception as exc:  # noqa: BLE001
        log.error("OKX order check failed: %s", exc)


if __name__ == "__main__":
    main()
    sys.exit(0)
