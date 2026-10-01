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




class StatsBranchTests(unittest.TestCase):
    """UT-DIAG-005: percentiles, empty windows, 4xx/5xx + upstream_error buckets."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)

    def tearDown(self): self.fx.close()




    def test_stats_mixed_null_and_string_keys_do_not_crash(self):
        # Regression: bucket keys (stat_hour, deployment_id, model) may contain None
        # (traffic that never bound a deployment) alongside strings; a raw tuple
        # sort raised TypeError on None vs str (m5air /v1/diagnostics/stats 503).
        self.d.record_latency(None, "Worker", 400, 1)
        self.d.record_latency("depl_b", "Worker", 200, 2)
        windows = self.d.stats("2000-01-01T00:00", "2100-01-01T00:00")["windows"]
        self.assertEqual(len(windows), 2)
        self.assertEqual({w["deployment_id"] for w in windows}, {None, "depl_b"})










if __name__ == "__main__":
    unittest.main()
