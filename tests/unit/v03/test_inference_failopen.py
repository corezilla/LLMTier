"""M003 VRC-INF-005 / M006 VRC-DIAG-003: observation fail-open.

Real `DiagnosticsService` over a real store; diagnostic tables are dropped so
every write fails, and the inference result (and usage ledger) must be
unaffected. No network/LAN: FakeAdapter is an in-process provider double.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from http_api.errors import ApiError

from .fakes import AppFixture, FakeAdapter


class InferenceFailOpenTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.fx.seed("Worker")
        self.service = self.fx.app.responses
        self.service._adapter = lambda _: FakeAdapter()
        self.body = {"model": "Worker", "input": "hi", "stream": True, "store": False}

    def tearDown(self):
        self.fx.close()

    def _break_diagnostics(self):
        conn = self.fx.app.store.connection()
        for table in ("trace_events", "diagnostic_snapshots", "data_plane_stats", "data_plane_latency_samples"):
            conn.execute(f"DROP TABLE {table}")

    def test_inference_result_unchanged_when_diagnostic_writes_fail(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=True)
        self._break_diagnostics()
        result = self.service.create("p", "r1", self.body)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["usage"]["total_tokens"], 3)

    def test_usage_ledger_still_measured_when_diagnostic_writes_fail(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=True)
        self._break_diagnostics()
        self.service.create("p", "r2", self.body)
        row = self.fx.app.store.one("SELECT measurement_status,total_tokens FROM usage_record_versions WHERE request_id='r2' AND record_version=2")
        self.assertEqual(row["measurement_status"], "measured")
        self.assertEqual(row["total_tokens"], 3)

    def test_upstream_fault_still_surfaces_when_diagnostic_writes_fail(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=True)
        self._break_diagnostics()
        self.service._adapter = lambda _: FakeAdapter(fail=ApiError(503, "provider_unavailable", "x"))
        with self.assertRaises(ApiError) as cm:
            self.service.create("p", "r3", self.body)
        self.assertEqual((cm.exception.status, cm.exception.code), (503, "provider_unavailable"))


class InferenceNoSecondAuthTests(unittest.TestCase):
    """UT-INF-005: the inference path performs no second authentication."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed("Worker")
        self.service = self.fx.app.responses
        self.service._adapter = lambda _: FakeAdapter()
        self.body = {"model": "Worker", "input": "hi", "stream": True, "store": False}

    def tearDown(self):
        self.fx.close()

    def test_inference_path_does_not_call_authenticate(self):
        # If the inference path re-authenticated, these patched entry points
        # would raise and the call would fail. They are the only auth entry points.
        def _boom(*_a, **_k):
            raise AssertionError("inference path must not call authentication")

        with patch("http_api.auth.authenticate", _boom), \
             patch("http_api.auth.authenticate_any", _boom), \
             patch("http_api.auth.unauthenticated_principal", _boom):
            result = self.service.create("p", "r-noauth", self.body)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["usage"]["total_tokens"], 3)

    def test_inference_modules_do_not_import_auth(self):
        # Structural counterpart: importing the inference path must not pull in
        # the auth module, so no second auth call point can exist transitively.
        import importlib
        import sys
        saved = {name: mod for name, mod in sys.modules.items()
                 if name == "http_api.auth" or name.startswith("inference")}
        for name in saved:
            sys.modules.pop(name, None)
        try:
            importlib.import_module("inference.responses")
            self.assertNotIn("http_api.auth", sys.modules)
        finally:
            sys.modules.update(saved)


if __name__ == "__main__":
    unittest.main()
