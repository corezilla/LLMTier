"""M006 libdiag unit gaps (UT-DIAG-002/003/004/005/006/007/008).

Real `DiagnosticsService` over an isolated temp store (ENV-1). No network.
Write-failure fail-open is exercised by dropping the diagnostic tables so the
in-service write raises and is swallowed (the store itself stays healthy).
"""
from __future__ import annotations

import unittest

from tests.common.fakes import AppFixture

WINDOW = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}


def _boom(*_a, **_k):
    raise RuntimeError("diagnostic store down")






class FailOpenWriteTests(unittest.TestCase):
    """UT-DIAG-003/007: write-failure degradation + cleanup failure returns 0."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)

    def tearDown(self): self.fx.close()

    def test_record_trace_failure_is_swallowed(self):
        self.d._traces.store.transaction = _boom
        self.assertIsNone(self.d.record_trace("r", "received"))

    def test_record_latency_failure_is_swallowed(self):
        self.d._stats.store.transaction = _boom
        self.assertIsNone(self.d.record_latency(None, "Worker", 200, 1.0))

    def test_capture_snapshot_failure_returns_none(self):
        self.d._snapshots.store.transaction = _boom
        self.assertIsNone(self.d.capture_snapshot("r", None, "Worker", "u", "m", 200, 1.0, None))

    def test_cleanup_failure_returns_zero(self):
        self.d.store.transaction = _boom
        self.assertEqual(self.d.cleanup(), 0)

    def test_failed_write_is_warned_to_operator_log(self):
        self.d._traces.store.transaction = _boom
        self.d.record_trace("r", "received")
        events = [row for row in self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")["data"] if row["event"] == "capture_failed"]
        self.assertTrue(events)


class UnavailableDiagnosticsUnitTests(unittest.TestCase):
    """UT-DIAG-007: `_UnavailableDiagnostics` degrades every method as a no-op."""

    def setUp(self):
        from http_api.app import _UnavailableDiagnostics
        self.d = _UnavailableDiagnostics()

    def test_switches_off_and_void_methods(self):
        self.assertEqual(self.d.switches(), {"snapshots_enabled": False, "stats_enabled": False})
        self.assertIsNone(self.d.record_trace("r", "s"))
        self.assertIsNone(self.d.record_latency(None, "m", 200, 1.0))
        self.assertIsNone(self.d.capture_snapshot("r", None, "m", "u", "b", 200, 1.0, None))
        self.assertEqual(self.d.stats("a", "b"), {"windows": []})
        self.assertEqual(self.d.cleanup(), 0)

    def test_read_surfaces_are_empty(self):
        self.assertEqual(self.d.trace("r")["stages"], [])
        self.assertEqual(self.d.traces()["items"], [])
        self.assertEqual(self.d.snapshots_page(None, None, None, None)["items"], [])
        self.assertEqual(self.d.injections(None), [])
        self.assertIsNone(self.d.enabled_injection(None))
        self.assertIsNone(self.d.enabled_stream_injection(None))

    def test_stream_wrapper_passes_through(self):
        chunks = [b"a", b"b"]
        self.assertEqual(list(self.d.stream_wrapper(None, chunks)), chunks)






if __name__ == "__main__":
    unittest.main()
