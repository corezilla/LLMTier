import json
import sqlite3
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory
from http_api.errors import ApiError

from tests.common.fakes import AppFixture


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
        # RISK-LOG-1 closed: `_SENSITIVE` now consumes the value after the key
        # name (`api[_-]?key|apikey`/`secret`/`access_key[_id]`/`token` + `[:=]`),
        # so the secret value never reaches `operational_logs`.
        self.logs.record("info","m","e","api_key=abc123")
        message=self.page()["data"][0]["message"]
        self.assertIn("[REDACTED]",message)
        self.assertNotIn("abc123",message)

    def test_api_key_value_redaction(self):
        """RISK-LOG-1 closed: apikey/api_key values are redacted, not just the key name."""
        self.logs.record("info","apikey","e","apikey=9832")
        self.logs.record("info","token","e","token=abcd1234")
        by_module={e["module"]:e["message"] for e in self.page()["data"]}
        self.assertNotIn("9832",by_module["apikey"])
        self.assertNotIn("abcd1234",by_module["token"])

    def test_access_key_value_redacted(self):
        # `access_key=AKIA...` previously did not match at all; now the value is gone.
        self.logs.record("info","m","e","access_key=AKIA123456")
        self.assertNotIn("AKIA123456",self.page()["data"][0]["message"])

    def test_x_api_key_header_value_redacted(self):
        self.logs.record("info","m","e","X-Api-Key: sk-live-1234567890")
        self.assertNotIn("sk-live-1234567890",self.page()["data"][0]["message"])

    def test_secret_redacted(self):
        self.logs.record("info","m","e","client_secret: supersecretvalue")
        self.assertNotIn("supersecretvalue",self.page()["data"][0]["message"])




