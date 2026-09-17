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

    def mutate(self, actor: str, action: str, target: str, request_id: str, fn):
        try:
            result = fn()
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
        self.audit.record(actor, "deployment.probe", deployment["id"], status, request_id)
        return {"deployment_id": deployment["id"], "status": status, "checked_at": result["checked_at"], "may_have_incurred_cost": False}
