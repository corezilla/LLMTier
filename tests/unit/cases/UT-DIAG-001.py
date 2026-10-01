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








class TracesQueryTests(unittest.TestCase):
    """M006 FUNC-DIAG-TRACES / cleanup (VRC-DIAG-004)."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.window = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}

    def tearDown(self): self.fx.close()




    def test_set_switches_rejects_non_boolean(self):
        with self.assertRaises(ApiError) as cm:
            self.d.set_switches(snapshots_enabled="yes")
        self.assertEqual(cm.exception.code, "invalid_request")








