from __future__ import annotations

import json
import math
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .errors import ApiError
from .store import Store


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def hour_of(stamp: str | None = None) -> str:
    stamp = stamp or now()
    return stamp[:13]


def _iso(stamp: datetime) -> str:
    return stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


_TYPES = ("fault_502", "fault_503", "delay", "rate_limit", "stream_terminate", "malformed_event")
_PRE_CALL = ("fault_502", "fault_503", "rate_limit", "delay")
_RANGES = {"delay_ms": (0, 60000), "retry_after_sec": (0, 300), "stream_terminate_after_events": (1, 10000), "malformed_after_events": (0, 10000)}
_CONFIG_FIELDS = {
    "fault_502": ("error_body",),
    "fault_503": ("error_body",),
    "delay": ("delay_ms",),
    "rate_limit": ("retry_after_sec",),
    "stream_terminate": ("stream_terminate_after_events",),
    "malformed_event": ("malformed_after_events", "malformed_event_type"),
}


def _percentile(sorted_values: list[float], p: int) -> float | None:
    if not sorted_values:
        return None
    rank = max(1, math.ceil(p / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


class DiagnosticsService:
    """LT-OBS 可观测性服务：trace / 快照 / 统计 / 注入开关。

    所有 record_* 均 fail-open：观测失败不得影响 Data Plane 可用性。
    """

    def __init__(self, store: Store, logs=None):
        self.store = store
        self.logs = logs

    def _warn(self, message: str) -> None:
        try:
            if self.logs:
                self.logs.record("warning", "diagnostics", "capture_failed", message)
        except Exception:
            pass

    # ------------------------------------------------------------ 开关
    def switches(self) -> dict[str, bool]:
        row = self.store.one("SELECT snapshots_enabled,stats_enabled FROM diagnostic_settings WHERE singleton=1")
        return {"snapshots_enabled": bool(row["snapshots_enabled"]), "stats_enabled": bool(row["stats_enabled"])}

    def set_switches(self, snapshots_enabled: bool | None = None, stats_enabled: bool | None = None) -> dict[str, bool]:
        current = self.switches()
        snapshots = current["snapshots_enabled"] if snapshots_enabled is None else bool(snapshots_enabled)
        stats = current["stats_enabled"] if stats_enabled is None else bool(stats_enabled)
        with self.store.transaction(True) as conn:
            conn.execute("UPDATE diagnostic_settings SET snapshots_enabled=?,stats_enabled=? WHERE singleton=1", (int(snapshots), int(stats)))
        return self.switches()

    # ------------------------------------------------------------ trace（LT-OBS-6）
    def record_trace(self, request_id: str, stage: str, detail: dict | None = None, correlation_id: str | None = None) -> None:
        try:
            with self.store.transaction(True) as conn:
                conn.execute(
                    "INSERT INTO trace_events VALUES(?,?,?,?,?,?,?)",
                    (f"tev_{uuid.uuid4().hex}", request_id, stage, now(), json.dumps(detail, ensure_ascii=False) if detail else None, correlation_id, now()),
                )
        except Exception as exc:
            self._warn(f"trace write failed: {exc}")

    def trace(self, request_id: str) -> dict:
        stages = [
            {"stage": row["stage"], "timestamp": row["stage_timestamp"], "detail": json.loads(row["detail"]) if row["detail"] else None}
            for row in self.store.all("SELECT stage,stage_timestamp,detail FROM trace_events WHERE request_id=? ORDER BY stage_timestamp,id", (request_id,))
        ]
        if not stages:
            raise ApiError(404, "not_found", "No trace for this request_id")
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

    # ------------------------------------------------------------ 快照（LT-OBS-1）
    def capture_snapshot(self, request_id: str, deployment_id: str | None, model: str | None, upstream_url: str,
                         backend_model: str | None, http_status: int | None, latency_ms: float | None, error_summary: str | None) -> str | None:
        if not self.switches()["snapshots_enabled"]:
            return None
        try:
            snap_type = "upstream" if http_status is not None else "error"
            snap_id = f"snap_{uuid.uuid4().hex}"
            with self.store.transaction(True) as conn:
                conn.execute(
                    "INSERT INTO diagnostic_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (snap_id, request_id, now(), upstream_url, backend_model, http_status, latency_ms, (error_summary or "")[:256] or None, model, deployment_id, snap_type),
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

    # ------------------------------------------------------------ 统计（LT-OBS-2）
    def record_latency(self, deployment_id: str | None, model: str | None, status_code: int | None, latency_ms: float | None) -> None:
        if not self.switches()["stats_enabled"]:
            return
        try:
            status = str(status_code) if status_code is not None and status_code >= 100 else "upstream_error"
            hour = hour_of()
            error = 1 if (status_code is not None and status_code >= 400) or status == "upstream_error" else 0
            with self.store.transaction(True) as conn:
                conn.execute(
                    "INSERT INTO data_plane_stats VALUES(?,?,?,?,1,?,?) ON CONFLICT(stat_hour,deployment_id,model,status) DO UPDATE SET"
                    " request_count=request_count+1,error_count=error_count+?,updated_at=?",
                    (hour, deployment_id, model, status, error, now(), error, now()),
                )
                if latency_ms is not None:
                    conn.execute("INSERT INTO data_plane_latency_samples VALUES(?,?,?,?,?)", (hour, deployment_id, model, float(latency_ms), now()))
        except Exception as exc:
            self._warn(f"stats write failed: {exc}")

    def stats(self, since: str, until: str, deployment_id: str | None = None, model: str | None = None) -> dict:
        where = ["stat_hour>=?", "stat_hour<=?"]
        params: list[object] = [since[:13], until[:13]]
        if deployment_id: where.append("deployment_id IS ?"); params.append(deployment_id)
        if model: where.append("model IS ?"); params.append(model)
        rows = self.store.all(
            f"SELECT stat_hour,deployment_id,model,status,request_count,error_count FROM data_plane_stats WHERE {' AND '.join(where)}"
            " ORDER BY stat_hour,deployment_id,model,status", params)
        sample_where = " AND ".join(["stat_hour>=?", "stat_hour<=?"] + (["deployment_id IS ?"] if deployment_id else []) + (["model IS ?"] if model else []))
        sample_params = [since[:13], until[:13]] + ([deployment_id] if deployment_id else []) + ([model] if model else [])
        samples = self.store.all(
            f"SELECT stat_hour,deployment_id,model,latency_ms FROM data_plane_latency_samples WHERE {sample_where} ORDER BY stat_hour,deployment_id,model,latency_ms",
            sample_params)
        buckets: dict[tuple, dict] = {}
        for row in rows:
            key = (row["stat_hour"], row["deployment_id"], row["model"])
            bucket = buckets.setdefault(key, {"stat_hour": key[0], "deployment_id": key[1], "model": key[2],
                                              "status_breakdown": {}, "request_count": 0, "error_count": 0, "latencies": []})
            bucket["status_breakdown"][row["status"]] = bucket["status_breakdown"].get(row["status"], 0) + row["request_count"]
            bucket["request_count"] += row["request_count"]
            bucket["error_count"] += row["error_count"]
        for row in samples:
            key = (row["stat_hour"], row["deployment_id"], row["model"])
            bucket = buckets.setdefault(key, {"stat_hour": key[0], "deployment_id": key[1], "model": key[2],
                                              "status_breakdown": {}, "request_count": 0, "error_count": 0, "latencies": []})
            bucket["latencies"].append(row["latency_ms"])
        windows = []
        for key in sorted(buckets):
            b = buckets[key]
            latencies = sorted(b["latencies"])
            total = len(latencies)
            windows.append({
                "stat_hour": b["stat_hour"], "deployment_id": b["deployment_id"], "model": b["model"],
                "status_breakdown": b["status_breakdown"], "request_count": b["request_count"], "error_count": b["error_count"],
                "latency_p50_ms": _percentile(latencies, 50), "latency_p95_ms": _percentile(latencies, 95),
                "latency_min_ms": latencies[0] if latencies else None, "latency_max_ms": latencies[-1] if latencies else None,
                "latency_sum_ms": sum(latencies) if latencies else 0,
            })
        return {"windows": windows}

    # ------------------------------------------------------------ 注入（LT-OBS-5）
    def _validate(self, item: dict) -> dict:
        kind = item.get("type")
        if kind not in _TYPES:
            raise ApiError(400, "invalid_injection", f"unknown injection type: {kind}", param="type")
        enabled = bool(item.get("enabled"))
        config = item.get("config") or {}
        if not isinstance(config, dict):
            raise ApiError(400, "invalid_injection", "config must be an object", param="config")
        clean: dict[str, Any] = {}
        for field in _CONFIG_FIELDS[kind]:
            if field not in config:
                raise ApiError(400, "invalid_injection", f"missing config field: {field}", param=field)
            value = config[field]
            if field == "error_body":
                if not isinstance(value, str) or not value: raise ApiError(400, "invalid_injection", "error_body must be a non-empty string", param="error_body")
                if len(value.encode()) > 512: value = value.encode()[:512].decode("utf-8", "ignore")
                clean[field] = value
            elif field == "malformed_event_type":
                if value not in {"invalid_json", "unknown_event_type"}: raise ApiError(400, "invalid_injection", "unknown malformed_event_type", param="malformed_event_type")
                clean[field] = value
            else:
                low, high = _RANGES[field]
                if not isinstance(value, int) or isinstance(value, bool) or not (low <= value <= high):
                    raise ApiError(400, "invalid_injection", f"{field} out of range [{low},{high}]", param=field)
                clean[field] = value
        return {"type": kind, "config": clean, "enabled": bool(item.get("enabled"))}

    def set_injections(self, deployment_id: str, actor_items: list[dict]) -> list[dict]:
        if self.store.one("SELECT 1 FROM deployments WHERE id=?", (deployment_id,)) is None:
            raise ApiError(404, "not_found", f"Unknown deployment: {deployment_id}")
        validated = [self._validate(item) for item in actor_items]
        stamp = now()
        with self.store.transaction(True) as conn:
            for item in validated:
                kind, config, enabled = item["type"], item["config"], item["enabled"]
                columns = {"fault_status": 502 if kind == "fault_502" else (503 if kind == "fault_503" else None)}
                conn.execute(
                    f"""INSERT INTO diagnostic_injections VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(deployment_id,injection_type) DO UPDATE SET
                        fault_status=excluded.fault_status, fault_body=excluded.fault_body, delay_ms=excluded.delay_ms,
                        retry_after_sec=excluded.retry_after_sec, stream_terminate_after_events=excluded.stream_terminate_after_events,
                        malformed_after_events=excluded.malformed_after_events, malformed_event_type=excluded.malformed_event_type,
                        enabled=excluded.enabled, updated_at=excluded.updated_at""",
                    (f"inj_{uuid.uuid4().hex}", deployment_id, kind,
                     502 if kind == "fault_502" else (503 if kind == "fault_503" else None),
                     config.get("error_body"), config.get("delay_ms"), config.get("retry_after_sec"),
                     config.get("stream_terminate_after_events"), config.get("malformed_after_events"),
                     config.get("malformed_event_type"), int(enabled), stamp),
                )
        return self.injections(deployment_id)

    def injections(self, deployment_id: str) -> list[dict]:
        rows = self.store.all(
            "SELECT injection_type,fault_status,fault_body,delay_ms,retry_after_sec,stream_terminate_after_events,"
            "malformed_after_events,malformed_event_type,enabled,updated_at FROM diagnostic_injections WHERE deployment_id=?"
            " ORDER BY injection_type", (deployment_id,))
        items = []
        for row in rows:
            config = {}
            for field in _CONFIG_FIELDS.get(row["injection_type"], ()):
                config[field] = row[{ "error_body": "fault_body", "delay_ms": "delay_ms", "retry_after_sec": "retry_after_sec",
                                      "stream_terminate_after_events": "stream_terminate_after_events",
                                      "malformed_after_events": "malformed_after_events", "malformed_event_type": "malformed_event_type"}.get(field)]
            items.append({"type": row["injection_type"], "config": config, "enabled": bool(row["enabled"]), "updated_at": row["updated_at"]})
        return items

    def enabled_injection(self, deployment_id: str) -> dict | None:
        """返回当前应生效的**前置阶段**注入（fault_502→fault_503→rate_limit→delay 首个命中）。"""
        rows = {row["injection_type"]: row for row in self.store.all(
            "SELECT * FROM diagnostic_injections WHERE deployment_id=? AND enabled=1", (deployment_id,))}
        for kind in _PRE_CALL:
            row = rows.get(kind)
            if row: return dict(row)
        return None

    def enabled_stream_injection(self, deployment_id: str) -> dict | None:
        """返回当前应生效的**流阶段**注入（stream_terminate→malformed_event 首个命中）。"""
        rows = {row["injection_type"]: row for row in self.store.all(
            "SELECT * FROM diagnostic_injections WHERE deployment_id=? AND enabled=1", (deployment_id,))}
        for kind in ("stream_terminate", "malformed_event"):
            row = rows.get(kind)
            if row: return dict(row)
        return None

    def stream_wrapper(self, deployment_id: str, base_stream: Iterable[bytes]) -> Iterable[bytes]:
        cfg = self.enabled_stream_injection(deployment_id)
        if cfg is None:
            yield from base_stream
            return
        count = 0
        for chunk in base_stream:
            count += 1
            yield chunk
            if cfg["injection_type"] == "stream_terminate" and count >= (cfg["stream_terminate_after_events"] or 1):
                return
            if cfg["injection_type"] == "malformed_event" and count >= (cfg["malformed_after_events"] or 1):
                yield b"event: response.malformed\ndata: {\"broken\": json-is-not-valid-here\n\n"
                return

    # ------------------------------------------------------------ 保留期
    def cleanup(self, days: int = 7) -> None:
        cutoff = _iso(datetime.now(timezone.utc) - timedelta(days=days))
        try:
            with self.store.transaction(True) as conn:
                for table, column in (("diagnostic_snapshots", "captured_at"), ("trace_events", "created_at"),
                                      ("data_plane_latency_samples", "created_at"), ("data_plane_stats", "stat_hour")):
                    conn.execute(f"DELETE FROM {table} WHERE {column}<?", (cutoff,))
        except Exception as exc:
            self._warn(f"cleanup failed: {exc}")
