"""
Абстракция часов для тестов и replay.

Production использует `SystemClock`; в тестах подменяется фиксированным временем.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class Clock(ABC):
    @abstractmethod
    def now_utc(self) -> datetime:
        ...


class SystemClock(Clock):
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)
