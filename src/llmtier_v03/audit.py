from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .store import Store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AuditLog:
    def __init__(self, store: Store): self.store = store

    def record(self, actor: str, action: str, target: str, result: str, request_id: str | None = None) -> None:
        self.store.connection().execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)", (f"audit_{uuid.uuid4().hex[:16]}", actor, action, target, result, _now(), request_id))

    def page(self, limit: int = 50) -> dict:
        rows = self.store.all("SELECT * FROM audit_events ORDER BY created_at DESC,id DESC LIMIT ?", (max(1, min(limit, 200)),))
        return {"data": [{k: r[k] for k in ("id", "actor", "action", "target", "result", "created_at", "request_id")} for r in rows], "page": {"has_more": False, "next_cursor": None}}
