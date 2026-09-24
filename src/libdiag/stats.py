"""Feature: data-plane statistics (data_plane_stats / latency samples).

Composition point: record_latency consults the settings switch (SettingsDiagnostics).
"""
from __future__ import annotations

from util.store import Store

from .common import hour_of, now, percentile
from .settings import SettingsDiagnostics
from .traces import Warn


class StatsDiagnostics:
    def __init__(self, store: Store, settings: SettingsDiagnostics, warn: Warn):
        self.store = store
        self.settings = settings
        self._warn = warn

    def record_latency(self, deployment_id: str | None, model: str | None, status_code: int | None, latency_ms: float | None) -> None:
        if not self.settings.switches()["stats_enabled"]:
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
            breakdown = b["status_breakdown"]
            err4 = sum(count for status, count in breakdown.items() if str(status).isdigit() and 400 <= int(status) < 500)
            err5 = sum(count for status, count in breakdown.items() if (str(status).isdigit() and int(status) >= 500) or status == "upstream_error")
            windows.append({
                "stat_hour": b["stat_hour"], "deployment_id": b["deployment_id"], "model": b["model"],
                "status_breakdown": breakdown, "error_4xx_count": err4, "error_5xx_count": err5,
                "request_count": b["request_count"], "error_count": b["error_count"],
                "latency_p50_ms": percentile(latencies, 50), "latency_p95_ms": percentile(latencies, 95),
                "latency_min_ms": latencies[0] if latencies else None, "latency_max_ms": latencies[-1] if latencies else None,
                "latency_sum_ms": sum(latencies) if latencies else 0,
            })
        return {"windows": windows}
