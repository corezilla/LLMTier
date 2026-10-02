"""MT-DIAG-003 — 注入校验六分支（M006，层②/层③ K8，negative，P0）。

K8 组合行：(六类, 合法)/(任一类, enabled 非布尔)/(任一类, 缺字段)/
(delay, 越界)/(malformed_event, 非法 event type)/(fault_502, error_body 空)；
另覆盖 error_body 超长截断与 error_body 非字符串。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.inference_env import InferenceEnv


class InjectionValidationTests(InferenceEnv):
    def _expect_400(self, item, param):
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.set_injections(self.senior["id"], [item])
        self.assertEqual(("invalid_injection", 400), (cm.exception.code, cm.exception.status))
        self.assertEqual(param, cm.exception.param)

    def test_enabled_non_boolean_is_400(self):
        for bad in ("true", 1, None, []):
            self._expect_400({"type": "fault_502", "enabled": bad, "config": {"error_body": "x"}}, "enabled")

    def test_config_non_object_is_400(self):
        for bad in ("x", 5, [1]):
            self._expect_400({"type": "fault_502", "enabled": True, "config": bad}, "config")

    def test_missing_config_field_is_400(self):
        self._expect_400({"type": "fault_502", "enabled": True, "config": {}}, "error_body")
        self._expect_400({"type": "delay", "enabled": True, "config": {}}, "delay_ms")
        self._expect_400({"type": "rate_limit", "enabled": True, "config": {}}, "retry_after_sec")
        self._expect_400({"type": "stream_terminate", "enabled": True, "config": {}}, "stream_terminate_after_events")
        self._expect_400({"type": "malformed_event", "enabled": True, "config": {"malformed_after_events": 1}}, "malformed_event_type")

    def test_delay_out_of_range_is_400(self):
        for bad in (-1, 60001, 1.5, True, "5"):
            self._expect_400({"type": "delay", "enabled": True, "config": {"delay_ms": bad}}, "delay_ms")

    def test_malformed_event_type_invalid_is_400(self):
        for bad in ("nope", "", 1):
            self._expect_400({"type": "malformed_event", "enabled": True,
                              "config": {"malformed_after_events": 1, "malformed_event_type": bad}}, "malformed_event_type")

    def test_error_body_empty_or_non_string_is_400(self):
        self._expect_400({"type": "fault_502", "enabled": True, "config": {"error_body": ""}}, "error_body")
        self._expect_400({"type": "fault_502", "enabled": True, "config": {"error_body": 5}}, "error_body")

    def test_error_body_over_512_is_truncated(self):
        body = "z" * 900
        stored = self.fx.app.diagnostics.set_injections(self.senior["id"],
                                                       [{"type": "fault_502", "enabled": True, "config": {"error_body": body}}])
        stored_body = stored[0]["config"]["error_body"]
        self.assertEqual(512, len(stored_body.encode()))
        self.assertTrue(stored_body.startswith("z"))

    def test_range_boundaries_accepted(self):
        # 逐类型独立断言（UPSERT 同类型会替换，避免同轮互相覆盖读回）
        def stored_of(kind, value_field, value):
            item = {"type": kind, "enabled": True, "config": {value_field: value}}
            rows = self.fx.app.diagnostics.set_injections(self.senior["id"], [item])
            return next(r for r in rows if r["type"] == kind)
        # 读回按 injection_type 排序（delay < rate_limit），取本类型行断言
        self.assertEqual(0, stored_of("delay", "delay_ms", 0)["config"]["delay_ms"])
        self.assertEqual(60000, stored_of("delay", "delay_ms", 60000)["config"]["delay_ms"])
        self.assertEqual(0, stored_of("rate_limit", "retry_after_sec", 0)["config"]["retry_after_sec"])
        self.assertEqual(300, stored_of("rate_limit", "retry_after_sec", 300)["config"]["retry_after_sec"])
        rows = self.fx.app.diagnostics.set_injections(
            self.senior["id"],
            [{"type": "stream_terminate", "enabled": True, "config": {"stream_terminate_after_events": 1}}])
        term = next(r for r in rows if r["type"] == "stream_terminate")
        self.assertEqual(1, term["config"]["stream_terminate_after_events"])

    def test_validation_failure_writes_nothing(self):
        with self.assertRaises(Exception):
            self.fx.app.diagnostics.set_injections(self.senior["id"],
                                                   [{"type": "fault_502", "enabled": True, "config": {"error_body": "ok"}},
                                                    {"type": "delay", "enabled": True, "config": {"delay_ms": 99999}}])
        self.assertEqual([], self.fx.app.diagnostics.injections(self.senior["id"]))


if __name__ == "__main__":
    unittest.main()
