"""
Kill switch: немедленная остановка новых рискованных действий.

Реализация должна быть максимально простой и доступной из control plane.
"""

from __future__ import annotations


class KillSwitch:
    def __init__(self) -> None:
        self._armed = False

    @property
    def armed(self) -> bool:
        return self._armed

    def arm(self) -> None:
        self._armed = True

    def disarm(self) -> None:
        self._armed = False
