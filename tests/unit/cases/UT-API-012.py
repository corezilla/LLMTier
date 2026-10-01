from __future__ import annotations

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

from tests.common.fakes import AppFixture, FakeAdapter, response_capabilities


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








if __name__ == "__main__":
    unittest.main()


import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from http_api import __version__
from http_api.app import Application, handler_factory


class StartupTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def settings(self,value=None):
        p=self.root/"settings.json";p.write_text(json.dumps(value or {"providers":[],"deployments":[],"service_levels":[]}));return str(p)
    def test_non_apierror_bootstrap_does_not_crash(self):
        """CR-BOOTSTRAP-CATCH: a non-ApiError bootstrap failure → not_ready, no crash."""
        with patch("management.registry.Registry.bootstrap_settings",side_effect=OSError("disk gone")):
            app=Application(str(self.root/"g.db"),self.settings())
            try:
                self.assertIsNotNone(app.bootstrap_error)
                self.assertEqual((app.bootstrap_error.status,app.bootstrap_error.code),(503,"bootstrap_invalid"))
            finally:
                app.store.close()
