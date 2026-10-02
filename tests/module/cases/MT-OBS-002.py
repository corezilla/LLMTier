"""MT-OBS-002 — 诊断开关分支（M005 observability，层② + 层④ T9，normal，P1）。

覆盖：`/v1/diagnostics` 经 M001 端点切换快照/统计开关的四个分支——默认关、
开、部分更新保留另一开关、关闭零写入（`off → on → off` 迁移 T9）；外加
非布尔开关 / 未知字段 400（形状校验在 M001，禁入 M004 mutate → 不落审计行）。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP（`PerTestLoopbackEnv`：每个
test 方法一份全新库与 loopback server，「默认关」与「零写入」计数因此不跨
用例污染，无需再用 PATCH 复位初态）；上游为 `_test_adapter` 边界替身
（`FakeAdapter`，不触真实网络）。
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import PerTestLoopbackEnv

SINCE = "2000-01-01T00:00:00Z"
FUTURE = "2999-01-01T00:00:00Z"
RESPONSE_BODY = {"model": "Worker", "input": "hi", "stream": True, "store": False}
SWITCH_FIELDS = {"snapshots_enabled", "stats_enabled"}
CHAIN_STAGES = {"received", "validated", "routed", "upstream_started", "upstream_ended", "completed"}


class MTOBS002DiagnosticsSwitches(PerTestLoopbackEnv):
    """开关四分支 + 迁移 T9（off → on → off）。"""

    def _read(self):
        status, payload, _ = self.request("GET", "/v1/diagnostics")
        self.assertEqual(200, status)
        return payload

    def _patch(self, body):
        return self.request("PATCH", "/v1/diagnostics", body)

    def _call(self):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            status, _, headers = self.request("POST", "/v1/responses", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual(200, status)
        return headers["X-Request-ID"]

    def _snapshots(self):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}")
        self.assertEqual(200, status)
        return payload["items"]

    def _stats(self):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/stats?since={SINCE}&until={FUTURE}")
        self.assertEqual(200, status)
        return payload["windows"]

    def _trace(self, request_id):
        status, payload, _ = self.request("GET", f"/v1/trace/{request_id}")
        self.assertEqual(200, status)
        return payload

    def _switch_audits(self):
        return [row for row in self.fx.app.audit.page(limit=200)["data"]
                if row["action"] == "diagnostics.switch.update"]

    def test_switches_are_off_by_default_on_a_fresh_store(self):
        self.assertEqual({"snapshots_enabled": False, "stats_enabled": False}, self._read())
        self.assertEqual([], self._switch_audits())

    def test_patch_enables_both_switches_and_audit_records_success(self):
        status, payload, _ = self._patch({"snapshots_enabled": True, "stats_enabled": True})
        self.assertEqual(200, status)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": True}, payload)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": True}, self._read())
        audits = self._switch_audits()
        self.assertEqual(1, len(audits))
        self.assertEqual("success", audits[0]["result"])
        self.assertEqual("diagnostics", audits[0]["target"])

    def test_partial_patch_preserves_the_other_switch(self):
        self._patch({"snapshots_enabled": True, "stats_enabled": True})
        status, payload, _ = self._patch({"stats_enabled": False})
        self.assertEqual(200, status)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": False}, payload)
        status, payload, _ = self._patch({"snapshots_enabled": True})
        self.assertEqual(200, status)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": False}, payload)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": False}, self._read())
        self.assertEqual(3, len(self._switch_audits()))

    def test_empty_patch_keeps_both_switches(self):
        self._patch({"snapshots_enabled": True, "stats_enabled": False})
        status, payload, _ = self._patch({})
        self.assertEqual(200, status)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": False}, payload)
        self.assertEqual(SWITCH_FIELDS, set(payload))
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": False}, self._read())

    def test_non_boolean_switch_is_400_and_writes_no_audit_row(self):
        for key in ("snapshots_enabled", "stats_enabled"):
            status, payload, _ = self._patch({key: "yes"})
            self.assertEqual(400, status)
            self.assertEqual("invalid_request", payload["error"]["code"])
            self.assertEqual(key, payload["error"]["param"])
        # 请求形状在 M001 层被拒 → 不进入 M004 mutate → 无审计行、状态不变
        self.assertEqual([], self._switch_audits())
        self.assertEqual({"snapshots_enabled": False, "stats_enabled": False}, self._read())

    def test_unknown_switch_field_is_400_and_leaves_state_untouched(self):
        self._patch({"snapshots_enabled": True, "stats_enabled": True})
        status, payload, _ = self._patch({"tracing_enabled": True})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])
        self.assertEqual(1, len(self._switch_audits()))
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": True}, self._read())

    def test_disabled_switches_write_no_snapshot_and_no_stats_row(self):
        self._patch({"snapshots_enabled": True, "stats_enabled": True})
        on_request = self._call()
        self.assertEqual(1, len([i for i in self._snapshots() if i["request_id"] == on_request]))
        self.assertNotEqual([], self._stats())
        self._patch({"snapshots_enabled": False, "stats_enabled": False})
        self.assertEqual({"snapshots_enabled": False, "stats_enabled": False}, self._read())
        before_snapshots, before_stats = self._snapshots(), self._stats()
        off_request = self._call()
        self.assertEqual(before_snapshots, self._snapshots())
        self.assertEqual(before_stats, self._stats())
        # 观测 seam 上同样可见「未记录」：trace 的 snapshot 为空、join 出的快照为 None
        view = self._trace(off_request)
        self.assertIsNone(view["snapshot"])
        stages = {stage["stage"]: stage for stage in view["stages"]}
        self.assertIsNone(stages["upstream_ended"]["detail"]["snapshot_id"])
        # 推理本身不受影响：trace 链仍完整
        self.assertEqual(CHAIN_STAGES, set(stages))

    def test_snapshots_off_keeps_stats_on(self):
        self._patch({"snapshots_enabled": True, "stats_enabled": True})
        self._patch({"snapshots_enabled": False, "stats_enabled": True})
        self.assertEqual({"snapshots_enabled": False, "stats_enabled": True}, self._read())
        before_snapshots, before_stats = self._snapshots(), self._stats()
        request_id = self._call()
        self.assertEqual(before_snapshots, self._snapshots())
        self.assertNotEqual(before_stats, self._stats())
        self.assertIsNone(self._trace(request_id)["snapshot"])

    def test_stats_off_keeps_snapshots_on(self):
        self._patch({"snapshots_enabled": True, "stats_enabled": True})
        self._patch({"snapshots_enabled": True, "stats_enabled": False})
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": False}, self._read())
        before_snapshots, before_stats = self._snapshots(), self._stats()
        request_id = self._call()
        self.assertNotEqual(before_snapshots, self._snapshots())
        self.assertEqual(before_stats, self._stats())
        self.assertIsNotNone(self._trace(request_id)["snapshot"])


if __name__ == "__main__":
    unittest.main()
