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

    def request_method(self, method, path, token):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method, headers={"Authorization": f"Bearer {token}"})
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

    def test_auth_either_admin_first_role_selection(self):
        # `/v1/usage` DELETE requires admin. With BOTH tokens configured, the
        # admin token must resolve to the admin role (allowed) and the data
        # token must not (403). This is the admin-first branch of `_auth_either`.
        status, _ = self.request_method("DELETE", "/v1/usage", "at")
        self.assertEqual(200, status)
        status, payload = self.request_method("DELETE", "/v1/usage", "dt")
        self.assertEqual(403, status)
        self.assertEqual("permission_denied", payload["error"]["code"])




if __name__ == "__main__":
    unittest.main()
