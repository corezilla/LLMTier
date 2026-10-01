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

from tests.common.fakes import AppFixture, response_capabilities


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

    def test_malformed_offset_cursor_is_400_not_500(self):
        """CR-ADMIN-CURSOR: `<sid>:<non-integer>` → 400 cursor_expired, never ValueError→500."""
        first = self.fx.app.admin.page([{"id": "1"}, {"id": "2"}], "op", "x", limit=1)
        sid = first["page"]["next_cursor"].split(":")[0]
        with self.assertRaises(ApiError) as cm:
            self.fx.app.admin.page([], "op", "x", f"{sid}:abc", limit=1)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "cursor_expired"))

    def test_non_integer_offset_cursor_is_400_not_valueerror(self):
        # `validstyle:abc` must not leak an uncaught ValueError to the 500 path.
        with self.assertRaises(ApiError) as cm:
            self.fx.app.admin.page([], "op", "x", "validstyle:abc", limit=1)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "cursor_expired"))


class AdminCursorGuardTests(unittest.TestCase):
    """CR-ADMIN-CURSOR-GUARD: cursor binds principal, authorization and original filter."""

    def setUp(self): self.fx = AppFixture()
    def tearDown(self): self.fx.close()

    def test_cursor_filter_kind_mismatch_is_400(self):
        # A cursor minted for `providers` must not resume `deployments`: the
        # `filter_digest`/`snapshot_kind` binding rejects it.
        first = self.fx.app.admin.page([{"id": "1"}, {"id": "2"}], "op", "providers", limit=1)
        with self.assertRaises(ApiError) as cm:
            self.fx.app.admin.page([], "op", "deployments", first["page"]["next_cursor"], limit=1)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "cursor_expired"))

    def test_cursor_filter_digest_is_checked(self):
        # Tampering the stored filter digest (same principal + same kind row) makes
        # the cursor invalid; only the `filter_digest` recheck catches this, so the
        # `snapshot_kind` equality alone is not relied upon.
        first = self.fx.app.admin.page([{"id": "1"}, {"id": "2"}], "op", "x", limit=1)
        cursor = first["page"]["next_cursor"]; sid = cursor.split(":")[0]
        self.fx.app.store.connection().execute("UPDATE query_snapshots SET filter_digest='tampered' WHERE snapshot_id=?", (sid,))
        with self.assertRaises(ApiError) as cm:
            self.fx.app.admin.page([], "op", "x", cursor, limit=1)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "cursor_expired"))

    def test_cursor_authorization_digest_is_checked(self):
        # Tampering the stored authorization digest (same principal row) makes the
        # cursor invalid instead of silently resuming.
        first = self.fx.app.admin.page([{"id": "1"}, {"id": "2"}], "op", "x", limit=1)
        cursor = first["page"]["next_cursor"]; sid = cursor.split(":")[0]
        self.fx.app.store.connection().execute("UPDATE query_snapshots SET authorization_digest='tampered' WHERE snapshot_id=?", (sid,))
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






if __name__ == "__main__":
    unittest.main()
