import json
import sqlite3
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory
from http_api.errors import ApiError

from .fakes import AppFixture


class LogTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.logs=self.fx.app.logs
    def tearDown(self):self.fx.close()
    def page(self,**kw):return self.logs.page(since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z",**kw)
    def test_record(self):self.logs.record("info","m","e","hello");self.assertEqual(self.page()["data"][0]["message"],"hello")
    def test_bearer_redacted(self):self.logs.record("info","m","e","Bearer abcdefghijklmnop");self.assertNotIn("abcdefghijklmnop",self.page()["data"][0]["message"])
    def test_authorization_redacted(self):self.logs.record("info","m","e","Authorization header");self.assertNotIn("Authorization",self.page()["data"][0]["message"])
    def test_newline_removed(self):self.logs.record("info","m","e","a\nb");self.assertEqual(self.page()["data"][0]["message"],"a b")
    def test_message_bounded(self):self.logs.record("info","m","e","x"*900);self.assertLessEqual(len(self.page()["data"][0]["message"]),512)
    def test_filter_level(self):self.logs.record("error","m","e","x");self.logs.record("info","m","e","y");self.assertTrue(all(x["level"]=="error" for x in self.page(level="error")["data"]))
    def test_filter_module(self):self.logs.record("info","one","e","x");self.logs.record("info","two","e","y");self.assertTrue(all(x["module"]=="one" for x in self.page(module="one")["data"]))


class LogRedactionGapTests(unittest.TestCase):
    """UT-LOG-002: `token=` and `api_key` redaction; `limit` clamp; ordering."""

    def setUp(self):self.fx=AppFixture();self.logs=self.fx.app.logs
    def tearDown(self):self.fx.close()
    def page(self,**kw):return self.logs.page(since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z",**kw)

    def test_token_query_redacted(self):
        self.logs.record("info","m","e","GET /x?token=supersecretvalue")
        self.assertNotIn("supersecretvalue",self.page()["data"][0]["message"])

    def test_api_key_redacted(self):
        # RISK-LOG-1 登记：`_SENSITIVE` 的 `api[_-]?key` 分支只匹配键名，不捕获值
        # （`token=` 分支才有 `\s*[=:]\s*\S+`）。设计 §40 log-design §6.3 固定该正则、
        # RISK-LOG-1 状态"观察"，故此处锁定**当前已文档化行为**：键名脱敏、值保留。
        # 注意：旧断言用含 "secret" 的值会因 `secret` 分支误命中而假通过，改用中性值。
        self.logs.record("info","m","e","api_key=abc123")
        message=self.page()["data"][0]["message"]
        self.assertIn("[REDACTED]",message)
        self.assertIn("abc123",message)  # 已知缺口（RISK-LOG-1）：值未脱敏

    def test_api_key_value_redaction_gap(self):
        """RISK-LOG-1：api_key/apikey 的值当前不脱敏（设计已登记，不改代码）。"""
        self.logs.record("info","apikey","e","apikey=9832")
        self.logs.record("info","token","e","token=abcd1234")
        by_module={e["module"]:e["message"] for e in self.page()["data"]}
        self.assertIn("9832",by_module["apikey"])  # 已知缺口：值未脱敏
        self.assertNotIn("abcd1234",by_module["token"])  # token= 分支正确脱敏

    def test_secret_redacted(self):
        self.logs.record("info","m","e","client_secret: supersecretvalue")
        self.assertNotIn("supersecretvalue",self.page()["data"][0]["message"])

    def test_limit_clamped_to_200(self):
        # Seed MORE than the cap so removing `min(limit,200)` is observable.
        for index in range(205):
            self.logs.record("info","m","e",str(index))
        self.assertEqual(len(self.page(limit=500)["data"]),200)
        # Below the cap the caller's limit is honored unchanged.
        self.assertEqual(len(self.page(limit=7)["data"]),7)

    def test_page_requires_window(self):
        with self.assertRaises(ApiError) as cm:
            self.logs.page()
        self.assertEqual((cm.exception.status,cm.exception.code),(400,"invalid_request"))


class LogHttpFailureTests(unittest.TestCase):
    """UT-LOG-002: `/v1/logs` requires the window; a store failure is 503."""

    @classmethod
    def setUpClass(cls):
        cls.fx=AppFixture()
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),handler_factory(cls.fx.app))
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.fx.close()

    def get(self,path):
        request=urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",method="GET")
        try:
            with urllib.request.urlopen(request) as response:return response.status,json.loads(response.read())
        except urllib.error.HTTPError as exc:return exc.code,json.loads(exc.read())

    def test_missing_window_is_400(self):
        status,payload=self.get("/v1/logs")
        self.assertEqual((status,payload["error"]["code"]),(400,"invalid_request"))

    def test_store_failure_is_503(self):
        original=self.fx.app.logs.page
        self.fx.app.logs.page=lambda *_a,**_k:(_ for _ in ()).throw(sqlite3.OperationalError("locked"))
        try:
            status,payload=self.get("/v1/logs?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z")
        finally:
            self.fx.app.logs.page=original
        self.assertEqual((status,payload["error"]["code"]),(503,"usage_store_unavailable"))
