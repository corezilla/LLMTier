"""MT-API-004 — 路由命中/未命中分支（M001，层②，negative，P0）。

组装保证：未命中端点→404 `not_found`（错误信封一致）；命中分支正常返回；
已知路径未支持方法同样落 404 兜底出口。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class RouteBranchTests(LoopbackEnv):
    def test_unknown_route_is_404_envelope(self):
        status, payload, headers = self.request("GET", "/v1/nope")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])
        self.assertTrue(headers.get("X-Request-ID"))

    def test_unknown_top_level_path_is_404(self):
        status, payload, _ = self.request("GET", "/nope/deeper")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])

    def test_unsupported_method_on_known_path_is_404(self):
        status, payload, _ = self.request("DELETE", "/healthz")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])

    def test_hit_branch_returns_200(self):
        status, payload, _ = self.request("GET", "/v1/models")
        self.assertEqual(200, status)
        self.assertEqual("list", payload["object"])


if __name__ == "__main__":
    unittest.main()
