"""Shared ENV-1/ENV-2 assembly helpers for the MT-* module cases.

ENV-2 = real ThreadingHTTPServer on 127.0.0.1:0 over a real assembled
Application (ENV-1). No LAN / no external provider (upstream is the
FakeAdapter boundary double wired through the designed `_test_adapter`
seam, asset `llmtier-unit-fakes`).

Two bases share the same client helpers: `LoopbackEnv` (one fixture per
test class) and `PerTestLoopbackEnv` (one fixture per test method, for
cases whose oracle is about absent rows or about storage state).
"""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import Application, handler_factory
from tests.common.fakes import AppFixture, FakeAdapter


class _LoopbackClients:
    """ENV-2 client helpers over a real loopback socket (shared by both bases)."""

    def request(self, method, path, body=None, headers=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        merged = {"Content-Type": "application/json"}
        merged.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=merged)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read()
                try:
                    return resp.status, json.loads(payload), dict(resp.headers)
                except json.JSONDecodeError:
                    return resp.status, payload, dict(resp.headers)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            try:
                return exc.code, json.loads(payload), dict(exc.headers)
            except json.JSONDecodeError:
                return exc.code, payload, dict(exc.headers)

    def raw_connection(self):
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)

    def raw_request(self, method, path, body=b"", headers=None):
        conn = self.raw_connection()
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            payload = response.read()
            return response.status, payload, dict(response.getheaders())
        finally:
            conn.close()

    def post_sse(self, body, headers=None):
        """Open a POST /v1/responses SSE exchange; returns (conn, response)."""
        conn = self.raw_connection()
        payload = json.dumps(body).encode()
        conn.request("POST", "/v1/responses", body=payload,
                     headers={"Content-Type": "application/json", **(headers or {})})
        return conn, conn.getresponse()

    def raw_post_sse(self, body, extra_headers=""):
        """POST /v1/responses over a raw socket; returns (sock, buf, request_id).

        The caller owns the socket (read frames / drain / teardown freely).
        """
        payload = json.dumps(body).encode()
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=30)
        sock.sendall(
            b"POST /v1/responses HTTP/1.1\r\nHost: 127.0.0.1\r\n"
            b"Content-Type: application/json\r\n" + extra_headers.encode() +
            b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
        )
        buf = b""
        while b"response.created" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        request_id = buf.split(b"X-Request-ID: ", 1)[1].split(b"\r\n", 1)[0].decode()
        return sock, buf, request_id

    def wait_for(self, predicate, timeout=8.0, interval=0.05):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(interval)
        return None

    @staticmethod
    def drain(sock):
        """Drain in-flight bytes (non-blocking) so close() is not throttled by unread data."""
        import socket as _socket
        sock.setblocking(False)
        try:
            while True:
                if not sock.recv(1 << 20):
                    break
        except (BlockingIOError, _socket.error):
            pass
        sock.setblocking(True)


class LoopbackEnv(_LoopbackClients, unittest.TestCase):
    """Seeded real app + real loopback HTTP server + JSON/raw/SSE clients.

    The assembled fixture (ENV-1 store + ENV-2 server) is shared by every test
    method of the class (`setUpClass`), so tests inside one class see each
    other's writes.
    """

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture()
        cls.fx.seed()
        cls._start_server()

    @classmethod
    def _start_server(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()


class PerTestLoopbackEnv(_LoopbackClients, unittest.TestCase):
    """Same ENV-1/ENV-2 assembly, but a fresh store + server per test method.

    Used by cases whose oracles are about *absence* of rows or about storage
    state (zero-write switches, unreadable store, injection revocation): with a
    per-class fixture those stimuli leak into the neighbouring test methods.
    """

    def setUp(self):
        self.fx = AppFixture()
        self.fx.seed()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(self.fx.app))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.fx.close()


class LargeFakeAdapter(FakeAdapter):
    """Boundary double producing a long SSE stream (many output items).

    The default FakeAdapter's stream fits in loopback socket buffers, so a
    client disconnect would never surface as a server-side write error. This
    variant keeps the server writing well past the disconnect.
    """

    def __init__(self, items=800):
        super().__init__(usage=True)
        self.items = items

    def complete(self, model, request):
        from inference.providers.base import ProviderResult
        output = [
            {"type": "message", "id": f"msg_{i}", "role": "assistant", "status": "completed",
             "content": [{"type": "output_text", "text": f"chunk {i} " + "x" * 80, "annotations": []}]}
            for i in range(self.items)
        ]
        return ProviderResult(output, {"input_tokens": 2, "output_tokens": self.items, "total_tokens": self.items + 2},
                              status="completed")
