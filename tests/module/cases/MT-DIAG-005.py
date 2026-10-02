"""MT-DIAG-005 — stream_wrapper 三态（M006，层②/层③ K4 流阶段行，boundary，P1）。

三态：无注入→透传（帧序与 `[DONE]` 完整）；`stream_terminate`→到点 return
（无 terminal、无 `[DONE]`）；`malformed_event`→到点追加畸形帧后 return。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.inference_env import InferenceEnv


class StreamWrapperTests(InferenceEnv):
    BASE_STREAM = [b"event: a\ndata: 1\n\n", b"event: b\ndata: 2\n\n",
                   b"event: c\ndata: 3\n\n", b"data: [DONE]\n\n"]

    def test_no_injection_passes_through_unchanged(self):
        out = list(self.fx.app.diagnostics.stream_wrapper(self.senior["id"], iter(self.BASE_STREAM)))
        self.assertEqual(self.BASE_STREAM, out)

    def test_stream_terminate_stops_at_configured_event(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "stream_terminate", "enabled": True,
                                                 "config": {"stream_terminate_after_events": 2}}])
        out = list(self.fx.app.diagnostics.stream_wrapper(self.senior["id"], iter(self.BASE_STREAM)))
        self.assertEqual(self.BASE_STREAM[:2], out)
        self.assertNotIn(b"[DONE]", b"".join(out))

    def test_stream_terminate_default_threshold_is_one(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "stream_terminate", "enabled": True,
                                                 "config": {"stream_terminate_after_events": 1}}])
        out = list(self.fx.app.diagnostics.stream_wrapper(self.senior["id"], iter(self.BASE_STREAM)))
        self.assertEqual(self.BASE_STREAM[:1], out)

    def test_malformed_event_appends_broken_frame_and_stops(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "malformed_event", "enabled": True,
                                                 "config": {"malformed_after_events": 2,
                                                            "malformed_event_type": "invalid_json"}}])
        out = list(self.fx.app.diagnostics.stream_wrapper(self.senior["id"], iter(self.BASE_STREAM)))
        self.assertEqual(self.BASE_STREAM[:2], out[:-1])
        self.assertIn(b"response.malformed", out[-1])
        self.assertNotIn(b"[DONE]", b"".join(out))

    def test_disabled_stream_injection_passes_through(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "stream_terminate", "enabled": False,
                                                 "config": {"stream_terminate_after_events": 1}}])
        out = list(self.fx.app.diagnostics.stream_wrapper(self.senior["id"], iter(self.BASE_STREAM)))
        self.assertEqual(self.BASE_STREAM, out)

    def test_other_deployment_injection_does_not_affect(self):
        self.fx.app.diagnostics.set_injections(self.embedding["id"],
                                               [{"type": "stream_terminate", "enabled": True,
                                                 "config": {"stream_terminate_after_events": 1}}])
        out = list(self.fx.app.diagnostics.stream_wrapper(self.senior["id"], iter(self.BASE_STREAM)))
        self.assertEqual(self.BASE_STREAM, out)


if __name__ == "__main__":
    unittest.main()
