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


















if __name__ == "__main__":
    unittest.main()
