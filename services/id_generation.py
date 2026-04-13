"""Генерация устойчивых идентификаторов (client order id, event id)."""

from __future__ import annotations

import uuid


def new_client_order_id(prefix: str = "cl") -> str:
    """Заглушка: достаточная уникальность для одного процесса; усилить при multi-instance."""
    return f"{prefix}-{uuid.uuid4().hex}"
