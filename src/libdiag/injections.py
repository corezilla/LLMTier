"""Feature: fault-injection config (diagnostic_injections) — validate + read/write."""
from __future__ import annotations

import uuid
from typing import Any

from http_api.errors import ApiError
from util.store import Store, txn

from .common import now

_TYPES = ("fault_502", "fault_503", "delay", "rate_limit", "stream_terminate", "malformed_event")
_PRE_CALL = ("fault_502", "fault_503", "rate_limit", "delay")
_STREAM = ("stream_terminate", "malformed_event")
_RANGES = {"delay_ms": (0, 60000), "retry_after_sec": (0, 300), "stream_terminate_after_events": (1, 10000), "malformed_after_events": (0, 10000)}
_CONFIG_FIELDS = {
    "fault_502": ("error_body",),
    "fault_503": ("error_body",),
    "delay": ("delay_ms",),
    "rate_limit": ("retry_after_sec",),
    "stream_terminate": ("stream_terminate_after_events",),
    "malformed_event": ("malformed_after_events", "malformed_event_type"),
}


class InjectionDiagnostics:
    def __init__(self, store: Store):
        self.store = store

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

    def set_injections(self, deployment_id: str, actor_items: list[dict], conn=None) -> list[dict]:
        if self.store.one("SELECT 1 FROM deployments WHERE id=?", (deployment_id,)) is None:
            raise ApiError(404, "not_found", f"Unknown deployment: {deployment_id}")
        if not isinstance(actor_items, list):
            raise ApiError(400, "invalid_injection", "Expected a list of injection items")
        validated = [self._validate(item) for item in actor_items]
        stamp = now()
        with txn(self.store, conn) as conn:
            for item in validated:
                kind, config, enabled = item["type"], item["config"], item["enabled"]
                conn.execute(
                    """INSERT INTO diagnostic_injections VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
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
        if self.store.one("SELECT 1 FROM deployments WHERE id=?", (deployment_id,)) is None:
            raise ApiError(404, "not_found", f"Unknown deployment: {deployment_id}")
        rows = self.store.all(
            "SELECT id,injection_type,fault_status,fault_body,delay_ms,retry_after_sec,stream_terminate_after_events,"
            "malformed_after_events,malformed_event_type,enabled,updated_at FROM diagnostic_injections WHERE deployment_id=?"
            " ORDER BY injection_type", (deployment_id,))
        items = []
        for row in rows:
            config = {}
            for field in _CONFIG_FIELDS.get(row["injection_type"], ()):
                config[field] = row[{ "error_body": "fault_body", "delay_ms": "delay_ms", "retry_after_sec": "retry_after_sec",
                                      "stream_terminate_after_events": "stream_terminate_after_events",
                                      "malformed_after_events": "malformed_after_events", "malformed_event_type": "malformed_event_type"}.get(field)]
            items.append({"id": row["id"], "deployment_id": deployment_id, "type": row["injection_type"], "config": config, "enabled": bool(row["enabled"]), "updated_at": row["updated_at"]})
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
        for kind in _STREAM:
            row = rows.get(kind)
            if row: return dict(row)
        return None
