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














