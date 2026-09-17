from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from .store import Store


_SENSITIVE = re.compile(r"(?i)(authorization|bearer\s+\S+|secret|api[_-]?key|token\s*[=:]\s*\S+)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class OperationalLog:
    def __init__(self, store: Store): self.store = store

    def record(self, level: str, module: str, event: str, message: str, request_id: str | None = None) -> None:
        safe = _SENSITIVE.sub("[REDACTED]", str(message).replace("\n", " "))[:512]
        self.store.connection().execute("INSERT INTO operational_logs VALUES(?,?,?,?,?,?,?)", (f"log_{uuid.uuid4().hex[:16]}", _now(), level, module, event, safe, request_id))

    def page(self, limit: int = 50, level: str | None = None, module: str | None = None, request_id: str | None = None, since: str | None = None, until: str | None = None) -> dict:
        where, params = ["created_at>=?", "created_at<?"], [since, until]
        for column, value in (("level", level), ("module", module), ("request_id", request_id)):
            if value: where.append(f"{column}=?"); params.append(value)
        sql = "SELECT * FROM operational_logs" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY created_at DESC,id DESC LIMIT ?"
        params.append(max(1, min(limit, 200)))
        return {"data": [dict(r) for r in self.store.all(sql, params)], "page": {"has_more": False, "next_cursor": None}}
