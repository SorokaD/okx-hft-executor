"""
Точка входа процесса (console script `okx-hft-executor`).

Загружает настройки, собирает зависимости через bootstrap и запускает оркестратор.
Реальная торговая петля подключается на следующих этапах разработки.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.bootstrap import build_executor_context
from app.orchestrator import run_once_placeholder
from config.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="OKX HFT executor (scaffold).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только проверить конфигурацию и выйти.",
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    log = logging.getLogger(__name__)
    log.info("Старт каркаса okx-hft-executor, режим=%s", settings.runtime_mode.value)

    ctx = build_executor_context(settings)
    if args.dry_run:
        log.info("Dry-run: контекст собран, выход.")
        return

    asyncio.run(run_once_placeholder(ctx))


if __name__ == "__main__":
    main()
    sys.exit(0)
