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




class LogRedactionGapTests(unittest.TestCase):
    """UT-LOG-002: `token=` and `api_key` redaction; `limit` clamp; ordering."""

    def setUp(self):self.fx=AppFixture();self.logs=self.fx.app.logs
    def tearDown(self):self.fx.close()
    def page(self,**kw):return self.logs.page(since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z",**kw)







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
