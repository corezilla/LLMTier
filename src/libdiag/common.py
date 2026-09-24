"""Shared helpers for the libdiag (M006) diagnostics feature modules."""
from __future__ import annotations

import math
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def hour_of(stamp: str | None = None) -> str:
    stamp = stamp or now()
    return stamp[:13]


def iso(stamp: datetime) -> str:
    return stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def percentile(sorted_values: list[float], p: int) -> float | None:
    if not sorted_values:
        return None
    rank = max(1, math.ceil(p / 100 * len(sorted_values)))
    return sorted_values[rank - 1]
