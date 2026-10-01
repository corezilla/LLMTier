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




















if __name__ == "__main__":
    unittest.main()
