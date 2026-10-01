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










class DiagnosticCursorContractTests(unittest.TestCase):
    """Cursor validation: invalid cursors must be rejected, not silently ignored."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics

    def tearDown(self): self.fx.close()

    def test_snapshots_invalid_cursor_rejected(self):
        with self.assertRaises(ApiError) as cm:
            self.d.snapshots_page(None, None, None, None, 50, "snap_does_not_exist")
        self.assertEqual(cm.exception.status, 400)
        self.assertEqual(cm.exception.code, "cursor_expired")






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

    def test_snapshots_invalid_cursor_is_400_expired(self):
        status, payload = self.request("GET", "/v1/diagnostics/snapshots?cursor=snap_bogus")
        self.assertEqual(400, status)
        self.assertEqual("cursor_expired", payload["error"]["code"])









