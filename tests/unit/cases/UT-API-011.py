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






if __name__ == "__main__":
    unittest.main()
