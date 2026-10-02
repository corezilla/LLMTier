"""MT-API-009 — `_static` 三分支（M001，层②，security，P1）。

分支：`../` 目录穿越→404；缺失文件→404；`/ui/`→index.html。
原始路径注入（不做 URL 规范化），真实 webui 产物。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class StaticBranchTests(LoopbackEnv):
    def test_traversal_is_404(self):
        for path in ("/ui/../http_api/app.py", "/ui/../../etc/passwd", "/ui/../util/store.py"):
            status, payload, _ = self.raw_request("GET", path)
            self.assertEqual(404, status, path)
            self.assertIn(b"not_found", payload)

    def test_missing_file_is_404(self):
        status, payload, _ = self.request("GET", "/ui/does-not-exist.css")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])

    def test_ui_root_maps_to_index(self):
        status, _, headers = self.request("GET", "/ui/")
        self.assertEqual(200, status)
        self.assertEqual("text/html", headers.get("Content-Type", "").split(";")[0])

    def test_root_path_serves_index_too(self):
        status, body, _ = self.request("GET", "/")
        self.assertEqual(200, status)
        text = body.decode() if isinstance(body, bytes) else body
        self.assertIn("LLMTier", text)


if __name__ == "__main__":
    unittest.main()
