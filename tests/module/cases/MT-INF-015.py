"""MT-INF-015 — 超大 response 边界内归一（M003，层②，boundary，P1；§1.5.1 c3）。

超大 body / 超多事件在模块边界内完整归一、不越界崩溃、恰好一个 terminal；
超 2 MB 下游响应预算归系统层（G-TRANSPORT-BUDGET-1，不在本层）。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class OversizeTests(InferenceEnv):
    def test_two_megabyte_output_normalized(self):
        self.upstream_mode("oversize")
        result = self.fx.app.responses.create("consumer", "req_big", RESPONSE_BODY)
        self.assertEqual("completed", result["status"])
        text = result["output"][0]["content"][0]["text"]
        self.assertEqual(2 * 1024 * 1024, len(text))
        row = self.head_record("req_big")
        self.assertEqual("measured", row["measurement_status"])

    def test_many_events_normalized(self):
        self.upstream_mode("many_events", events=3000)
        result = self.fx.app.responses.create("consumer", "req_many", RESPONSE_BODY)
        self.assertEqual("completed", result["status"])
        row = self.head_record("req_many")
        self.assertEqual("measured", row["measurement_status"])

    def test_service_remains_healthy_after_oversize(self):
        self.upstream_mode("oversize")
        self.fx.app.responses.create("consumer", "req_big2", RESPONSE_BODY)
        self.upstream_mode("ok")
        result = self.fx.app.responses.create("consumer", "req_ok_after_big", RESPONSE_BODY)
        self.assertEqual("completed", result["status"])


if __name__ == "__main__":
    unittest.main()
