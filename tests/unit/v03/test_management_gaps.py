"""M004 management unit gaps (UT-MGMT-001/007/008/009/010/011).

Real `Application` on an isolated temp store (ENV-1); bootstrap uses temp
settings files. Account-usage refresh uses an in-process HTTP response stub
(local `FakeResponse`, matching test_account_usage.py) — no network.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from http_api.app import Application
from http_api.errors import ApiError

from .fakes import AppFixture, response_capabilities


class FakeResponse:
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.payload


def _valid_config():
    return {
        "providers": [{"id": "prov1", "name": "P", "kind": "local", "endpoint": "http://127.0.0.1:9", "secret_ref": None, "enabled": True}],
        "deployments": [{"id": "dep1", "name": "D", "provider_id": "prov1", "backend_model": "m", "capabilities": response_capabilities(), "enabled": True}],
        "service_levels": [{"id": "Worker", "deployment_ids": ["dep1"], "enabled": True}],
    }


class BootstrapTests(unittest.TestCase):
    """UT-MGMT-001/007: bootstrap valid/no-op/section/secret-ref/rollback."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _settings(self, name, value):
        path = self.root / name; path.write_text(json.dumps(value)); return str(path)

    def _app(self, name, settings):
        return Application(str(self.root / name), settings)

    def test_valid_bootstrap_succeeds(self):
        app = self._app("a.db", self._settings("s.json", _valid_config()))
        try:
            self.assertIsNone(app.bootstrap_error)
            self.assertEqual(app.store.one("SELECT count(*) FROM providers")[0], 1)
        finally:
            app.store.close()

    def test_repeated_start_is_noop(self):
        app = self._app("b.db", self._settings("s.json", _valid_config())); app.store.close()
        again = self._app("b.db", str(self.root / "missing.json"))
        try:
            self.assertIsNone(again.bootstrap_error)
        finally:
            again.store.close()

    def test_missing_section_fails(self):
        app = self._app("c.db", self._settings("s2.json", {"providers": []}))
        try:
            self.assertIsNotNone(app.bootstrap_error)
            self.assertEqual(app.bootstrap_error.code, "bootstrap_invalid")
        finally:
            app.store.close()

    def test_env_secret_ref_unavailable_fails(self):
        config = _valid_config()
        config["providers"][0]["secret_ref"] = "env:LLMTIER_UT_NOPE"
        app = self._app("d.db", self._settings("s3.json", config))
        try:
            self.assertEqual(app.bootstrap_error.code, "bootstrap_invalid")
        finally:
            app.store.close()

    def test_file_secret_ref_missing_fails(self):
        config = _valid_config()
        config["providers"][0]["secret_ref"] = "file:/nonexistent/llmtier/secret"
        app = self._app("e.db", self._settings("s4.json", config))
        try:
            self.assertEqual(app.bootstrap_error.code, "bootstrap_invalid")
        finally:
            app.store.close()

    def test_failed_bootstrap_rolls_back_to_empty_store(self):
        config = _valid_config()
        config["providers"][0]["secret_ref"] = "env:LLMTIER_UT_NOPE"
        app = self._app("f.db", self._settings("s5.json", config))
        try:
            self.assertEqual(app.store.one("SELECT count(*) FROM providers")[0], 0)
        finally:
            app.store.close()


class ResourceInUseTests(unittest.TestCase):
    """UT-MGMT-008: referenced provider/deployment deletes → 409 resource_in_use."""

    def setUp(self): self.fx = AppFixture(); self.p, self.d = self.fx.seed()
    def tearDown(self): self.fx.close()

    def test_delete_provider_referenced_by_deployment_is_409(self):
        with self.assertRaises(ApiError) as cm:
            self.fx.app.registry.delete_provider(self.p["id"], self.fx.app.registry.get_provider(self.p["id"])[1])
        self.assertEqual((cm.exception.status, cm.exception.code), (409, "resource_in_use"))

    def test_delete_deployment_referenced_by_tier_is_409(self):
        with self.assertRaises(ApiError) as cm:
            self.fx.app.registry.delete_deployment(self.d["id"], self.fx.app.registry.get_deployment(self.d["id"])[1])
        self.assertEqual((cm.exception.status, cm.exception.code), (409, "resource_in_use"))


class AdminCursorExpiryTests(unittest.TestCase):
    """UT-MGMT-009: admin cursor `expires_at` → 400 cursor_expired."""

    def setUp(self): self.fx = AppFixture()
    def tearDown(self): self.fx.close()

    def test_expired_admin_cursor_is_400(self):
        first = self.fx.app.admin.page([{"id": "1"}, {"id": "2"}], "op", "x", limit=1)
        cursor = first["page"]["next_cursor"]; sid = cursor.split(":")[0]
        self.fx.app.store.connection().execute("UPDATE query_snapshots SET expires_at='2000-01-01T00:00:00.000Z' WHERE snapshot_id=?", (sid,))
        with self.assertRaises(ApiError) as cm:
            self.fx.app.admin.page([], "op", "x", cursor, limit=1)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "cursor_expired"))


