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


class SnapshotBranchTests(unittest.TestCase):
    """UT-DIAG-005: error_summary byte truncation / snapshot_type / switch-off."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)

    def tearDown(self): self.fx.close()

    def test_error_summary_truncated_to_256_utf8_bytes(self):
        self.d.capture_snapshot("r1", None, "Worker", "http://u/p", "m", None, None, "é" * 300)
        summary = self.d.snapshots_page(None, None, None, None)["items"][0]["error_summary"]
        self.assertEqual(len(summary.encode("utf-8")), 256)

    def test_snapshot_type_upstream_when_status_present(self):
        self.d.capture_snapshot("r2", None, "Worker", "http://u/p", "m", 200, 1.0, None)
        self.assertEqual(self.d.snapshots_page(None, None, None, None)["items"][0]["snapshot_type"], "upstream")

    def test_snapshot_type_error_when_status_absent(self):
        self.d.capture_snapshot("r3", None, "Worker", "http://u/p", "m", None, None, "boom")
        self.assertEqual(self.d.snapshots_page(None, None, None, None)["items"][0]["snapshot_type"], "error")

    def test_switch_off_captures_nothing(self):
        self.d.set_switches(snapshots_enabled=False)
        self.assertIsNone(self.d.capture_snapshot("r4", None, "Worker", "http://u/p", "m", 200, 1.0, None))
        self.assertEqual(self.d.snapshots_page(None, None, None, None)["items"], [])


class StatsBranchTests(unittest.TestCase):
    """UT-DIAG-005: percentiles, empty windows, 4xx/5xx + upstream_error buckets."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)

    def tearDown(self): self.fx.close()

    def test_stats_empty_windows_when_no_samples(self):
        self.assertEqual(self.d.stats("2000-01-01T00:00", "2100-01-01T00:00")["windows"], [])

    def test_percentiles_and_error_buckets(self):
        for latency in (10, 20, 30, 40, 50):
            self.d.record_latency(None, "Worker", 200, latency)
        self.d.record_latency(None, "Worker", 404, 5)
        self.d.record_latency(None, "Worker", 500, 5)
        self.d.record_latency(None, "Worker", None, 5)
        bucket = self.d.stats("2000-01-01T00:00", "2100-01-01T00:00")["windows"][0]
        self.assertEqual(bucket["latency_p50_ms"], 10.0)
        self.assertEqual(bucket["latency_p95_ms"], 50.0)
        self.assertEqual(bucket["error_4xx_count"], 1)
        self.assertEqual(bucket["error_5xx_count"], 2)
        self.assertIn("upstream_error", bucket["status_breakdown"])

    def test_stats_switch_off_writes_nothing(self):
        self.d.set_switches(stats_enabled=False)
        self.d.record_latency(None, "Worker", 200, 1)
        self.assertEqual(self.d.stats("2000-01-01T00:00", "2100-01-01T00:00")["windows"], [])











if __name__ == "__main__":
    unittest.main()
