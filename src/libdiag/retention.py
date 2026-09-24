"""Feature: retention — delete diagnostics rows older than N days."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from util.store import Store

from .common import iso

_RETENTION_TABLES = (
    ("diagnostic_snapshots", "captured_at"),
    ("trace_events", "created_at"),
    ("data_plane_latency_samples", "created_at"),
    ("data_plane_stats", "stat_hour"),
)


def cleanup(store: Store, warn: Callable[[str], None], days: int = 7) -> int:
    cutoff = iso(datetime.now(timezone.utc) - timedelta(days=days))
    deleted = 0
    try:
        with store.transaction(True) as conn:
            for table, column in _RETENTION_TABLES:
                deleted += conn.execute(f"DELETE FROM {table} WHERE {column}<?", (cutoff,)).rowcount
        return deleted
    except Exception as exc:
        warn(f"cleanup failed: {exc}")
        return 0
