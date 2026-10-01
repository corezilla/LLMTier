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




if __name__ == "__main__":
    unittest.main()
