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



    def test_traces_out_of_window_is_empty(self):
        self.d.record_trace("r1", "received", None)
        # Window entirely in the future relative to the recorded trace.
        self.assertEqual(self.d.traces(since="2100-01-01T00:00:00Z", until="2200-01-01T00:00:00Z")["items"], [])
        # Window entirely in the past.
        self.assertEqual(self.d.traces(since="1900-01-01T00:00:00Z", until="2000-01-01T00:00:00Z")["items"], [])
        # Same trace IS returned by a window that contains it (discriminating).
        self.assertEqual(len(self.d.traces(**self.window)["items"]), 1)



class DiagnosticCursorContractTests(unittest.TestCase):
    """Cursor validation: invalid cursors must be rejected, not silently ignored."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics

    def tearDown(self): self.fx.close()


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






