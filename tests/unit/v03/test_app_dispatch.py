"""M001 http-api unit gaps (UT-API-005/006/009/010/011/012/013).

Real loopback `ThreadingHTTPServer` (ENV-2) over a real `Application` (ENV-1).
No network/LAN dependence: server binds 127.0.0.1:0.

Covers the ISD-review gaps for VRC-API-001/003/004:
  404 unknown route; 413 oversized body; invalid/top-level-non-object JSON;
  non-integer Content-Length; `_int_param`/`_optional_boolean` rejection;
  `_static` traversal + `/ui/` index; `/readyz` not_ready mapping;
  `/tier/admin/v1/*` alias parity; `_UnavailableDiagnostics` fail-open;
  `bootstrap_error` reachability (/healthz + /ui reachable, /readyz 503, data plane 503);
  data-credential-on-admin dispatch 403.
"""
from __future__ import annotations

import http.client
import json
import tempfile
import threading
import urllib.error
import urllib.request
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from http_api.app import Application, handler_factory
from http_api.errors import ApiError

from .fakes import AppFixture, FakeAdapter, response_capabilities


class LoopbackApp(unittest.TestCase):
    """Base: a seeded real app on a real loopback HTTP server, plus a raw client."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture()
        cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def request(self, method, path, body=None, headers=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        merged = {"Content-Type": "application/json"}
        merged.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=merged)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read()), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read()), dict(exc.headers)

    def raw_status(self, method, path, body=b"", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        payload = response.read()
        conn.close()
        return response.status, payload


class DispatchErrorTests(LoopbackApp):
    """UT-API-005: unknown route / unhandled error mapping."""

    def test_unknown_route_is_404_not_found(self):
        status, payload, headers = self.request("GET", "/v1/nope")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])
        self.assertTrue(headers.get("X-Request-ID"))

    def test_unhandled_error_is_500_and_logged(self):
        with patch.object(self.fx.app.models, "list", side_effect=RuntimeError("boom")):
            status, payload, _ = self.request("GET", "/v1/models")
        self.assertEqual(500, status)
        self.assertEqual("internal_error", payload["error"]["code"])
        events = [row for row in self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")["data"] if row["event"] == "unhandled_error"]
        self.assertTrue(events)

    def test_read_path_store_failure_is_503_usage_store_unavailable(self):
        with patch.object(self.fx.app.usage, "page", side_effect=RuntimeError("db down")):
            status, payload, _ = self.request("GET", "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z")
        self.assertEqual(503, status)
        self.assertEqual("usage_store_unavailable", payload["error"]["code"])


class BodyTests(LoopbackApp):
    """UT-API-009: `_body` boundary / negative mapping."""

    def test_body_over_2mb_is_413(self):
        # Declare an oversized Content-Length without sending the body; the
        # handler rejects on the header before reading the stream.
        status, payload = self.raw_status("POST", "/v1/embeddings", body=b"", headers={"Content-Length": str(2 * 1024 * 1024 + 1)})
        self.assertEqual(413, status)
        self.assertEqual("request_too_large", json.loads(payload)["error"]["code"])

    def test_invalid_json_is_400(self):
        status, payload, _ = self.request("POST", "/v1/embeddings", raw=b"{not json")
        self.assertEqual(400, status)
        self.assertEqual("invalid_json", payload["error"]["code"])

    def test_top_level_non_object_is_400(self):
        status, payload, _ = self.request("POST", "/v1/embeddings", raw=b"[1,2,3]")
        self.assertEqual(400, status)
        self.assertEqual("invalid_json", payload["error"]["code"])

    def test_non_integer_content_length_is_400(self):
        status, payload = self.raw_status("POST", "/v1/embeddings", body=b"{}", headers={"Content-Length": "abc"})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", json.loads(payload)["error"]["code"])


class QueryParamTests(LoopbackApp):
    """UT-API-006: `_int_param` / `_optional_boolean` rejection and acceptance."""

    def test_non_integer_limit_is_400(self):
        status, payload, _ = self.request("GET", "/v1/audit?limit=abc")
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_integer_limit_accepted(self):
        status, _, _ = self.request("GET", "/v1/audit?limit=1")
        self.assertEqual(200, status)

    def test_non_boolean_switch_is_400(self):
        status, payload, _ = self.request("PATCH", "/v1/diagnostics", {"snapshots_enabled": "yes"})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_boolean_switch_accepted(self):
        status, _, _ = self.request("PATCH", "/v1/diagnostics", {"snapshots_enabled": True})
        self.assertEqual(200, status)


class StaticAndReadinessTests(LoopbackApp):
    """UT-API-004/010: static traversal, `/ui/` index, readyz mapping."""

    def test_directory_traversal_is_404(self):
        status, payload, _ = self.request("GET", "/ui/../app.py")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])

    def test_ui_root_serves_index(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/ui/", method="GET")
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            self.assertEqual(200, resp.status)
            self.assertTrue(resp.headers.get("Content-Type", "").startswith("text/html"))
        self.assertIn("<!doctype html>", body.lower())

    def test_readyz_seeded_is_degraded_503(self):
        status, payload, _ = self.request("GET", "/readyz")
        self.assertEqual(503, status)
        self.assertEqual("degraded", payload["status"])


class ReadinessStatusTests(unittest.TestCase):
    """UT-API-004: primary vs degraded vs not_ready HTTP status mapping."""

    def test_empty_is_not_ready_503(self):
        from http_api.health import readiness_view
        fx = AppFixture()
        try:
            payload, status = readiness_view(fx.app.registry)
            self.assertEqual((payload["status"], status), ("not_ready", 503))
        finally:
            fx.close()

    def test_one_healthy_others_unavailable_is_degraded_503(self):
        from http_api.health import readiness_view
        fx = AppFixture(); fx.seed("Worker")
        try:
            payload, status = readiness_view(fx.app.registry)
            self.assertEqual((payload["status"], status), ("degraded", 503))
        finally:
            fx.close()


class BootstrapErrorTests(unittest.TestCase):
    """UT-API-012: `bootstrap_error` reachability + fail-open surface."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture()
        cls.fx.app.bootstrap_error = ApiError(503, "bootstrap_required", "no settings")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def get(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_healthz_still_reachable(self):
        self.assertEqual(200, self.get("/healthz"))

    def test_ui_still_reachable(self):
        self.assertEqual(200, self.get("/ui/"))

    def test_readyz_is_503_not_ready(self):
        self.assertEqual(503, self.get("/readyz"))

    def test_data_plane_returns_bootstrap_error(self):
        self.assertEqual(503, self.get("/v1/models"))


class UnavailableDiagnosticsTests(unittest.TestCase):
    """UT-API-012: DiagnosticsService init failure degrades to a no-op observer."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        settings = root / "settings.json"
        settings.write_text(json.dumps({"providers": [], "deployments": [], "service_levels": []}))
        patcher = patch("http_api.app.DiagnosticsService", side_effect=RuntimeError("diag init boom"))
        self.addCleanup(patcher.stop)
        patcher.start()
        self.app = Application(str(root / "a.db"), str(settings))

    def tearDown(self):
        self.app.store.close(); self.temp.cleanup()

    def test_degrades_to_unavailable_observer(self):
        from http_api.app import _UnavailableDiagnostics
        self.assertIsInstance(self.app.diagnostics, _UnavailableDiagnostics)

    def test_switches_default_off(self):
        self.assertEqual(self.app.diagnostics.switches(), {"snapshots_enabled": False, "stats_enabled": False})

    def test_void_methods_are_noops(self):
        self.assertIsNone(self.app.diagnostics.record_trace("r", "received"))
        self.assertIsNone(self.app.diagnostics.record_latency(None, "Worker", 200, 1.0))
        self.assertIsNone(self.app.diagnostics.capture_snapshot("r", None, "Worker", "u", "m", 200, 1.0, None))
        self.assertEqual(self.app.diagnostics.stats("a", "b"), {"windows": []})
        self.assertEqual(self.app.diagnostics.cleanup(), 0)

    def test_inference_still_succeeds_when_diagnostics_unavailable(self):
        self.app.registry.create_provider({"name": "p", "kind": "local", "endpoint": "http://127.0.0.1:9", "secret_ref": None, "enabled": True})
        provider = self.app.registry.list_providers()[0]
        deployment, _ = self.app.registry.create_deployment({"name": "d", "provider_id": provider["id"], "backend_model": "m", "capabilities": response_capabilities(), "enabled": True})
        _, etag = self.app.registry.get_service_level("Worker")
        self.app.registry.update_service_level("Worker", {"deployment_ids": [deployment["id"]]}, etag)
        self.app.store.connection().execute("UPDATE deployments SET health='healthy' WHERE id=?", (deployment["id"],))
        self.app.responses._adapter = lambda _: FakeAdapter()
        result = self.app.responses.create("p", "r", {"model": "Worker", "input": "hi", "stream": True, "store": False})
        self.assertEqual(result["status"], "completed")


class AliasParityTests(LoopbackApp):
    """UT-API-011: `/tier/admin/v1/*` alias routes behave like `/v1/*`."""

    def test_diagnostics_switches_parity(self):
        base = self.request("GET", "/v1/diagnostics")
        alias = self.request("GET", "/tier/admin/v1/diagnostics")
        self.assertEqual(base[0], alias[0])
        self.assertEqual(base[1], alias[1])

    def test_snapshots_parity(self):
        base = self.request("GET", "/v1/diagnostics/snapshots?limit=abc")
        alias = self.request("GET", "/tier/admin/v1/diagnostics/snapshots?limit=abc")
        self.assertEqual((base[0], base[1]["error"]["code"]), (alias[0], alias[1]["error"]["code"]))
        self.assertEqual(400, base[0])

    def test_traces_parity_empty(self):
        base = self.request("GET", "/v1/diagnostics/traces?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        alias = self.request("GET", "/tier/admin/v1/diagnostics/traces?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        self.assertEqual(base[1]["items"], alias[1]["items"])


class AdminDispatchAuthTests(unittest.TestCase):
    """UT-API-008: data credential on an admin endpoint → 403 at the dispatch layer."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture(); cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.env = patch.dict("os.environ", {"LLMTIER_DATA_TOKEN": "dt", "LLMTIER_ADMIN_TOKEN": "at"}, clear=False)
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def request(self, path, token):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method="GET", headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_data_token_on_admin_endpoint_is_403(self):
        status, payload = self.request("/v1/providers", "dt")
        self.assertEqual(403, status)
        self.assertEqual("permission_denied", payload["error"]["code"])

    def test_admin_token_on_admin_endpoint_is_200(self):
        status, _ = self.request("/v1/providers", "at")
        self.assertEqual(200, status)


class DiagnosticsPatchContractTests(LoopbackApp):
    """UT-API-013: `/v1/diagnostics` PATCH unknown key / non-boolean."""

    def test_unknown_key_is_400(self):
        status, payload, _ = self.request("PATCH", "/v1/diagnostics", {"enabled": True})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_alias_unknown_key_is_400(self):
        status, payload, _ = self.request("PATCH", "/tier/admin/v1/diagnostics", {"enabled": True})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
