"""M006 libdiag unit gaps (UT-DIAG-002/003/004/005/006/007/008).

Real `DiagnosticsService` over an isolated temp store (ENV-1). No network.
Write-failure fail-open is exercised by dropping the diagnostic tables so the
in-service write raises and is swallowed (the store itself stays healthy).
"""
from __future__ import annotations

import unittest

from .fakes import AppFixture

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


class StreamWrapperTests(unittest.TestCase):
    """UT-DIAG-004/008: passthrough vs terminate vs malformed; stream priority; revoke."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        self.did = self.fx.app.registry.list_deployments()[0]["id"]
        self.base = [b"a\n", b"b\n", b"c\n"]

    def tearDown(self): self.fx.close()

    def test_passthrough_without_injection(self):
        self.assertEqual(list(self.d.stream_wrapper(self.did, self.base)), self.base)

    def test_stream_terminate_early_end(self):
        self.d.set_injections(self.did, [{"type": "stream_terminate", "config": {"stream_terminate_after_events": 1}, "enabled": True}])
        self.assertEqual(list(self.d.stream_wrapper(self.did, self.base)), [b"a\n"])

    def test_malformed_event_appends_broken_frame(self):
        self.d.set_injections(self.did, [{"type": "malformed_event", "config": {"malformed_after_events": 1, "malformed_event_type": "invalid_json"}, "enabled": True}])
        frames = list(self.d.stream_wrapper(self.did, self.base))
        self.assertEqual(frames[0], b"a\n")
        self.assertIn(b"response.malformed", frames[-1])

    def test_stream_injection_priority_is_terminate_first(self):
        self.d.set_injections(self.did, [
            {"type": "malformed_event", "config": {"malformed_after_events": 1, "malformed_event_type": "unknown_event_type"}, "enabled": True},
            {"type": "stream_terminate", "config": {"stream_terminate_after_events": 2}, "enabled": True},
        ])
        self.assertEqual(self.d.enabled_stream_injection(self.did)["injection_type"], "stream_terminate")

    def test_pre_call_injection_priority_is_fault_502_first(self):
        self.d.set_injections(self.did, [
            {"type": "delay", "config": {"delay_ms": 1}, "enabled": True},
            {"type": "rate_limit", "config": {"retry_after_sec": 1}, "enabled": True},
            {"type": "fault_502", "config": {"error_body": "x"}, "enabled": True},
        ])
        self.assertEqual(self.d.enabled_injection(self.did)["injection_type"], "fault_502")

    def test_empty_items_revokes_all(self):
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": True}])
        self.assertEqual(self.d.set_injections(self.did, []), [])
        self.assertEqual(self.d.injections(self.did), [])


class CursorContractGapTests(unittest.TestCase):
    """UT-DIAG-006: trace cursor format `first_ts|request_id`; correlation from stage detail."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics
        for rid in ("r1", "r2"):
            self.d.record_trace(rid, "received", None)
            self.d.record_trace(rid, "completed", None)

    def tearDown(self): self.fx.close()

    def test_trace_cursor_is_first_ts_pipe_request_id(self):
        first = self.d.traces(limit=1, **WINDOW)
        self.assertTrue(first["has_more"])
        self.assertIn("|", first["next_cursor"])
        parts = first["next_cursor"].split("|", 1)
        self.assertEqual(parts[1], first["items"][0]["request_id"])

    def test_correlation_id_taken_from_stage_detail(self):
        self.d.record_trace("r3", "received", {"x_correlation_id": "corr-1"}, correlation_id="corr-1")
        self.assertEqual(self.d.trace("r3")["correlation_id"], "corr-1")

    def test_snapshots_cursor_is_snapshot_id(self):
        self.d.set_switches(snapshots_enabled=True)
        self.d.capture_snapshot("r4", None, "Worker", "u", "m", 200, 1.0, None)
        page = self.d.snapshots_page(None, None, None, None, limit=1)
        row = self.fx.app.store.one("SELECT id FROM diagnostic_snapshots")
        self.assertEqual(page["items"][0]["id"], row["id"])


if __name__ == "__main__":
    unittest.main()
