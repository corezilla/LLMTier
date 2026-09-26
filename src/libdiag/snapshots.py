"""Feature: diagnostic snapshots (diagnostic_snapshots) — capture + paged query.

Composition point: capture_snapshot consults the settings switch (SettingsDiagnostics).
"""
from __future__ import annotations

import uuid

from util.store import Store

from .common import now
from .settings import SettingsDiagnostics
from .traces import Warn


class SnapshotDiagnostics:
    def __init__(self, store: Store, settings: SettingsDiagnostics, warn: Warn):
        self.store = store
        self.settings = settings
        self._warn = warn

    def capture_snapshot(self, request_id: str, deployment_id: str | None, model: str | None, upstream_url: str,
                         backend_model: str | None, http_status: int | None, latency_ms: float | None, error_summary: str | None) -> str | None:
        if not self.settings.switches()["snapshots_enabled"]:
            return None
        try:
            snap_type = "upstream" if http_status is not None else "error"
            snap_id = f"snap_{uuid.uuid4().hex}"
            summary = error_summary.encode("utf-8")[:256].decode("utf-8", "ignore") if error_summary else None
            with self.store.transaction(True) as conn:
                conn.execute(
                    "INSERT INTO diagnostic_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (snap_id, request_id, now(), upstream_url, backend_model, http_status, latency_ms, summary or None, model, deployment_id, snap_type),
                )
            return snap_id
        except Exception as exc:
            self._warn(f"snapshot write failed: {exc}")
            return None

    def snapshots_page(self, since: str | None, until: str | None, deployment_id: str | None, model: str | None,
                       limit: int = 50, cursor: str | None = None) -> dict:
        limit = max(1, min(limit, 500))
        where, params = ["1=1"], []
        if since: where.append("captured_at>=?"); params.append(since)
        if until: where.append("captured_at<=?"); params.append(until)
        if deployment_id: where.append("deployment_id=?"); params.append(deployment_id)
        if model: where.append("model=?"); params.append(model)
        if cursor: where.append("(captured_at||id)<(SELECT captured_at||id FROM diagnostic_snapshots WHERE id=?)"); params.append(cursor)
        rows = self.store.all(
            f"SELECT * FROM diagnostic_snapshots WHERE {' AND '.join(where)} ORDER BY captured_at DESC,id DESC LIMIT ?", (*params, limit + 1))
        more = len(rows) > limit
        items = [{k: row[k] for k in ("id", "request_id", "captured_at", "upstream_url", "backend_model", "http_status", "latency_ms", "error_summary", "model", "deployment_id", "snapshot_type")} for row in rows[:limit]]
        return {"items": items, "next_cursor": items[-1]["id"] if more and items else None, "has_more": more}
