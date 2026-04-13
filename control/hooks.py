"""
Операционные хуки: пауза, возобновление, flatten.

Реальные вызовы должны пробрасывать команды в execution/risk через thread-safe/async-safe канал.
"""

from __future__ import annotations

from risk.kill_switch import KillSwitch


def arm_kill_switch(kill_switch: KillSwitch) -> None:
    kill_switch.arm()
