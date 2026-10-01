"""M005 observability unit gaps (UT-OBS-006/007).

M005 has no independent implementation file; its behavior lands on M001's
diagnostic routes and M006's query surface (scheme §1). These tests exercise
that surface through real `Application`/loopback HTTP (ENV-1 + ENV-2).
No network/LAN: server binds 127.0.0.1:0.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
import unittest
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory

from tests.common.fakes import AppFixture, FakeAdapter


class CorrelationObservabilityTests(unittest.TestCase):
    """UT-OBS-004/007: X-Correlation-ID echo and traceparent trace-id extraction."""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture(); cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def post(self, headers):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/responses", data=b"{}", method="POST",
            headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers)

    def test_explicit_correlation_id_is_echoed(self):
        status, headers = self.post({"X-Correlation-ID": "mine"})
        self.assertEqual(400, status)  # body {} fails validation; correlation still echoed
        self.assertEqual(headers.get("X-Correlation-ID"), "mine")

    def test_traceparent_trace_id_is_extracted(self):
        trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        status, headers = self.post({"traceparent": f"00-{trace_id}-00f067aa0ba902b7-01"})
        self.assertEqual(headers.get("X-Correlation-ID"), trace_id)

    def test_no_correlation_header_is_absent(self):
        _, headers = self.post({})
        self.assertIsNone(headers.get("X-Correlation-ID"))






if __name__ == "__main__":
    unittest.main()
