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

    def test_non_boolean_switch_is_400_and_not_persisted(self):
        before = self.request("GET", "/v1/diagnostics")[1]
        status, payload, _ = self.request("PATCH", "/v1/diagnostics", {"snapshots_enabled": "yes"})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])
        after = self.request("GET", "/v1/diagnostics")[1]
        self.assertEqual(before, after)  # rejected request must not mutate the switches


if __name__ == "__main__":
    unittest.main()


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



    def test_switch_patch_rejects_unknown_key(self):
        status, payload = self.request("PATCH", "/v1/diagnostics", {"enabled": True})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_switch_patch_rejects_null_value(self):
        status, payload = self.request("PATCH", "/v1/diagnostics", {"snapshots_enabled": None})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_switch_patch_accepts_boolean_and_empty_body(self):
        for body in ({"snapshots_enabled": True}, {}):
            status, _ = self.request("PATCH", "/v1/diagnostics", body)
            self.assertEqual(200, status)





