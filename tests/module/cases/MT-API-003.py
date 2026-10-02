"""MT-API-003 — 组装后静态交付与空库就绪（M001，层①，security，P1）。

组装保证：真实 `src/web_ui/` 产物经 /ui/* 交付（/ui/→index.html）；空库
（未播种）时 /readyz→503 not_ready、/healthz 始终可达。
"""
from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory
from tests.common.fakes import AppFixture
from tests.module.cases.support.http_env import LoopbackEnv


class EmptyAppTests(unittest.TestCase):
    """空库组装实例（ENV-1 无播种 + ENV-2）。"""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def _get(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_empty_store_readyz_is_503_not_ready(self):
        status, payload = self._get("/readyz")
        self.assertEqual(503, status)
        self.assertEqual("not_ready", payload["status"])
        self.assertTrue(all(m["availability"] == "unavailable" for m in payload["models"]))

    def test_healthz_reachable_on_empty_store(self):
        status, payload = self._get("/healthz")
        self.assertEqual(200, status)
        self.assertEqual("ok", payload["status"])


class StaticDeliveryTests(LoopbackEnv):
    def test_ui_root_serves_index_html(self):
        status, body, headers = self.request("GET", "/ui/")
        self.assertEqual(200, status)
        text = body.decode() if isinstance(body, bytes) else body
        self.assertIn("LLMTier", text)
        self.assertEqual("text/html", headers.get("Content-Type", "").split(";")[0])

    def test_ui_serves_real_app_js(self):
        status, body, headers = self.request("GET", "/ui/app.js")
        self.assertEqual(200, status)
        text = body.decode() if isinstance(body, bytes) else body
        self.assertIn("dispatchUiError", text)
        self.assertEqual("no-store", headers.get("Cache-Control"))


if __name__ == "__main__":
    unittest.main()
