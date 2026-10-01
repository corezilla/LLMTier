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




class InjectionConfigTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics; self.did = self.fx.app.registry.list_deployments()[0]["id"]

    def tearDown(self): self.fx.close()



    def test_error_body_truncated_to_512_bytes(self):
        self.d.set_injections(self.did, [{"type": "fault_502", "config": {"error_body": "x" * 600}, "enabled": True}])
        items = self.d.injections(self.did)
        self.assertEqual(len(items[0]["config"]["error_body"].encode()), 512)






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










