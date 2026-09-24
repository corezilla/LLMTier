from __future__ import annotations

import json
import hashlib
import sqlite3
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from http_api.errors import ApiError, require
from util.store import Store, txn


FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")
CAPABILITY_KEYS = {"responses", "embeddings", "tools", "structured_outputs", "input_modalities", "output_modalities", "context_window", "max_output_tokens", "embedding_space_id", "embedding_dimensions", "embedding_max_batch_inputs", "embedding_max_input_tokens"}
EMPTY_CAPABILITIES = {"responses": False, "embeddings": False, "tools": False, "structured_outputs": False, "input_modalities": [], "output_modalities": [], "context_window": None, "max_output_tokens": None, "embedding_space_id": None, "embedding_dimensions": None, "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
USAGE_PROVIDERS = {"none", "local", "minimax", "volc"}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _etag(resource_id: str, version: int) -> str:
    return f'"{resource_id}.v{version}"'


def _bool(value: Any) -> bool:
    return bool(int(value))


@dataclass(frozen=True, slots=True)
class Candidate:
    level_id: str
    deployment_id: str
    provider_id: str
    endpoint: str
    backend_model: str
    kind: str
    health: str
    ordinal: int


class Registry:
    def __init__(self, store: Store):
        self.store = store

    def bootstrap_settings(self, settings_path: str | None) -> None:
        meta = self.store.one("SELECT bootstrap_sha256 FROM schema_meta WHERE singleton=1")
        if meta and meta["bootstrap_sha256"]:
            return
        if not settings_path:
            raise ApiError(503, "bootstrap_required", "An explicit settings path is required for an empty store")
        path = Path(settings_path)
        try:
            raw = path.read_bytes(); config = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiError(503, "bootstrap_invalid", "Bootstrap settings cannot be read or parsed") from exc
        require(set(config) == {"providers", "deployments", "service_levels"}, 503, "bootstrap_invalid", "Bootstrap settings have unknown or missing sections")
        providers = config["providers"]; deployments = config["deployments"]; levels = config["service_levels"]
        require(all(isinstance(x, dict) for x in providers + deployments + levels), 503, "bootstrap_invalid", "Bootstrap entries must be objects")
        provider_ids = {x.get("id") for x in providers}; deployment_ids = {x.get("id") for x in deployments}
        require(None not in provider_ids and len(provider_ids) == len(providers), 503, "bootstrap_invalid", "Provider IDs must be unique")
        require(None not in deployment_ids and len(deployment_ids) == len(deployments), 503, "bootstrap_invalid", "Deployment IDs must be unique")
        require(all(x.get("provider_id") in provider_ids for x in deployments), 503, "bootstrap_invalid", "Deployment provider reference is invalid")
        require(all(x.get("id") in FIXED_TIERS and all(d in deployment_ids for d in x.get("deployment_ids", [])) for x in levels), 503, "bootstrap_invalid", "Service level reference is invalid")
        for item in providers:
            ref = item.get("secret_ref")
            if ref and ref.startswith("env:"): require(bool(os.environ.get(ref[4:])), 503, "bootstrap_invalid", "Provider secret environment reference is unavailable")
            if ref and ref.startswith("file:"): require(Path(ref[5:]).is_file(), 503, "bootstrap_invalid", "Provider secret file reference is unavailable")
            require(not ref or ref.startswith(("env:", "file:")), 503, "bootstrap_invalid", "Unsupported provider secret reference")
        digest = hashlib.sha256(raw).hexdigest()
        try:
            with self.store.transaction(True) as conn:
                for item in providers:
                    require(set(item) == {"id", "name", "kind", "endpoint", "secret_ref", "enabled"}, 503, "bootstrap_invalid", "Invalid provider entry")
                    conn.execute("INSERT INTO providers VALUES(?,?,?,?,?,?,?)", (item["id"], item["name"], item["kind"], item["endpoint"], item["secret_ref"], int(item["enabled"]), 1))
                    self._write_usage_profile(conn, item["id"], self._usage_values(None, item["kind"]), 1)
                for item in deployments:
                    require(set(item) == {"id", "name", "provider_id", "backend_model", "capabilities", "enabled"}, 503, "bootstrap_invalid", "Invalid deployment entry")
                    caps = item["capabilities"]
                    require(isinstance(caps, dict) and set(caps) <= CAPABILITY_KEYS and all(isinstance(caps.get(k), bool) for k in ("responses", "embeddings", "tools", "structured_outputs")), 503, "bootstrap_invalid", "Invalid deployment capabilities")
                    normalized_caps = {**EMPTY_CAPABILITIES, **caps}
                    conn.execute("INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)", (item["id"], item["name"], item["provider_id"], item["backend_model"], json.dumps(normalized_caps, separators=(",", ":")), int(item["enabled"]), "unknown", 1))
                    conn.execute("INSERT INTO deployment_runtime_profiles(deployment_id) VALUES(?)", (item["id"],))
                configured = {x["id"]: x for x in levels}
                empty = {"responses": False, "embeddings": False, "tools": False, "structured_outputs": False, "input_modalities": [], "output_modalities": [], "context_window": None, "max_output_tokens": None, "embedding_space_id": None, "embedding_dimensions": None, "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
                for tier in FIXED_TIERS:
                    item = configured.get(tier, {"id": tier, "deployment_ids": [], "enabled": True})
                    capabilities = self._capability_intersection_direct(conn, item["deployment_ids"]) if item["deployment_ids"] else empty
                    conn.execute("INSERT INTO service_levels VALUES(?,?,?,?)", (tier, int(item.get("enabled", True)), json.dumps(capabilities, separators=(",", ":")), 1))
                    conn.executemany("INSERT INTO service_level_deployments VALUES(?,?,?)", [(tier, did, i) for i, did in enumerate(item["deployment_ids"])])
                conn.execute("UPDATE schema_meta SET bootstrap_sha256=? WHERE singleton=1", (digest,))
                conn.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)", (f"audit_{uuid.uuid4().hex[:16]}", "bootstrap", "registry.bootstrap", "store", "success", __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00','Z'), None))
        except ApiError: raise
        except Exception as exc:
            raise ApiError(503, "bootstrap_invalid", "Bootstrap transaction failed") from exc

    @staticmethod
    def _capability_intersection_direct(conn, deployment_ids: list[str]) -> dict[str, Any]:
        rows = [conn.execute("SELECT capabilities_json FROM deployments WHERE id=?", (rid,)).fetchone() for rid in deployment_ids]
        require(all(rows), 503, "bootstrap_invalid", "Unknown deployment in service level")
        values = [json.loads(r["capabilities_json"]) for r in rows]
        keys = set.intersection(*(set(v) for v in values)) if values else set()
        result = {}
        for key in keys:
            items = [v[key] for v in values]
            if all(isinstance(v, bool) for v in items): result[key] = all(items)
            elif all(v == items[0] for v in items): result[key] = items[0]
        return result

    def ensure_fixed_tiers(self) -> None:
        empty = {"responses": False, "embeddings": False, "tools": False, "structured_outputs": False, "input_modalities": [], "output_modalities": [], "context_window": None, "max_output_tokens": None, "embedding_space_id": None, "embedding_dimensions": None, "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
        with self.store.transaction(True) as conn:
            for tier in FIXED_TIERS:
                conn.execute("INSERT OR IGNORE INTO service_levels VALUES(?,?,?,?)", (tier, 1, json.dumps(empty, separators=(",", ":")), 1))

    def create_provider(self, body: dict[str, Any], conn: sqlite3.Connection | None = None) -> tuple[dict[str, Any], str]:
        required = {"name", "kind", "endpoint", "secret_ref", "enabled"}
        require(required <= set(body) and set(body) <= required | {"usage"}, 400, "invalid_request", "Provider fields are incomplete or unknown")
        require(body["kind"] in {"cloud", "local"}, 400, "invalid_request", "Invalid provider kind", "kind")
        usage = self._usage_values(body.get("usage"), body["kind"])
        rid = _id("provider")
        try:
            with txn(self.store, conn) as conn:
                conn.execute("INSERT INTO providers VALUES(?,?,?,?,?,?,?)", (rid, body["name"], body["kind"], body["endpoint"], body["secret_ref"], int(body["enabled"]), 1))
                self._write_usage_profile(conn, rid, usage, 1)
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise ApiError(409, "resource_conflict", "Provider name already exists") from exc
            raise
        return self.get_provider(rid)

    def get_provider(self, rid: str) -> tuple[dict[str, Any], str]:
        row = self.store.one("SELECT * FROM providers WHERE id=?", (rid,))
        if row is None:
            raise ApiError(404, "not_found", "Provider not found")
        profile = self.store.one("SELECT * FROM provider_usage_profiles WHERE provider_id=?", (rid,))
        usage = self._usage_view(profile, row["kind"])
        totals = self.store.one(
            "SELECT count(*) calls,count(v.input_tokens) input_known,count(v.output_tokens) output_known,count(v.total_tokens) total_known,sum(v.input_tokens) input_tokens,sum(v.output_tokens) output_tokens,sum(v.total_tokens) total_tokens "
            "FROM provider_request_bindings b JOIN usage_heads h ON h.principal_id=b.principal_id AND h.request_id=b.request_id "
            "JOIN usage_record_versions v ON v.principal_id=h.principal_id AND v.request_id=h.request_id AND v.record_version=h.head_record_version WHERE b.provider_id=?",
            (rid,),
        )
        calls = int(totals["calls"] or 0)
        view = {"id": row["id"], "name": row["name"], "kind": row["kind"], "endpoint": row["endpoint"], "has_secret": bool(row["secret_ref"]), "enabled": _bool(row["enabled"]), "usage": usage, "request_usage": {"calls": calls, "input_tokens": totals["input_tokens"] if calls and totals["input_known"] == calls else None, "output_tokens": totals["output_tokens"] if calls and totals["output_known"] == calls else None, "total_tokens": totals["total_tokens"] if calls and totals["total_known"] == calls else None}, "version": row["version"]}
        return view, _etag(row["id"], row["version"])

    def list_providers(self) -> list[dict[str, Any]]:
        return [self.get_provider(row["id"])[0] for row in self.store.all("SELECT id FROM providers ORDER BY name,id")]

    def update_provider(self, rid: str, body: dict[str, Any], if_match: str | None, conn: sqlite3.Connection | None = None) -> tuple[dict[str, Any], str]:
        allowed = {"name", "kind", "endpoint", "secret_ref", "enabled", "usage"}
        require(body and set(body) <= allowed, 400, "invalid_request", "Unknown or empty provider patch")
        with txn(self.store, conn) as conn:
            row = conn.execute("SELECT * FROM providers WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Provider not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Provider version changed", extra={"current_version": row["version"]})
            values = {k: row[k] for k in ("name", "kind", "endpoint", "secret_ref", "enabled")}
            values.update({k: v for k, v in body.items() if k != "usage"})
            version = row["version"] + 1
            conn.execute("UPDATE providers SET name=?,kind=?,endpoint=?,secret_ref=?,enabled=?,version=? WHERE id=?", (values["name"], values["kind"], values["endpoint"], values["secret_ref"], int(values["enabled"]), version, rid))
            current = conn.execute("SELECT * FROM provider_usage_profiles WHERE provider_id=?", (rid,)).fetchone()
            usage = self._usage_values(body.get("usage"), values["kind"], current)
            self._write_usage_profile(conn, rid, usage, int(current["version"] + 1) if current else 1)
            if "usage" in body:
                conn.execute("DELETE FROM provider_usage_snapshots WHERE provider_id=?", (rid,))
        return self.get_provider(rid)

    @staticmethod
    def _usage_values(value: Any, kind: str, current=None) -> dict[str, Any]:
        defaults = {
            "usage_provider": "local" if kind == "local" else "none",
            "usage_api_key_ref": None,
            "usage_access_key_ref": None,
            "usage_secret_key_ref": None,
            "max_concurrent_requests": 1,
            "min_request_interval_ms": 0,
            "requests_per_minute": 0,
        }
        if current is not None:
            defaults.update({key: current[key] for key in defaults})
        if value is None:
            return defaults
        require(isinstance(value, dict) and set(value) <= set(defaults), 400, "invalid_request", "Unknown provider usage field", "usage")
        defaults.update(value)
        require(defaults["usage_provider"] in USAGE_PROVIDERS, 400, "invalid_request", "Unsupported usage provider", "usage.usage_provider")
        for key in ("usage_api_key_ref", "usage_access_key_ref", "usage_secret_key_ref"):
            ref = defaults[key]
            require(ref is None or (isinstance(ref, str) and ref.startswith(("env:", "file:"))), 400, "invalid_request", "Credential references must use env: or file:", f"usage.{key}")
        for key, minimum in (("max_concurrent_requests", 1), ("min_request_interval_ms", 0), ("requests_per_minute", 0)):
            require(isinstance(defaults[key], int) and defaults[key] >= minimum, 400, "invalid_request", "Invalid provider account limit", f"usage.{key}")
        return defaults

    @staticmethod
    def _write_usage_profile(conn, provider_id: str, value: dict[str, Any], version: int) -> None:
        conn.execute(
            "INSERT INTO provider_usage_profiles VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(provider_id) DO UPDATE SET "
            "usage_provider=excluded.usage_provider,usage_api_key_ref=excluded.usage_api_key_ref,usage_access_key_ref=excluded.usage_access_key_ref,usage_secret_key_ref=excluded.usage_secret_key_ref,max_concurrent_requests=excluded.max_concurrent_requests,min_request_interval_ms=excluded.min_request_interval_ms,requests_per_minute=excluded.requests_per_minute,version=excluded.version",
            (provider_id, value["usage_provider"], value["usage_api_key_ref"], value["usage_access_key_ref"], value["usage_secret_key_ref"], value["max_concurrent_requests"], value["min_request_interval_ms"], value["requests_per_minute"], version),
        )

    @staticmethod
    def _usage_view(row, kind: str) -> dict[str, Any]:
        if row is None:
            return {"usage_provider": "local" if kind == "local" else "none", "has_usage_api_key": False, "has_usage_access_key": False, "has_usage_secret_key": False, "max_concurrent_requests": 1, "min_request_interval_ms": 0, "requests_per_minute": 0}
        return {"usage_provider": row["usage_provider"], "has_usage_api_key": row["usage_api_key_ref"] is not None, "has_usage_access_key": row["usage_access_key_ref"] is not None, "has_usage_secret_key": row["usage_secret_key_ref"] is not None, "max_concurrent_requests": row["max_concurrent_requests"], "min_request_interval_ms": row["min_request_interval_ms"], "requests_per_minute": row["requests_per_minute"]}

    def delete_provider(self, rid: str, if_match: str | None, conn: sqlite3.Connection | None = None) -> None:
        with txn(self.store, conn) as conn:
            row = conn.execute("SELECT version FROM providers WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Provider not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Provider version changed", extra={"current_version": row["version"]})
            if conn.execute("SELECT 1 FROM deployments WHERE provider_id=? LIMIT 1", (rid,)).fetchone():
                raise ApiError(409, "resource_in_use", "Provider is referenced by a deployment")
            conn.execute("DELETE FROM providers WHERE id=?", (rid,))

    def create_deployment(self, body: dict[str, Any], conn: sqlite3.Connection | None = None) -> tuple[dict[str, Any], str]:
        required = {"name", "provider_id", "backend_model", "capabilities", "enabled"}
        require(set(body) == required, 400, "invalid_request", "Deployment fields are incomplete or unknown")
        self._validate_capabilities(body["capabilities"])
        require(self.store.one("SELECT 1 FROM providers WHERE id=?", (body["provider_id"],)) is not None, 400, "invalid_request", "Unknown provider", "provider_id")
        rid = _id("deployment")
        try:
            with txn(self.store, conn) as conn:
                conn.execute("INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)", (rid, body["name"], body["provider_id"], body["backend_model"], json.dumps(body["capabilities"], separators=(",", ":")), int(body["enabled"]), "unknown", 1))
                conn.execute("INSERT INTO deployment_runtime_profiles(deployment_id) VALUES(?)", (rid,))
        except Exception as exc:
            if "UNIQUE" in str(exc): raise ApiError(409, "resource_conflict", "Deployment name already exists") from exc
            raise
        return self.get_deployment(rid)

    def get_deployment(self, rid: str) -> tuple[dict[str, Any], str]:
        row = self.store.one("SELECT * FROM deployments WHERE id=?", (rid,))
        if row is None: raise ApiError(404, "not_found", "Deployment not found")
        view = {"id": row["id"], "name": row["name"], "provider_id": row["provider_id"], "backend_model": row["backend_model"], "capabilities": json.loads(row["capabilities_json"]), "enabled": _bool(row["enabled"]), "health": row["health"], "version": row["version"]}
        return view, _etag(row["id"], row["version"])

    def list_deployments(self) -> list[dict[str, Any]]:
        return [self.get_deployment(r["id"])[0] for r in self.store.all("SELECT id FROM deployments ORDER BY name,id")]

    def update_deployment(self, rid: str, body: dict[str, Any], if_match: str | None, conn: sqlite3.Connection | None = None) -> tuple[dict[str, Any], str]:
        allowed = {"name", "provider_id", "backend_model", "capabilities", "enabled"}
        require(body and set(body) <= allowed, 400, "invalid_request", "Unknown or empty deployment patch")
        if "capabilities" in body: self._validate_capabilities(body["capabilities"])
        with txn(self.store, conn) as conn:
            row = conn.execute("SELECT * FROM deployments WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Deployment not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Deployment version changed", extra={"current_version": row["version"]})
            values = {"name": row["name"], "provider_id": row["provider_id"], "backend_model": row["backend_model"], "capabilities": json.loads(row["capabilities_json"]), "enabled": _bool(row["enabled"])}
            values.update(body)
            require(conn.execute("SELECT 1 FROM providers WHERE id=?", (values["provider_id"],)).fetchone() is not None, 400, "invalid_request", "Unknown provider", "provider_id")
            version = row["version"] + 1
            conn.execute("UPDATE deployments SET name=?,provider_id=?,backend_model=?,capabilities_json=?,enabled=?,version=? WHERE id=?", (values["name"], values["provider_id"], values["backend_model"], json.dumps(values["capabilities"], separators=(",", ":")), int(values["enabled"]), version, rid))
            if "capabilities" in body:
                # RULE-MGMT-CAPS: a deployment capability change recomputes every bound tier's
                # intersection and rejects the edit when a tier can no longer be satisfied.
                bound = [r["level_id"] for r in conn.execute("SELECT DISTINCT level_id FROM service_level_deployments WHERE deployment_id=?", (rid,))]
                for level_id in bound:
                    ids = [r["deployment_id"] for r in conn.execute("SELECT deployment_id FROM service_level_deployments WHERE level_id=? ORDER BY ordinal", (level_id,))]
                    capabilities = self._capability_intersection(ids)
                    self._validate_level(level_id, ids, capabilities)
                    conn.execute("UPDATE service_levels SET capabilities_json=?,version=version+1 WHERE id=?", (json.dumps(capabilities, separators=(",", ":")), level_id))
        return self.get_deployment(rid)

    def delete_deployment(self, rid: str, if_match: str | None, conn: sqlite3.Connection | None = None) -> None:
        with txn(self.store, conn) as conn:
            row = conn.execute("SELECT version FROM deployments WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Deployment not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Deployment version changed", extra={"current_version": row["version"]})
            if conn.execute("SELECT 1 FROM service_level_deployments WHERE deployment_id=? LIMIT 1", (rid,)).fetchone():
                raise ApiError(409, "resource_in_use", "Deployment is referenced by a service level")
            conn.execute("DELETE FROM deployments WHERE id=?", (rid,))

    def _capability_intersection(self, deployment_ids: list[str]) -> dict[str, Any]:
        # E-MGMT-INVALID: an unknown deployment reference is a 400, not a 404.
        values: list[dict[str, Any]] = []
        for rid in deployment_ids:
            row = self.store.one("SELECT capabilities_json FROM deployments WHERE id=?", (rid,))
            if row is None:
                raise ApiError(400, "invalid_request", f"Unknown deployment: {rid}", "deployment_ids")
            values.append(json.loads(row["capabilities_json"]))
        keys = set.intersection(*(set(v) for v in values)) if values else set()
        result: dict[str, Any] = {}
        for key in keys:
            items = [v[key] for v in values]
            if all(isinstance(v, bool) for v in items): result[key] = all(items)
            elif all(v == items[0] for v in items): result[key] = items[0]
        return result

    @staticmethod
    def _validate_capabilities(value: Any) -> None:
        require(isinstance(value, dict) and set(value) == CAPABILITY_KEYS, 400, "invalid_request", "Capabilities are incomplete or unknown", "capabilities")
        require(all(isinstance(value[k], bool) for k in ("responses", "embeddings", "tools", "structured_outputs")), 400, "invalid_request", "Capability flags must be boolean", "capabilities")

    def _validate_level(self, level_id: str, deployment_ids: list[str], capabilities: dict[str, Any]) -> None:
        require(bool(deployment_ids), 400, "invalid_request", "A service level requires at least one deployment", "deployment_ids")
        require(set(capabilities) == CAPABILITY_KEYS, 409, "capability_conflict", "Bound deployments do not have one compatible capability set")
        if level_id == "Embedding-v1":
            require(capabilities.get("embeddings") is True and capabilities.get("responses") is False, 409, "embedding_space_conflict", "Embedding-v1 requires embedding-only deployments")
            require(capabilities.get("embedding_space_id") == "bge-m3-dense-1024-v1" and capabilities.get("embedding_dimensions") == [1024], 409, "embedding_space_conflict", "Embedding-v1 requires the frozen BGE-M3 vector space")
            require(capabilities.get("embedding_max_batch_inputs") == 32 and capabilities.get("embedding_max_input_tokens") == 8192, 409, "embedding_space_conflict", "Embedding-v1 limits do not match the frozen contract")
        else:
            require(capabilities.get("responses") is True, 409, "capability_conflict", "Inference Tier requires Responses support")

    def create_service_level(self, body: dict[str, Any], conn: sqlite3.Connection | None = None) -> tuple[dict[str, Any], str]:
        require(set(body) == {"id", "deployment_ids", "enabled"}, 400, "invalid_request", "Service level fields are incomplete or unknown")
        require(body["id"] in FIXED_TIERS, 400, "invalid_request", "Service level ID is not a fixed Tier", "id")
        capabilities = self._capability_intersection(body["deployment_ids"])
        self._validate_level(body["id"], body["deployment_ids"], capabilities)
        try:
            with txn(self.store, conn) as conn:
                conn.execute("INSERT INTO service_levels VALUES(?,?,?,?)", (body["id"], int(body["enabled"]), json.dumps(capabilities, separators=(",", ":")), 1))
                conn.executemany("INSERT INTO service_level_deployments VALUES(?,?,?)", [(body["id"], did, i) for i, did in enumerate(body["deployment_ids"])])
        except Exception as exc:
            if "UNIQUE" in str(exc): raise ApiError(409, "resource_conflict", "Service level already exists") from exc
            raise
        return self.get_service_level(body["id"])

    def get_service_level(self, rid: str) -> tuple[dict[str, Any], str]:
        row = self.store.one("SELECT * FROM service_levels WHERE id=?", (rid,))
        if row is None: raise ApiError(404, "not_found", "Service level not found")
        ids = [r["deployment_id"] for r in self.store.all("SELECT deployment_id FROM service_level_deployments WHERE level_id=? ORDER BY ordinal", (rid,))]
        view = {"id": row["id"], "deployment_ids": ids, "enabled": _bool(row["enabled"]), "capabilities": json.loads(row["capabilities_json"]), "version": row["version"]}
        return view, _etag(row["id"], row["version"])

    def list_service_levels(self) -> list[dict[str, Any]]:
        present = {r["id"] for r in self.store.all("SELECT id FROM service_levels")}
        return [self.get_service_level(rid)[0] for rid in FIXED_TIERS if rid in present]

    def update_service_level(self, rid: str, body: dict[str, Any], if_match: str | None, conn: sqlite3.Connection | None = None) -> tuple[dict[str, Any], str]:
        require(body and set(body) <= {"deployment_ids", "enabled"}, 400, "invalid_request", "Unknown or empty service level patch")
        with txn(self.store, conn) as conn:
            row = conn.execute("SELECT * FROM service_levels WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Service level not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Service level version changed", extra={"current_version": row["version"]})
            current_ids = [r["deployment_id"] for r in conn.execute("SELECT deployment_id FROM service_level_deployments WHERE level_id=? ORDER BY ordinal", (rid,))]
            ids = body.get("deployment_ids", current_ids)
            capabilities = self._capability_intersection(ids)
            self._validate_level(rid, ids, capabilities)
            enabled = body.get("enabled", _bool(row["enabled"]))
            version = row["version"] + 1
            conn.execute("UPDATE service_levels SET enabled=?,capabilities_json=?,version=? WHERE id=?", (int(enabled), json.dumps(capabilities, separators=(",", ":")), version, rid))
            if "deployment_ids" in body:
                conn.execute("DELETE FROM service_level_deployments WHERE level_id=?", (rid,))
                conn.executemany("INSERT INTO service_level_deployments VALUES(?,?,?)", [(rid, did, i) for i, did in enumerate(ids)])
        return self.get_service_level(rid)

    def delete_service_level(self, rid: str, if_match: str | None, conn: sqlite3.Connection | None = None) -> None:
        raise ApiError(409, "fixed_service_level", "Fixed Tier service levels cannot be deleted")

    def candidates(self, level_id: str) -> list[Candidate]:
        rows = self.store.all("""
          SELECT sld.level_id,d.id deployment_id,p.id provider_id,p.endpoint,d.backend_model,p.kind,d.health,sld.ordinal
          FROM service_level_deployments sld JOIN service_levels sl ON sl.id=sld.level_id
          JOIN deployments d ON d.id=sld.deployment_id JOIN providers p ON p.id=d.provider_id
          WHERE sld.level_id=? AND sl.enabled=1 AND d.enabled=1 AND p.enabled=1 ORDER BY sld.ordinal
        """, (level_id,))
        return [Candidate(**dict(r)) for r in rows]
