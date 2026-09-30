"""M005 observability unit gaps (UT-OBS-006/007).

M005 has no independent implementation file; its behavior lands on M001's
diagnostic routes and M006's query surface (scheme §1). These tests exercise
that surface through real `Application`/loopback HTTP (ENV-1 + ENV-2).
No network/LAN: server binds 127.0.0.1:0.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
import unittest
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory

from .fakes import AppFixture, FakeAdapter


class CorrelationObservabilityTests(unittest.TestCase):
    """UT-OBS-004/007: X-Correlation-ID echo and traceparent trace-id extraction."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture(); cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def post(self, headers):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/responses", data=b"{}", method="POST",
            headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers)

    def test_explicit_correlation_id_is_echoed(self):
        status, headers = self.post({"X-Correlation-ID": "mine"})
        self.assertEqual(400, status)  # body {} fails validation; correlation still echoed
        self.assertEqual(headers.get("X-Correlation-ID"), "mine")

    def test_traceparent_trace_id_is_extracted(self):
        trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        status, headers = self.post({"traceparent": f"00-{trace_id}-00f067aa0ba902b7-01"})
        self.assertEqual(headers.get("X-Correlation-ID"), trace_id)

    def test_no_correlation_header_is_absent(self):
        _, headers = self.post({})
        self.assertIsNone(headers.get("X-Correlation-ID"))


class SnapshotRedactionTests(unittest.TestCase):
    """UT-OBS-006: upstream URL query string is stripped end-to-end (query token not stored)."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed("Worker")
        self.d = self.fx.app.diagnostics
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)

    def tearDown(self): self.fx.close()

    def test_query_secret_is_not_stored_in_snapshot(self):
        provider_id = self.fx.app.store.one("SELECT provider_id FROM deployments")[0]
        self.fx.app.store.connection().execute(
            "UPDATE providers SET endpoint='http://127.0.0.1:9/v1?token=SECRETXYZ' WHERE id=?", (provider_id,))
        self.fx.app.responses._adapter = lambda _: FakeAdapter()
        self.fx.app.responses.create("p", "r1", {"model": "Worker", "input": "hi", "stream": True, "store": False})
        row = self.fx.app.store.one("SELECT upstream_url FROM diagnostic_snapshots WHERE request_id='r1'")
        self.assertEqual(row["upstream_url"], "http://127.0.0.1:9/v1")
        self.assertNotIn("SECRETXYZ", row["upstream_url"])

    def test_trace_stage_url_also_stripped(self):
        provider_id = self.fx.app.store.one("SELECT provider_id FROM deployments")[0]
        self.fx.app.store.connection().execute(
            "UPDATE providers SET endpoint='http://127.0.0.1:9/v1?api_key=TOPSECRET' WHERE id=?", (provider_id,))
        self.fx.app.responses._adapter = lambda _: FakeAdapter()
        self.fx.app.responses.create("p", "r2", {"model": "Worker", "input": "hi", "stream": True, "store": False})
        stages = self.d.trace("r2")["stages"]
        urls = [stage["detail"].get("upstream_url") for stage in stages if stage["detail"] and "upstream_url" in stage["detail"]]
        self.assertTrue(urls)
        self.assertTrue(all("TOPSECRET" not in url for url in urls))


class DiagnosticsAvailabilityTests(unittest.TestCase):
    """UT-OBS-006: a broken query store returns 503, not a faked empty page."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture(); cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def get(self, path):
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method="GET")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_snapshots_store_failure_is_503_not_empty_page(self):
        original = self.fx.app.diagnostics.snapshots_page
        self.fx.app.diagnostics.snapshots_page = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("db down"))
        try:
            status, payload = self.get("/v1/diagnostics/snapshots")
        finally:
            self.fx.app.diagnostics.snapshots_page = original
        self.assertEqual(503, status)
        self.assertEqual("usage_store_unavailable", payload["error"]["code"])
        self.assertNotIn("items", payload)

    def test_switches_read_still_200(self):
        status, _ = self.get("/v1/diagnostics")
        self.assertEqual(200, status)


if __name__ == "__main__":
    unittest.main()
