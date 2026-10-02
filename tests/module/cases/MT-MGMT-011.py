"""MT-MGMT-011 — 固定 tier 删除分支（M004，层②，negative，P1；§1.5.1 a16）。

删除固定 service level→409 `fixed_service_level`，资源不变。
（对照 `src/management/registry.py::delete_service_level`。）
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.module.cases.support.http_env import LoopbackEnv


class FixedTierDeleteTests(LoopbackEnv):
    def test_delete_fixed_tier_is_409_fixed_service_level(self):
        _, tier, headers = self.request("GET", "/v1/service-levels/Worker")
        status, payload, _ = self.request("DELETE", "/v1/service-levels/Worker",
                                          headers={"If-Match": headers.get("ETag", "")})
        self.assertEqual(409, status)
        self.assertEqual("fixed_service_level", payload["error"]["code"])

    def test_resource_unchanged_after_rejected_delete(self):
        _, before, _ = self.request("GET", "/v1/service-levels/Worker")
        self.request("DELETE", "/v1/service-levels/Worker", headers={"If-Match": '"Worker.v1"'})
        _, after, _ = self.request("GET", "/v1/service-levels/Worker")
        self.assertEqual(before, after)

    def test_all_fixed_tiers_reject_delete(self):
        for tier in ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1"):
            status, payload, _ = self.request("DELETE", f"/v1/service-levels/{tier}",
                                              headers={"If-Match": f'"{tier}.v1"'})
            self.assertEqual((409, "fixed_service_level"), (status, payload["error"]["code"]), tier)


if __name__ == "__main__":
    unittest.main()
