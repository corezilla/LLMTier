import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory
from http_api.errors import ApiError
from .fakes import AppFixture, FakeAdapter


def _stats_response(payload: dict) -> dict:
    return {"error": {"message": payload, "type": "server_error", "code": "provider_unavailable", "param": None, "retryable": True}}


class DiagnosticsSwitchTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.d = self.fx.app.diagnostics

    def tearDown(self): self.fx.close()

    def test_switches_default_off_and_runtime_toggle(self):
        self.assertEqual(self.d.switches(), {"snapshots_enabled": False, "stats_enabled": False})
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)
        self.assertEqual(self.d.switches(), {"snapshots_enabled": True, "stats_enabled": True})
        self.d.set_switches(snapshots_enabled=False)
        self.assertEqual(self.d.switches()["snapshots_enabled"], False)
        self.assertEqual(self.d.switches()["stats_enabled"], True)


class InjectionConfigTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics; self.did = self.fx.app.registry.list_deployments()[0]["id"]

    def tearDown(self): self.fx.close()

    def test_unknown_type_rejected(self):
        with self.assertRaises(ApiError) as cm:
            self.d.set_injections(self.did, [{"type": "nope", "config": {}, "enabled": True}])
        self.assertEqual(cm.exception.code, "invalid_injection")

    def test_missing_or_out_of_range_config_rejected(self):
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "delay", "config": {}, "enabled": True}])
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 60001}, "enabled": True}])
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "rate_limit", "config": {"retry_after_sec": -1}, "enabled": True}])
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "stream_terminate", "config": {"stream_terminate_after_events": 0}, "enabled": True}])

    def test_error_body_truncated_to_512_bytes(self):
        self.d.set_injections(self.did, [{"type": "fault_502", "config": {"error_body": "x" * 600}, "enabled": True}])
        items = self.d.injections(self.did)
        self.assertEqual(len(items[0]["config"]["error_body"].encode()), 512)

    def test_upsert_partial_update_keeps_other_types(self):
        self.d.set_injections(self.did, [
            {"type": "fault_502", "config": {"error_body": "a"}, "enabled": True},
            {"type": "delay", "config": {"delay_ms": 100}, "enabled": True},
        ])
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 200}, "enabled": False}])
        items = {x["type"]: x for x in self.d.injections(self.did)}
        self.assertTrue(items["fault_502"]["enabled"])
        self.assertFalse(items["delay"]["enabled"])
        self.assertEqual(items["delay"]["config"]["delay_ms"], 200)

    def test_unknown_deployment_rejected(self):
        with self.assertRaises(ApiError): self.d.set_injections("dep_missing", [{"type": "delay", "config": {"delay_ms": 1}, "enabled": True}])


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


class TracesQueryTests(unittest.TestCase):
    """M006 FUNC-DIAG-TRACES / cleanup (VRC-DIAG-004)."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.window = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}

    def tearDown(self): self.fx.close()

    def test_traces_dedups_by_request_and_stable_paging(self):
        self.d.record_trace("r1", "received", None)
        self.d.record_trace("r1", "completed", None)
        self.d.record_trace("r2", "received", None)
        page = self.d.traces(**self.window)
        self.assertEqual(sorted(item["request_id"] for item in page["items"]), ["r1", "r2"])
        self.assertFalse(page["has_more"])
        first = self.d.traces(limit=1, **self.window)
        self.assertTrue(first["has_more"]); self.assertIsNotNone(first["next_cursor"])
        second = self.d.traces(limit=1, cursor=first["next_cursor"], **self.window)
        self.assertEqual(len(second["items"]), 1)
        self.assertNotEqual(first["items"][0]["request_id"], second["items"][0]["request_id"])

    def test_cleanup_removes_expired_and_returns_count(self):
        self.d.record_trace("old", "received", None)
        self.fx.app.store.connection().execute("UPDATE trace_events SET created_at='2000-01-01T00:00:00.000Z'")
        deleted = self.d.cleanup(7)
        self.assertGreaterEqual(deleted, 1)
        self.assertEqual(self.d.traces(**self.window)["items"], [])

    def test_traces_out_of_window_is_empty(self):
        self.d.record_trace("r1", "received", None)
        # Window entirely in the future relative to the recorded trace.
        self.assertEqual(self.d.traces(since="2100-01-01T00:00:00Z", until="2200-01-01T00:00:00Z")["items"], [])
        # Window entirely in the past.
        self.assertEqual(self.d.traces(since="1900-01-01T00:00:00Z", until="2000-01-01T00:00:00Z")["items"], [])
        # Same trace IS returned by a window that contains it (discriminating).
        self.assertEqual(len(self.d.traces(**self.window)["items"]), 1)

    def test_set_switches_rejects_non_boolean(self):
        with self.assertRaises(ApiError) as cm:
            self.d.set_switches(snapshots_enabled="yes")
        self.assertEqual(cm.exception.code, "invalid_request")


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

    def test_traces_cursor_without_separator_rejected(self):
        with self.assertRaises(ApiError) as cm:
            self.d.traces(cursor="not-a-cursor")
        self.assertEqual(cm.exception.status, 400)
        self.assertEqual(cm.exception.code, "cursor_expired")

    def test_traces_valid_cursor_still_pages(self):
        self.d.record_trace("r1", "received", None)
        self.d.record_trace("r2", "received", None)
        first = self.d.traces(limit=1, since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        second = self.d.traces(limit=1, cursor=first["next_cursor"], since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertEqual(len(second["items"]), 1)


class InjectionEnabledContractTests(unittest.TestCase):
    """InjectionWrite.enabled must be a real boolean (openapi: type boolean)."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics; self.did = self.fx.app.registry.list_deployments()[0]["id"]

    def tearDown(self): self.fx.close()

    def test_non_boolean_enabled_rejected(self):
        for value in ("false", 1, 0, None, "true"):
            with self.assertRaises(ApiError) as cm:
                self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": value}])
            self.assertEqual(cm.exception.code, "invalid_injection")

    def test_missing_enabled_rejected(self):
        with self.assertRaises(ApiError) as cm:
            self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}}])
        self.assertEqual(cm.exception.code, "invalid_injection")

    def test_boolean_enabled_still_accepted(self):
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": False}])
        self.assertFalse(self.d.injections(self.did)[0]["enabled"])
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": True}])
        self.assertTrue(self.d.injections(self.did)[0]["enabled"])


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

    def test_traces_invalid_cursor_is_400_expired(self):
        status, payload = self.request("GET", "/v1/diagnostics/traces?cursor=bogus")
        self.assertEqual(400, status)
        self.assertEqual("cursor_expired", payload["error"]["code"])

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


