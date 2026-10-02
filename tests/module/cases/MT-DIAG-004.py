"""MT-DIAG-004 — set_injections 三分支 + 启用/撤销迁移（M006，层②/层④ T10/T11，negative，P0）。

分支：非 list→400；未知 deployment→404；`items:[]` 撤销全部（DELETE）。
迁移 T10（无→启用→命中）与 T11（启用→撤销→None）。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.inference_env import InferenceEnv


class SetInjectionsTests(InferenceEnv):
    def test_non_list_is_400(self):
        for bad in ("x", 5, {"type": "fault_502"}):
            with self.assertRaises(Exception) as cm:
                self.fx.app.diagnostics.set_injections(self.senior["id"], bad)
            self.assertEqual(("invalid_injection", 400), (cm.exception.code, cm.exception.status))

    def test_unknown_deployment_is_404(self):
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.set_injections("dep_missing", [])
        self.assertEqual(("not_found", 404), (cm.exception.code, cm.exception.status))
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.injections("dep_missing")
        self.assertEqual(("not_found", 404), (cm.exception.code, cm.exception.status))

    def test_t10_enable_then_hit(self):
        self.assertIsNone(self.fx.app.diagnostics.enabled_injection(self.senior["id"]))
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "rate_limit", "enabled": True, "config": {"retry_after_sec": 3}}])
        hit = self.fx.app.diagnostics.enabled_injection(self.senior["id"])
        self.assertIsNotNone(hit)
        self.assertEqual("rate_limit", hit["injection_type"])
        self.assertEqual(3, hit["retry_after_sec"])

    def test_t11_revoke_by_empty_items(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "rate_limit", "enabled": True, "config": {"retry_after_sec": 3}},
                                                {"type": "stream_terminate", "enabled": True,
                                                 "config": {"stream_terminate_after_events": 2}}])
        self.assertEqual(2, len(self.fx.app.diagnostics.injections(self.senior["id"])))
        self.fx.app.diagnostics.set_injections(self.senior["id"], [])
        self.assertEqual([], self.fx.app.diagnostics.injections(self.senior["id"]))
        self.assertIsNone(self.fx.app.diagnostics.enabled_injection(self.senior["id"]))
        self.assertIsNone(self.fx.app.diagnostics.enabled_stream_injection(self.senior["id"]))

    def test_upsert_replaces_same_type(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "rate_limit", "enabled": True, "config": {"retry_after_sec": 1}}])
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "rate_limit", "enabled": True, "config": {"retry_after_sec": 9}}])
        stored = self.fx.app.diagnostics.injections(self.senior["id"])
        self.assertEqual(1, len(stored))
        self.assertEqual(9, stored[0]["config"]["retry_after_sec"])

    def test_injections_are_scoped_to_deployment(self):
        self.fx.app.diagnostics.set_injections(self.senior["id"],
                                               [{"type": "delay", "enabled": True, "config": {"delay_ms": 1}}])
        self.assertEqual([], self.fx.app.diagnostics.injections(self.embedding["id"]))
        self.assertIsNone(self.fx.app.diagnostics.enabled_injection(self.embedding["id"]))


if __name__ == "__main__":
    unittest.main()
