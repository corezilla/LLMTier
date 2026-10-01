from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory
from http_api.errors import ApiError
from tests.common.fakes import AppFixture, FakeAdapter


def _stats_response(payload: dict) -> dict:
    return {"error": {"message": payload, "type": "server_error", "code": "provider_unavailable", "param": None, "retryable": True}}














class DiagnosticsHttpContractTests(unittest.TestCase):
    """HTTP contract: request handlers enforce the openapi schema (unknown keys,
    required items, boolean switch values)."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture(); cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.did = cls.fx.app.registry.list_deployments()[0]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())


    def test_traces_invalid_cursor_is_400_expired(self):
        status, payload = self.request("GET", "/v1/diagnostics/traces?cursor=bogus")
        self.assertEqual(400, status)
        self.assertEqual("cursor_expired", payload["error"]["code"])










"""M006 libdiag unit gaps (UT-DIAG-002/003/004/005/006/007/008).

Real `DiagnosticsService` over an isolated temp store (ENV-1). No network.
Write-failure fail-open is exercised by dropping the diagnostic tables so the
in-service write raises and is swallowed (the store itself stays healthy).
"""

import unittest

from tests.common.fakes import AppFixture

WINDOW = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}


def _boom(*_a, **_k):
    raise RuntimeError("diagnostic store down")












class CursorContractGapTests(unittest.TestCase):
    """UT-DIAG-006: trace cursor format `first_ts|request_id`; correlation from stage detail."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        for rid in ("r1", "r2"):
            self.d.record_trace(rid, "received", None)
            self.d.record_trace(rid, "completed", None)

    def tearDown(self): self.fx.close()

    def test_trace_cursor_is_first_ts_pipe_request_id(self):
        first = self.d.traces(limit=1, **WINDOW)
        self.assertTrue(first["has_more"])
        self.assertIn("|", first["next_cursor"])
        parts = first["next_cursor"].split("|", 1)
        self.assertEqual(parts[1], first["items"][0]["request_id"])

    def test_correlation_id_taken_from_stage_detail(self):
        self.d.record_trace("r3", "received", {"x_correlation_id": "corr-1"}, correlation_id="corr-1")
        self.assertEqual(self.d.trace("r3")["correlation_id"], "corr-1")

    def test_snapshots_cursor_is_snapshot_id(self):
        self.d.set_switches(snapshots_enabled=True)
        self.d.capture_snapshot("r4", None, "Worker", "u", "m", 200, 1.0, None)
        page = self.d.snapshots_page(None, None, None, None, limit=1)
        row = self.fx.app.store.one("SELECT id FROM diagnostic_snapshots")
        self.assertEqual(page["items"][0]["id"], row["id"])


if __name__ == "__main__":
    unittest.main()
