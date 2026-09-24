from __future__ import annotations

import uuid
import json
from datetime import datetime, timedelta, timezone

from .audit import AuditLog
from .errors import ApiError, require
from .health import apply_probe_result
from .logs import OperationalLog
from .providers.local import LocalProvider
from .providers.openai import OpenAIProvider
from .registry import Registry
from .usage import UsageRecorder


class AdminService:
    def __init__(self, registry: Registry, audit: AuditLog, logs: OperationalLog, usage: UsageRecorder):
        self.registry, self.audit, self.logs, self.usage = registry, audit, logs, usage

    def page(self, data, actor: str, kind: str, cursor: str | None = None, limit: int = 100):
        limit = max(1, min(limit, 200))
        if cursor:
            sid, _, raw_offset = cursor.partition(":"); offset = int(raw_offset or "0")
            snapshot = self.registry.store.one("SELECT * FROM query_snapshots WHERE snapshot_id=? AND snapshot_kind=?", (sid, f"admin:{kind}"))
            if snapshot is None or snapshot["principal_id"] != actor or datetime.fromisoformat(snapshot["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc): raise ApiError(400, "invalid_request", "Admin cursor is invalid or expired")
        else:
            sid, offset = f"admin_{uuid.uuid4().hex}", 0
            stamp = datetime.now(timezone.utc); expires = stamp + timedelta(minutes=10)
            with self.registry.store.transaction(True) as conn:
                conn.execute("INSERT INTO query_snapshots VALUES(?,?,?,?,?,?,?)", (sid, actor, f"admin:{kind}", "all", actor, stamp.isoformat().replace("+00:00", "Z"), expires.isoformat().replace("+00:00", "Z")))
                for ordinal, item in enumerate(data): conn.execute("INSERT INTO query_snapshot_items VALUES(?,?,?,?,?,?)", (sid, ordinal, str(item.get("id", ordinal)), None, json.dumps(item, separators=(",", ":")), None))
        rows = self.registry.store.all("SELECT frozen_view_json FROM query_snapshot_items WHERE snapshot_id=? AND ordinal>=? ORDER BY ordinal LIMIT ?", (sid, offset, limit + 1)); more = len(rows) > limit
        return {"data": [json.loads(r["frozen_view_json"]) for r in rows[:limit]], "page": {"has_more": more, "next_cursor": f"{sid}:{offset+limit}" if more else None}}

    def stats(self, from_ts: str, to_ts: str, group_by: str) -> dict:
        require(group_by in {"tier", "deployment"}, 400, "invalid_request", "group_by must be 'tier' or 'deployment'")
        principal_filter = None
        if group_by == "tier":
            sql = """
              SELECT v.model AS key,
                     COUNT(*) AS calls,
                     SUM(CASE WHEN v.measurement_status='measured' THEN 1 ELSE 0 END) AS measured_calls,
                     SUM(CASE WHEN v.measurement_status='unknown'  THEN 1 ELSE 0 END) AS unknown_calls,
                     COALESCE(SUM(v.input_tokens), 0) AS input_tokens,
                     COALESCE(SUM(v.output_tokens), 0) AS output_tokens,
                     COALESCE(SUM(v.total_tokens), 0) AS total_tokens,
                     COALESCE(SUM(v.cached_input_tokens), 0) AS cached_tokens,
                     COALESCE(SUM(v.cache_write_tokens), 0) AS cache_write_tokens,
                     COALESCE(SUM(v.reasoning_tokens), 0) AS reasoning_tokens
              FROM usage_record_versions v
              JOIN usage_heads h ON h.principal_id=v.principal_id AND h.request_id=v.request_id AND h.head_record_version=v.record_version
              WHERE v.recorded_at>=? AND v.recorded_at<=?
                AND (? IS NULL OR v.principal_id=?)
              GROUP BY v.model
              ORDER BY calls DESC, total_tokens DESC, v.model ASC
            """
            rows = self.registry.store.all(sql, (from_ts, to_ts, principal_filter, principal_filter))
            data = [{"tier": r["key"], "calls": int(r["calls"] or 0), "measured_calls": int(r["measured_calls"] or 0), "unknown_calls": int(r["unknown_calls"] or 0),
                     "input_tokens": int(r["input_tokens"]), "output_tokens": int(r["output_tokens"]), "total_tokens": int(r["total_tokens"]),
                     "cached_tokens": int(r["cached_tokens"]), "cache_write_tokens": int(r["cache_write_tokens"]), "reasoning_tokens": int(r["reasoning_tokens"])} for r in rows]
        else:
            sql = """
              SELECT b.deployment_id AS deployment_id,
                     d.name AS deployment_name, d.backend_model AS backend_model,
                     p.id AS provider_id, p.name AS provider_name, p.kind AS provider_kind,
                     COUNT(*) AS calls,
                     SUM(CASE WHEN v.measurement_status='measured' THEN 1 ELSE 0 END) AS measured_calls,
                     SUM(CASE WHEN v.measurement_status='unknown'  THEN 1 ELSE 0 END) AS unknown_calls,
                     COALESCE(SUM(v.input_tokens), 0) AS input_tokens,
                     COALESCE(SUM(v.output_tokens), 0) AS output_tokens,
                     COALESCE(SUM(v.total_tokens), 0) AS total_tokens,
                     COALESCE(SUM(v.cached_input_tokens), 0) AS cached_tokens,
                     COALESCE(SUM(v.cache_write_tokens), 0) AS cache_write_tokens,
                     COALESCE(SUM(v.reasoning_tokens), 0) AS reasoning_tokens
              FROM usage_record_versions v
              JOIN usage_heads h ON h.principal_id=v.principal_id AND h.request_id=v.request_id AND h.head_record_version=v.record_version
              JOIN provider_request_bindings b ON b.principal_id=v.principal_id AND b.request_id=v.request_id
              JOIN deployments d ON d.id=b.deployment_id
              JOIN providers p ON p.id=b.provider_id
              WHERE v.recorded_at>=? AND v.recorded_at<=?
                AND (? IS NULL OR v.principal_id=?)
              GROUP BY b.deployment_id, d.name, d.backend_model, p.id, p.name, p.kind
              ORDER BY calls DESC, total_tokens DESC, b.deployment_id ASC
            """
            rows = self.registry.store.all(sql, (from_ts, to_ts, principal_filter, principal_filter))
            data = [{"deployment_id": r["deployment_id"], "deployment_name": r["deployment_name"], "backend_model": r["backend_model"],
                     "provider_id": r["provider_id"], "provider_name": r["provider_name"], "provider_kind": r["provider_kind"],
                     "calls": int(r["calls"] or 0), "measured_calls": int(r["measured_calls"] or 0), "unknown_calls": int(r["unknown_calls"] or 0),
                     "input_tokens": int(r["input_tokens"]), "output_tokens": int(r["output_tokens"]), "total_tokens": int(r["total_tokens"]),
                     "cached_tokens": int(r["cached_tokens"]), "cache_write_tokens": int(r["cache_write_tokens"]), "reasoning_tokens": int(r["reasoning_tokens"])} for r in rows]
        return {"from": from_ts, "to": to_ts, "group_by": group_by, "data": data}

    def mutate(self, actor: str, action: str, target: str, request_id: str, fn, atomic: bool = True):
        # PF-MGMT-CONFIG: registry mutation and its audit row commit in one transaction.
        # atomic=False is used for operations with an external call (account usage
        # refresh) that must not hold the write transaction open.
        try:
            if atomic:
                with self.registry.store.transaction(True) as conn:
                    result = fn(conn)
                    self.audit.record(actor, action, target, "success", request_id, conn=conn)
            else:
                result = fn(None)
                self.audit.record(actor, action, target, "success", request_id)
            self.logs.record("info", "admin", action, f"{action} succeeded for {target}", request_id)
            return result
        except Exception:
            self.audit.record(actor, action, target, "failed", request_id)
            self.logs.record("warning", "admin", action, f"{action} failed for {target}", request_id)
            raise

    def probe(self, actor: str, body: dict, request_id: str) -> dict:
        require(body.get("confirm_external_call") is True and set(body) == {"deployment_id", "confirm_external_call"}, 400, "confirmation_required", "Probe requires explicit confirmation")
        deployment = self.registry.get_deployment(body["deployment_id"])[0]
        provider = self.registry.get_provider(deployment["provider_id"])[0]
        row = self.registry.store.one("SELECT secret_ref FROM providers WHERE id=?", (provider["id"],))
        adapter = (LocalProvider if provider["kind"] == "local" else OpenAIProvider)(provider["endpoint"], row["secret_ref"] if row else None)
        status = "healthy" if adapter.probe() else "unhealthy"
        result = apply_probe_result(self.registry, deployment["id"], status, request_id)
        self.audit.record(actor, "deployment.probe", deployment["id"], "success", request_id)
        return {"deployment_id": deployment["id"], "status": status, "checked_at": result["checked_at"], "may_have_incurred_cost": False}

    def list_provider_models(self, provider_id: str) -> list[str]:
        provider = self.registry.get_provider(provider_id)[0]
        row = self.registry.store.one("SELECT secret_ref FROM providers WHERE id=?", (provider_id,))
        adapter = (LocalProvider if provider["kind"] == "local" else OpenAIProvider)(provider["endpoint"], row["secret_ref"] if row else None)
        return adapter.list_models()
