"""
Высокоуровневая координация задач исполнителя.

Здесь в будущем появятся параллельные asyncio-задачи: поток рыночных данных,
обработка private WS, таймер reconciliation, run-loop execution engine.
Сейчас — минимальная заглушка для проверки сборки контекста.
"""

from __future__ import annotations

import logging

from app.bootstrap import ExecutorContext


async def run_once_placeholder(ctx: ExecutorContext) -> None:
    """Один «тик» каркаса: доказательство, что контекст и импорты работают."""
    log = logging.getLogger(__name__)
    log.info("Оркестратор (заглушка): clock=%s", type(ctx.clock).__name__)
    # Точка подключения run-loop: await engine.run_forever() и т.д.
