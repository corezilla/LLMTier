from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from http_api.errors import ApiError
from util.store import Store, txn


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class UsageRecorder:
    def __init__(self, store: Store): self.store = store

    def authorize_dispatch(self, principal: str, request_id: str, model: str, endpoint: str) -> None:
        stamp = now()
        with self.store.transaction(True) as conn:
            conn.execute("INSERT OR IGNORE INTO usage_obligations VALUES(?,?,?,?,?,?)", (principal, request_id, model, endpoint, stamp, stamp))
            if conn.execute("SELECT 1 FROM usage_heads WHERE principal_id=? AND request_id=?", (principal, request_id)).fetchone() is None:
                conn.execute("INSERT INTO usage_record_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (principal, request_id, 1, 0, model, endpoint, stamp, stamp, "unknown", "unavailable", None, None, None, None, None, None))
                conn.execute("INSERT INTO usage_heads VALUES(?,?,?,?)", (principal, request_id, 1, stamp))

    def bind_backend(self, principal: str, request_id: str, provider_id: str, deployment_id: str) -> None:
        # TODO(M003/D-PROVIDER-BINDING): the upstream provider X-Request-ID
        # (ProviderResult.provider_request_id) is not persisted. Persisting it needs
        # a nullable column on provider_request_bindings plus a real upgrade path
        # (Store.migrate() is init-only and pins EXPECTED_SCHEMA_VERSION=1) and a
        # post-complete() UPDATE, since bind_backend runs before the upstream call.
        # Deferred rather than shipped as a fresh-init-only migration.
        with self.store.transaction(True) as conn:
            conn.execute(
                "INSERT INTO provider_request_bindings VALUES(?,?,?,?,?) ON CONFLICT(principal_id,request_id) DO NOTHING",
                (principal, request_id, provider_id, deployment_id, now()),
            )

    def finish(self, principal: str, request_id: str, usage: dict[str, Any] | None, source_override: str | None = None) -> None:
        row = self.store.one("SELECT model,endpoint,recorded_at FROM usage_obligations WHERE principal_id=? AND request_id=?", (principal, request_id))
        if row is None: return
        stamp = now()
        current = self.store.one("SELECT head_record_version FROM usage_heads WHERE principal_id=? AND request_id=?", (principal, request_id))
        version = int(current["head_record_version"]) + 1
        measured = isinstance(usage, dict) and all(isinstance(usage.get(k), int) for k in ("input_tokens", "output_tokens", "total_tokens"))
        inp = usage.get("input_tokens") if measured else None
        out = usage.get("output_tokens") if measured else None
        total = usage.get("total_tokens") if measured else None
        details_i = usage.get("input_tokens_details", {}) if measured else {}
        details_o = usage.get("output_tokens_details", {}) if measured else {}
        with self.store.transaction(True) as conn:
            conn.execute("INSERT INTO usage_record_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (principal, request_id, version, 1, row["model"], row["endpoint"], row["recorded_at"], stamp, "measured" if measured else "unknown", source_override or ("provider" if measured else "unavailable"), inp, out, total, details_i.get("cached_tokens"), details_i.get("cache_write_tokens"), details_o.get("reasoning_tokens")))
            conn.execute("UPDATE usage_heads SET head_record_version=?,updated_at=? WHERE principal_id=? AND request_id=?", (version, stamp, principal, request_id))

    def _record(self, row) -> dict[str, Any]:
        return {"request_id": row["request_id"], "record_version": row["record_version"], "is_final": bool(row["is_final"]), "model": row["model"], "endpoint": row["endpoint"], "recorded_at": row["recorded_at"], "updated_at": row["updated_at"], "measurement_status": row["measurement_status"], "source": row["source"], "input_tokens": row["input_tokens"], "output_tokens": row["output_tokens"], "total_tokens": row["total_tokens"], "cached_input_tokens": row["cached_input_tokens"], "cache_write_tokens": row["cache_write_tokens"], "reasoning_tokens": row["reasoning_tokens"]}

    def page(self, principal: str, cursor: str | None, limit: int = 50, admin: bool = False, since: str | None = None, until: str | None = None, model: str | None = None, request_id: str | None = None) -> dict[str, Any]:
        try:
            return self._page(principal, cursor, limit, admin, since, until, model, request_id)
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(503, "usage_store_unavailable", "Usage store is unavailable") from exc

    def _page(self, principal: str, cursor: str | None, limit: int = 50, admin: bool = False, since: str | None = None, until: str | None = None, model: str | None = None, request_id: str | None = None) -> dict[str, Any]:
        try:
            start = datetime.fromisoformat((since or "").replace("Z", "+00:00")); end = datetime.fromisoformat((until or "").replace("Z", "+00:00"))
        except ValueError as exc: raise ApiError(400, "invalid_request", "from and to must be RFC3339 date-times") from exc
        if start >= end: raise ApiError(400, "invalid_request", "from must be before to")
        filters = json.dumps({"from": since, "to": until, "model": model, "request_id": request_id}, sort_keys=True, separators=(",", ":"))
        filter_digest = hashlib.sha256(filters.encode()).hexdigest()
        if cursor:
            snapshot = self.store.one("SELECT * FROM query_snapshots WHERE snapshot_id=?", (cursor.split(":", 1)[0],))
            if snapshot is None or datetime.fromisoformat(snapshot["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                raise ApiError(400, "cursor_expired", "Usage cursor is invalid or expired")
            if not admin and snapshot["principal_id"] != principal: raise ApiError(403, "permission_denied", "Cursor belongs to another principal")
            if snapshot["filter_digest"] != filter_digest: raise ApiError(400, "invalid_request", "Cursor filters do not match the original query")
            offset = int(cursor.split(":", 1)[1]) if ":" in cursor else 0
            sid = snapshot["snapshot_id"]
        else:
            sid, offset, stamp = f"snap_{uuid.uuid4().hex}", 0, now()
            expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            auth = hashlib.sha256(("admin" if admin else principal).encode()).hexdigest()
            with self.store.transaction(True) as conn:
                conn.execute("INSERT INTO query_snapshots VALUES(?,?,?,?,?,?,?)", (sid, principal, "usage", filter_digest, auth, stamp, expires))
                clauses, params = ["v.recorded_at>=?", "v.recorded_at<?"], [since, until]
                if not admin: clauses.append("h.principal_id=?"); params.append(principal)
                if model: clauses.append("v.model=?"); params.append(model)
                if request_id: clauses.append("v.request_id=?"); params.append(request_id)
                where = "WHERE " + " AND ".join(clauses)
                rows = conn.execute(f"SELECT v.* FROM usage_heads h JOIN usage_record_versions v ON v.principal_id=h.principal_id AND v.request_id=h.request_id AND v.record_version=h.head_record_version {where} ORDER BY v.recorded_at,v.request_id", params).fetchall()
                for ordinal, row in enumerate(rows):
                    conn.execute("INSERT INTO query_snapshot_items VALUES(?,?,?,?,?,?)", (sid, ordinal, row["request_id"], row["record_version"], json.dumps(self._record(row), separators=(",", ":")), None))
        rows = self.store.all("SELECT frozen_view_json FROM query_snapshot_items WHERE snapshot_id=? AND ordinal>=? ORDER BY ordinal LIMIT ?", (sid, offset, limit + 1))
        more = len(rows) > limit
        data = [json.loads(r["frozen_view_json"]) for r in rows[:limit]]
        snap = self.store.one("SELECT created_at FROM query_snapshots WHERE snapshot_id=?", (sid,))
        return {"data": data, "next_cursor": f"{sid}:{offset+limit}" if more else None, "has_more": more, "snapshot_id": sid, "snapshot_at": snap["created_at"]}

    def reset_usage(self, model: str | None = None, deployment_id: str | None = None, conn=None) -> dict[str, int]:
        """Delete usage records. Scopes by model (tier) and/or deployment_id.

        - model only:       delete all records for that tier (model column = tier name)
        - deployment_id only: delete all records joined to that deployment
        - both:             delete records that match both
        - neither:          delete ALL usage records (full reset)
        """
        with txn(self.store, conn) as conn:
            if model and deployment_id:
                conn.execute("""
                    CREATE TEMP TABLE _del_pairs AS
                    SELECT DISTINCT v.principal_id, v.request_id
                    FROM usage_record_versions v
                    JOIN usage_heads h ON h.principal_id=v.principal_id AND h.request_id=v.request_id AND h.head_record_version=v.record_version
                    JOIN provider_request_bindings b ON b.principal_id=v.principal_id AND b.request_id=v.request_id
                    WHERE v.model=? AND b.deployment_id=?
                """, (model, deployment_id))
            elif model:
                conn.execute("""
                    CREATE TEMP TABLE _del_pairs AS
                    SELECT DISTINCT v.principal_id, v.request_id
                    FROM usage_record_versions v
                    JOIN usage_heads h ON h.principal_id=v.principal_id AND h.request_id=v.request_id AND h.head_record_version=v.record_version
                    WHERE v.model=?
                """, (model,))
            elif deployment_id:
                conn.execute("""
                    CREATE TEMP TABLE _del_pairs AS
                    SELECT DISTINCT b.principal_id, b.request_id
                    FROM provider_request_bindings b
                    WHERE b.deployment_id=?
                """, (deployment_id,))
            else:
                conn.execute("CREATE TEMP TABLE _del_pairs AS SELECT DISTINCT principal_id, request_id FROM usage_record_versions")

            if model or deployment_id:
                deleted = conn.execute("SELECT COUNT(*) FROM _del_pairs").fetchone()[0]
                conn.execute("DELETE FROM usage_heads WHERE (principal_id, request_id) IN (SELECT principal_id, request_id FROM _del_pairs)")
                conn.execute("DELETE FROM usage_record_versions WHERE (principal_id, request_id) IN (SELECT principal_id, request_id FROM _del_pairs)")
                conn.execute("DELETE FROM usage_obligations WHERE (principal_id, request_id) IN (SELECT principal_id, request_id FROM _del_pairs)")
                conn.execute("DELETE FROM provider_request_bindings WHERE (principal_id, request_id) IN (SELECT principal_id, request_id FROM _del_pairs)")
                conn.execute("DROP TABLE _del_pairs")
            else:
                conn.execute("DELETE FROM usage_heads")
                conn.execute("DELETE FROM provider_request_bindings")
                deleted = conn.execute("DELETE FROM usage_record_versions").rowcount
                conn.execute("DELETE FROM usage_obligations")
                conn.execute("DROP TABLE IF EXISTS _del_pairs")

        return {"deleted": deleted}
