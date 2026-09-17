from __future__ import annotations

import json
import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ApiError, require
from .store import Store


FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")
CAPABILITY_KEYS = {"responses", "embeddings", "tools", "structured_outputs", "input_modalities", "output_modalities", "context_window", "max_output_tokens", "embedding_space_id", "embedding_dimensions", "embedding_max_batch_inputs", "embedding_max_input_tokens"}


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
                for item in deployments:
                    require(set(item) == {"id", "name", "provider_id", "backend_model", "capabilities", "enabled"}, 503, "bootstrap_invalid", "Invalid deployment entry")
                    conn.execute("INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)", (item["id"], item["name"], item["provider_id"], item["backend_model"], json.dumps(item["capabilities"], separators=(",", ":")), int(item["enabled"]), "unknown", 1))
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

    def create_provider(self, body: dict[str, Any]) -> tuple[dict[str, Any], str]:
        allowed = {"name", "kind", "endpoint", "secret_ref", "enabled"}
        require(set(body) == allowed, 400, "invalid_request", "Provider fields are incomplete or unknown")
        require(body["kind"] in {"cloud", "local"}, 400, "invalid_request", "Invalid provider kind", "kind")
        rid = _id("provider")
        try:
            with self.store.transaction(True) as conn:
                conn.execute("INSERT INTO providers VALUES(?,?,?,?,?,?,?)", (rid, body["name"], body["kind"], body["endpoint"], body["secret_ref"], int(body["enabled"]), 1))
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise ApiError(409, "resource_conflict", "Provider name already exists") from exc
            raise
        return self.get_provider(rid)

    def get_provider(self, rid: str) -> tuple[dict[str, Any], str]:
        row = self.store.one("SELECT * FROM providers WHERE id=?", (rid,))
        if row is None:
            raise ApiError(404, "not_found", "Provider not found")
        view = {"id": row["id"], "name": row["name"], "kind": row["kind"], "endpoint": row["endpoint"], "has_secret": row["secret_ref"] is not None, "enabled": _bool(row["enabled"]), "version": row["version"]}
        return view, _etag(row["id"], row["version"])

    def list_providers(self) -> list[dict[str, Any]]:
        return [self.get_provider(row["id"])[0] for row in self.store.all("SELECT id FROM providers ORDER BY name,id")]

    def update_provider(self, rid: str, body: dict[str, Any], if_match: str | None) -> tuple[dict[str, Any], str]:
        allowed = {"name", "kind", "endpoint", "secret_ref", "enabled"}
        require(body and set(body) <= allowed, 400, "invalid_request", "Unknown or empty provider patch")
        with self.store.transaction(True) as conn:
            row = conn.execute("SELECT * FROM providers WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Provider not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Provider version changed")
            values = {k: row[k] for k in ("name", "kind", "endpoint", "secret_ref", "enabled")}
            values.update(body)
            version = row["version"] + 1
            conn.execute("UPDATE providers SET name=?,kind=?,endpoint=?,secret_ref=?,enabled=?,version=? WHERE id=?", (values["name"], values["kind"], values["endpoint"], values["secret_ref"], int(values["enabled"]), version, rid))
        return self.get_provider(rid)

    def delete_provider(self, rid: str, if_match: str | None) -> None:
        with self.store.transaction(True) as conn:
            row = conn.execute("SELECT version FROM providers WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Provider not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Provider version changed")
            if conn.execute("SELECT 1 FROM deployments WHERE provider_id=? LIMIT 1", (rid,)).fetchone():
                raise ApiError(409, "resource_in_use", "Provider is referenced by a deployment")
            conn.execute("DELETE FROM providers WHERE id=?", (rid,))

    def create_deployment(self, body: dict[str, Any]) -> tuple[dict[str, Any], str]:
        required = {"name", "provider_id", "backend_model", "capabilities", "enabled"}
        require(set(body) == required, 400, "invalid_request", "Deployment fields are incomplete or unknown")
        self._validate_capabilities(body["capabilities"])
        require(self.store.one("SELECT 1 FROM providers WHERE id=?", (body["provider_id"],)) is not None, 400, "invalid_request", "Unknown provider", "provider_id")
        rid = _id("deployment")
        try:
            with self.store.transaction(True) as conn:
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

    def update_deployment(self, rid: str, body: dict[str, Any], if_match: str | None) -> tuple[dict[str, Any], str]:
        allowed = {"name", "provider_id", "backend_model", "capabilities", "enabled"}
        require(body and set(body) <= allowed, 400, "invalid_request", "Unknown or empty deployment patch")
        if "capabilities" in body: self._validate_capabilities(body["capabilities"])
        with self.store.transaction(True) as conn:
            row = conn.execute("SELECT * FROM deployments WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Deployment not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Deployment version changed")
            values = {"name": row["name"], "provider_id": row["provider_id"], "backend_model": row["backend_model"], "capabilities": json.loads(row["capabilities_json"]), "enabled": _bool(row["enabled"])}
            values.update(body)
            require(conn.execute("SELECT 1 FROM providers WHERE id=?", (values["provider_id"],)).fetchone() is not None, 400, "invalid_request", "Unknown provider", "provider_id")
            version = row["version"] + 1
            conn.execute("UPDATE deployments SET name=?,provider_id=?,backend_model=?,capabilities_json=?,enabled=?,version=? WHERE id=?", (values["name"], values["provider_id"], values["backend_model"], json.dumps(values["capabilities"], separators=(",", ":")), int(values["enabled"]), version, rid))
        return self.get_deployment(rid)

    def delete_deployment(self, rid: str, if_match: str | None) -> None:
        with self.store.transaction(True) as conn:
            row = conn.execute("SELECT version FROM deployments WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Deployment not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Deployment version changed")
            if conn.execute("SELECT 1 FROM service_level_deployments WHERE deployment_id=? LIMIT 1", (rid,)).fetchone():
                raise ApiError(409, "resource_in_use", "Deployment is referenced by a service level")
            conn.execute("DELETE FROM deployments WHERE id=?", (rid,))

    def _capability_intersection(self, deployment_ids: list[str]) -> dict[str, Any]:
        rows = [self.get_deployment(rid)[0] for rid in deployment_ids]
        require(len(rows) == len(deployment_ids), 400, "invalid_request", "Unknown deployment")
        keys = set.intersection(*(set(r["capabilities"]) for r in rows)) if rows else set()
        result: dict[str, Any] = {}
        for key in keys:
            values = [r["capabilities"][key] for r in rows]
            if all(isinstance(v, bool) for v in values): result[key] = all(values)
            elif all(v == values[0] for v in values): result[key] = values[0]
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
            models = [self.get_deployment(rid)[0]["backend_model"] for rid in deployment_ids]
            require(all(model == "BAAI/bge-m3" for model in models), 409, "embedding_space_conflict", "Embedding-v1 requires BAAI/bge-m3")
        else:
            require(capabilities.get("responses") is True, 409, "capability_conflict", "Inference Tier requires Responses support")

    def create_service_level(self, body: dict[str, Any]) -> tuple[dict[str, Any], str]:
        require(set(body) == {"id", "deployment_ids", "enabled"}, 400, "invalid_request", "Service level fields are incomplete or unknown")
        require(body["id"] in FIXED_TIERS, 400, "invalid_request", "Service level ID is not a fixed Tier", "id")
        capabilities = self._capability_intersection(body["deployment_ids"])
        self._validate_level(body["id"], body["deployment_ids"], capabilities)
        try:
            with self.store.transaction(True) as conn:
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

    def update_service_level(self, rid: str, body: dict[str, Any], if_match: str | None) -> tuple[dict[str, Any], str]:
        require(body and set(body) <= {"deployment_ids", "enabled"}, 400, "invalid_request", "Unknown or empty service level patch")
        with self.store.transaction(True) as conn:
            row = conn.execute("SELECT * FROM service_levels WHERE id=?", (rid,)).fetchone()
            if row is None: raise ApiError(404, "not_found", "Service level not found")
            if if_match != _etag(rid, row["version"]): raise ApiError(412, "version_conflict", "Service level version changed")
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

    def delete_service_level(self, rid: str, if_match: str | None) -> None:
        raise ApiError(409, "fixed_service_level", "Fixed Tier service levels cannot be deleted")

    def candidates(self, level_id: str) -> list[Candidate]:
        rows = self.store.all("""
          SELECT sld.level_id,d.id deployment_id,p.id provider_id,p.endpoint,d.backend_model,p.kind,d.health,sld.ordinal
          FROM service_level_deployments sld JOIN service_levels sl ON sl.id=sld.level_id
          JOIN deployments d ON d.id=sld.deployment_id JOIN providers p ON p.id=d.provider_id
          WHERE sld.level_id=? AND sl.enabled=1 AND d.enabled=1 AND p.enabled=1 ORDER BY sld.ordinal
        """, (level_id,))
        return [Candidate(**dict(r)) for r in rows]
