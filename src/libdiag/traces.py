"""Feature: request traces (trace_events) — record + single/paged query.

The trace view combines trace_events (this feature), diagnostic_snapshots
(snapshot feature) and usage_record_versions (M003/M004), so this module is
one of the cross-feature composition points.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from http_api.errors import ApiError
from util.store import Store

from .common import now

Warn = Callable[[str], None]


class TraceDiagnostics:
    def __init__(self, store: Store, warn: Warn):
        self.store = store
        self._warn = warn

    def record_trace(self, request_id: str, stage: str, detail: dict | None = None, correlation_id: str | None = None) -> None:
        try:
            with self.store.transaction(True) as conn:
                conn.execute(
                    "INSERT INTO trace_events VALUES(?,?,?,?,?,?,?)",
                    (f"tev_{uuid.uuid4().hex}", request_id, stage, now(), json.dumps(detail, ensure_ascii=False) if detail else None, correlation_id, now()),
                )
        except Exception as exc:
            self._warn(f"trace write failed: {exc}")

    def _trace_view(self, request_id: str) -> dict | None:
        stages = [
            {"stage": row["stage"], "timestamp": row["stage_timestamp"], "detail": json.loads(row["detail"]) if row["detail"] else None}
            for row in self.store.all("SELECT stage,stage_timestamp,detail FROM trace_events WHERE request_id=? ORDER BY stage_timestamp,id", (request_id,))
        ]
        if not stages:
            return None
        snapshot = self.store.one(
            "SELECT id,request_id,captured_at,upstream_url,backend_model,http_status,latency_ms,error_summary,model,deployment_id,snapshot_type"
            " FROM diagnostic_snapshots WHERE request_id=? ORDER BY captured_at DESC LIMIT 1", (request_id,))
        usage_row = self.store.one(
            "SELECT record_version,is_final,model,input_tokens,output_tokens,total_tokens,measurement_status,source"
            " FROM usage_record_versions WHERE request_id=? ORDER BY record_version DESC LIMIT 1", (request_id,))
        correlation = next((s["detail"].get("x_correlation_id") for s in reversed(stages) if s.get("detail") and s["detail"].get("x_correlation_id")), None)
        usage = None
        if usage_row:
            usage = {"record_version": usage_row["record_version"], "is_final": bool(usage_row["is_final"]), "model": usage_row["model"],
                     "input_tokens": usage_row["input_tokens"], "output_tokens": usage_row["output_tokens"],
                     "total_tokens": usage_row["total_tokens"], "measurement_status": usage_row["measurement_status"], "source": usage_row["source"]}
        return {
            "request_id": request_id,
            "correlation_id": correlation,
            "stages": stages,
            "snapshot": dict(snapshot) if snapshot else None,
            "usage": usage,
        }

    def trace(self, request_id: str) -> dict:
        view = self._trace_view(request_id)
        if view is None:
            raise ApiError(404, "not_found", "No trace for this request_id")
        return view

    def traces(self, since: str | None = None, until: str | None = None, deployment_id: str | None = None,
               model: str | None = None, limit: int = 50, cursor: str | None = None) -> dict:
        # FUNC-DIAG-TRACES (G-1): time-window trace query, deduped by request, stable paging.
        limit = max(1, min(limit, 500))
        where, params = [], []
        if since: where.append("te.stage_timestamp>=?"); params.append(since)
        if until: where.append("te.stage_timestamp<=?"); params.append(until)
        if deployment_id or model:
            sub, subp = "SELECT request_id FROM diagnostic_snapshots WHERE 1=1", []
            if deployment_id: sub += " AND deployment_id=?"; subp.append(deployment_id)
            if model: sub += " AND model=?"; subp.append(model)
            where.append(f"te.request_id IN ({sub})"); params.extend(subp)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        grouped = (f"SELECT te.request_id AS rid, MIN(te.stage_timestamp) AS first_ts"
                   f" FROM trace_events te{clause} GROUP BY te.request_id")
        outer_where, outer_params = [], []
        if cursor and "|" in cursor:
            cur_ts, cur_rid = cursor.split("|", 1)
            outer_where.append("(first_ts, rid) < (?, ?)"); outer_params.extend([cur_ts, cur_rid])
        sql = f"SELECT * FROM ({grouped}) WHERE {' AND '.join(outer_where)}" if outer_where else grouped
        sql += " ORDER BY first_ts DESC, rid DESC LIMIT ?"
        rows = self.store.all(sql, params + outer_params + [limit + 1])
        more = len(rows) > limit
        rows = rows[:limit]
        items = [view for view in (self._trace_view(row["rid"]) for row in rows) if view]
        next_cursor = f"{rows[-1]['first_ts']}|{rows[-1]['rid']}" if more and rows else None
        return {"items": items, "next_cursor": next_cursor, "has_more": more}