class ResetUsageScopeTests(unittest.TestCase):
    """UT-MGMT-009: reset_usage scope matrix (model/deployment/both/neither)."""

    W, E = "2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z"

    def setUp(self):
        self.fx = AppFixture(); self.p, self.d = self.fx.seed()
        self.u = self.fx.app.usage

    def tearDown(self): self.fx.close()

    def _record(self, rid, model, bind):
        self.u.authorize_dispatch("p", rid, model, "/v1/responses")
        if bind: self.u.bind_backend("p", rid, self.p["id"], bind)
        self.u.finish("p", rid, {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2})

    def _count(self):
        return len(self.u.page("p", None, admin=True, since=self.W, until=self.E)["data"])

    def test_reset_by_model_only(self):
        self._record("a", "Worker", self.d["id"]); self._record("b", "Senior", None)
        self.assertEqual(self.u.reset_usage(model="Worker"), {"deleted": 1})
        self.assertEqual(self._count(), 1)

    def test_reset_by_deployment_only(self):
        self._record("a", "Worker", self.d["id"]); self._record("b", "Senior", None)
        self.assertEqual(self.u.reset_usage(deployment_id=self.d["id"]), {"deleted": 1})
        self.assertEqual(self._count(), 1)

    def test_reset_by_model_and_deployment(self):
        self._record("a", "Worker", self.d["id"]); self._record("b", "Worker", None)
        self.assertEqual(self.u.reset_usage(model="Worker", deployment_id=self.d["id"]), {"deleted": 1})
        self.assertEqual(self._count(), 1)

    def test_reset_all(self):
        self._record("a", "Worker", self.d["id"]); self._record("b", "Senior", None)
        self.assertGreaterEqual(self.u.reset_usage()["deleted"], 1)
        self.assertEqual(self._count(), 0)


class ProbeUnreachableTests(unittest.TestCase):
    """UT-MGMT-010: unreachable upstream → unhealthy persisted; cost flag present."""

    class DeadAdapter:
        def __init__(self, *a, **k): pass
        def probe(self): return False

    def setUp(self): self.fx = AppFixture(); self.p, self.d = self.fx.seed(health="unknown")
    def tearDown(self): self.fx.close()

    def test_unreachable_probe_is_unhealthy_persisted(self):
        with patch("management.admin.LocalProvider", self.DeadAdapter):
            result = self.fx.app.admin.probe("a", {"deployment_id": self.d["id"], "confirm_external_call": True}, "req")
        self.assertEqual(result["status"], "unhealthy")
        self.assertIn("may_have_incurred_cost", result)
        self.assertFalse(result["may_have_incurred_cost"])
        self.assertEqual(self.fx.app.registry.get_deployment(self.d["id"])[0]["health"], "unhealthy")


class AccountUsageGapTests(unittest.TestCase):
    """UT-MGMT-011: GET no-network / not_refreshed / credentials_missing / provider_api_error."""

    def setUp(self): self.fx = AppFixture()
    def tearDown(self): self.fx.close()

    def _minimax_provider(self):
        self.fx.app.registry.create_provider({
            "name": "MiniMax", "kind": "cloud", "endpoint": "https://api.minimaxi.com/v1",
            "secret_ref": "env:LLMTIER_UT_MINIMAX", "enabled": True, "usage": {"usage_provider": "minimax"},
        })
        return self.fx.app.registry.list_providers()[0]

    def test_latest_never_touches_network(self):
        provider = self._minimax_provider()
        with patch("management.account_usage._urlopen", side_effect=AssertionError("network call")):
            self.fx.app.account_usage.latest(provider["id"])

    def test_credentials_missing_snapshot(self):
        provider = self._minimax_provider()
        with patch.dict("os.environ", {}, clear=True):
            snapshot = self.fx.app.account_usage.latest(provider["id"])
        self.assertEqual((snapshot["status"], snapshot["source"]), ("unavailable", "credentials_missing"))

    def test_local_provider_not_refreshed(self):
        self.p, _ = self.fx.seed()
        snapshot = self.fx.app.account_usage.latest(self.p["id"])
        self.assertEqual((snapshot["source"], snapshot["status"]), ("store", "not_refreshed"))

    def test_refresh_requires_confirmation(self):
        provider = self._minimax_provider()
        with self.assertRaises(ApiError) as cm:
            self.fx.app.account_usage.refresh(provider["id"], False)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "confirmation_required"))

    def test_provider_api_error_is_unavailable_with_error_string(self):
        provider = self._minimax_provider()
        payload = {"base_resp": {"status_code": 1, "status_msg": "denied"}}
        with patch.dict("os.environ", {"LLMTIER_UT_MINIMAX": "k"}), patch("management.account_usage._urlopen", return_value=FakeResponse(payload)):
            snapshot = self.fx.app.account_usage.refresh(provider["id"], True)
        self.assertEqual((snapshot["status"], snapshot["source"]), ("unavailable", "provider_api_error"))
        self.assertEqual(snapshot["error"], "denied")
        self.assertNotIsInstance(snapshot["error"], type(None))


if __name__ == "__main__":
    unittest.main()
