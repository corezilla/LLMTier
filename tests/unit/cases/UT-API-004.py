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








class StaticAndReadinessTests(LoopbackApp):
    """UT-API-004/010: static traversal, `/ui/` index, readyz mapping."""

    def test_directory_traversal_is_404(self):
        # The traversal guard lives in `_static`. `urllib` normalizes
        # `/ui/../x` to `/x` before sending, so a urllib request never reaches
        # `_static` and would pass even if the guard were removed. Send the raw
        # path over a real socket instead. `/ui/../http_api/app.py` resolves to
        # an existing file OUTSIDE the web_ui root, so removing the
        # `root not in target.parents` guard would serve it (200, source leak)
        # — this test goes red exactly then.
        status, payload = self.raw_status("GET", "/ui/../http_api/app.py")
        self.assertEqual(404, status)
        self.assertEqual("not_found", json.loads(payload)["error"]["code"])
        # A second, deeper raw traversal that also resolves outside the root.
        status, _ = self.raw_status("GET", "/ui/../../etc/passwd")
        self.assertEqual(404, status)
















if __name__ == "__main__":
    unittest.main()


import unittest

from http_api.errors import ApiError
from http_api.health import apply_probe_result, health_view, readiness_view
from tests.common.fakes import AppFixture


class HealthTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture()
    def tearDown(self):self.fx.close()
    def test_empty_is_not_ready(self):self.assertEqual(readiness_view(self.fx.app.registry)[0]["status"],"not_ready")
    def test_not_ready_http_status(self):self.assertEqual(readiness_view(self.fx.app.registry)[1],503)
    def test_probe_persists(self):
        _,d=self.fx.seed(health="unknown");apply_probe_result(self.fx.app.registry,d["id"],"healthy","r");self.assertEqual(self.fx.app.registry.get_deployment(d["id"])[0]["health"],"healthy")
