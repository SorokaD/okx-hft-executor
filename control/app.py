"""
ASGI-приложение для control plane (опционально, зависимость `pip install -e ".[control]"`).

На каркасе модуль может отсутствовать в среде без FastAPI — не импортировать из ядра без need.
"""

from __future__ import annotations

# Реализация FastAPI будет добавлена при подключении optional dependency.
