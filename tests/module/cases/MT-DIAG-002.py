"""MT-DIAG-002 — 注入配置组装（M006，层①，negative，P0）。

组装保证：六类注入经公开入口 `set_injections` 全部可配置并读回一致；非法类型
→400 `invalid_injection`；命中确定（`enabled_injection` 按优先级首个命中）；
前置/流阶段分离；traces 时间窗与分页。
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv

ALL_SIX = [
    ({"type": "fault_502", "config": {"error_body": "boom"}}),
    ({"type": "fault_503", "config": {"error_body": "down"}}),
    ({"type": "delay", "config": {"delay_ms": 5}}),
    ({"type": "rate_limit", "config": {"retry_after_sec": 1}}),
    ({"type": "stream_terminate", "config": {"stream_terminate_after_events": 1}}),
    ({"type": "malformed_event", "config": {"malformed_after_events": 1, "malformed_event_type": "invalid_json"}}),
]


class InjectionConfigTests(InferenceEnv):
    def test_all_six_injection_types_configure_and_read_back(self):
        items = [{**item, "enabled": True} for item in ALL_SIX]
        stored = self.fx.app.diagnostics.set_injections(self.senior["id"], items)
        self.assertEqual(6, len(stored))
        self.assertEqual({item["type"] for item in ALL_SIX}, {s["type"] for s in stored})
        read_back = self.fx.app.diagnostics.injections(self.senior["id"])
        self.assertEqual(6, len(read_back))
        for item in read_back:
            self.assertTrue(item["enabled"])
            self.assertEqual(self.senior["id"], item["deployment_id"])

    def test_pre_call_priority_fault_502_first(self):
        items = [{"type": "rate_limit", "enabled": True, "config": {"retry_after_sec": 1}},
                 {"type": "delay", "enabled": True, "config": {"delay_ms": 5}},
                 {"type": "fault_503", "enabled": True, "config": {"error_body": "d"}},
                 {"type": "fault_502", "enabled": True, "config": {"error_body": "b"}}]
        self.fx.app.diagnostics.set_injections(self.senior["id"], items)
        self.assertEqual("fault_502", self.fx.app.diagnostics.enabled_injection(self.senior["id"])["injection_type"])
        # 流阶段注入独立于前置阶段
        self.assertIsNone(self.fx.app.diagnostics.enabled_stream_injection(self.senior["id"]))

    def test_disabled_injection_does_not_hit(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                              [{"type": "fault_502", "enabled": False, "config": {"error_body": "off"}}])
        self.assertIsNone(self.fx.app.diagnostics.enabled_injection(self.senior["id"]))
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            result = self.fx.app.responses.create("consumer", "req_diag_002", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual("completed", result["status"])

    def test_enabled_injection_hits_in_assembled_inference(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                              [{"type": "fault_502", "enabled": True, "config": {"error_body": "hit"}}])
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            self.fx.app.responses.create("consumer", "req_diag_002b", RESPONSE_BODY)
        except Exception as exc:
            self.assertEqual("provider_failure", exc.code)
        else:
            self.fail("injection did not hit")

    def test_unknown_injection_type_is_400(self):
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.set_injections(self.senior["id"],
                                                   [{"type": "meltdown", "enabled": True, "config": {}}])
        self.assertEqual(("invalid_injection", 400, "type"), (cm.exception.code, cm.exception.status, cm.exception.param))

    def test_traces_time_window_and_paging(self):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            for i in range(3):
                self.fx.app.responses.create("consumer", f"req_trace_{i}", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        page = self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", limit=2)
        self.assertEqual(2, len(page["items"]))
        self.assertTrue(page["has_more"])
        page2 = self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", limit=2,
                                               cursor=page["next_cursor"])
        self.assertEqual(1, len(page2["items"]))
        ids1 = {i["request_id"] for i in page["items"]}
        ids2 = {i["request_id"] for i in page2["items"]}
        self.assertFalse(ids1 & ids2)
        # 时间窗外为空
        empty = self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2000-01-02T00:00:00Z")
        self.assertEqual([], empty["items"])


if __name__ == "__main__":
    unittest.main()
