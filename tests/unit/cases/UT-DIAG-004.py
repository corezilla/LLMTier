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






class InjectionEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.store = self.fx.app.store
        self.service = self.fx.app.responses
        self.service._adapter = lambda _: FakeAdapter()
        self.d = self.fx.app.diagnostics
        self.did = self.fx.app.registry.list_deployments()[0]["id"]
        self.body = {"model": "Worker", "input": "hello", "stream": True, "store": False}

    def tearDown(self): self.fx.close()

    def test_fault_502_returns_injected_error_and_marks_usage(self):
        self.d.set_injections(self.did, [{"type": "fault_502", "config": {"error_body": "injected backend error"}, "enabled": True}])
        with self.assertRaises(ApiError) as cm:
            self.service.create("p", "r-inj", self.body)
        self.assertEqual(cm.exception.status, 502)
        self.assertEqual(cm.exception.code, "provider_failure")
        self.assertIn("injected backend error", cm.exception.message)
        page = self.fx.app.usage.page("p", None, since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertEqual(page["data"][0]["source"], "injected")

    def test_rate_limit_injection_returns_429_with_retry_after(self):
        self.d.set_injections(self.did, [{"type": "rate_limit", "config": {"retry_after_sec": 7}, "enabled": True}])
        with self.assertRaises(ApiError) as cm:
            self.service.create("p", "r-rl", self.body)
        self.assertEqual(cm.exception.status, 429)
        self.assertEqual(cm.exception.headers.get("Retry-After"), "7")

    def test_delay_injection_still_completes(self):
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 10}, "enabled": True}])
        result = self.service.create("p", "r-delay", self.body)
        self.assertEqual(result["status"], "completed")








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






    def test_injection_patch_requires_items(self):
        status, payload = self.request("PATCH", f"/v1/deployments/{self.did}/diagnostics", {})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_injection_patch_explicit_empty_items_revokes(self):
        status, _ = self.request("PATCH", f"/v1/deployments/{self.did}/diagnostics", {"items": []})
        self.assertEqual(200, status)

    def test_injection_patch_rejects_non_boolean_enabled(self):
        status, payload = self.request("PATCH", f"/v1/deployments/{self.did}/diagnostics",
                                       {"items": [{"type": "delay", "config": {"delay_ms": 1}, "enabled": "false"}]})
        self.assertEqual(400, status)
        self.assertEqual("invalid_injection", payload["error"]["code"])


