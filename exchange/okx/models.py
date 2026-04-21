from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class OkxOrder:
    ord_id: str
    cl_ord_id: str
    state: str
    side: str
    px: Decimal | None
    avg_px: Decimal | None
    sz: Decimal
    fill_sz: Decimal


@dataclass(slots=True)
class OkxPosition:
    inst_id: str
    pos: Decimal
    avg_px: Decimal | None
    pos_id: str | None = None
    c_time_ms: int | None = None


@dataclass(slots=True)
class OkxTicker:
    inst_id: str
    last: Decimal
    ts_ms: int

