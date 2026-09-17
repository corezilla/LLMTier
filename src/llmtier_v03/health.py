from __future__ import annotations

from datetime import datetime, timezone

from .errors import ApiError
from .registry import FIXED_TIERS, Registry


def health_view(version: str) -> dict:
    return {"status": "ok", "version": version}


def readiness_view(registry: Registry) -> tuple[dict, int]:
    levels = {item["id"]: item for item in registry.list_service_levels()}
    models = []
    for tier in FIXED_TIERS:
        if tier not in levels:
            availability = "unavailable"
        else:
            candidates = registry.candidates(tier)
            healthy = sum(c.health == "healthy" for c in candidates)
            availability = "available" if healthy else ("degraded" if candidates else "unavailable")
        models.append({"id": tier, "availability": availability})
    status = "ready" if all(m["availability"] == "available" for m in models) else ("degraded" if any(m["availability"] != "unavailable" for m in models) else "not_ready")
    return {"status": status, "models": models}, (200 if status == "ready" else 503)


def apply_probe_result(registry: Registry, deployment_id: str, status: str, request_id: str, detail: str | None = None) -> dict:
    if status not in {"healthy", "degraded", "unhealthy", "unknown"}:
        raise ApiError(400, "invalid_request", "Invalid probe status")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with registry.store.transaction(True) as conn:
        if conn.execute("SELECT 1 FROM deployments WHERE id=?", (deployment_id,)).fetchone() is None:
            raise ApiError(404, "not_found", "Deployment not found")
        conn.execute("UPDATE deployments SET health=? WHERE id=?", (status, deployment_id))
        conn.execute("INSERT INTO probe_results VALUES(?,?,?,?,?) ON CONFLICT(deployment_id) DO UPDATE SET status=excluded.status,checked_at=excluded.checked_at,request_id=excluded.request_id,detail=excluded.detail", (deployment_id, status, now, request_id, detail))
    return {"deployment_id": deployment_id, "status": status, "checked_at": now, "request_id": request_id, "detail": detail}
