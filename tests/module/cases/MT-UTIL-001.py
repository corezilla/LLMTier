"""MT-UTIL-001 — Store 组装后连接行为（M007 util，层① 接口行为，boundary，P0）。

组装保证（经公开入口 Application 组装后）：连接 PRAGMA（foreign_keys=1、wal）、
每线程一连接、fd 基线稳定（多请求不泄漏）、close 释放 fd。
ENV-1 组装隔离库 + ENV-2 loopback HTTP（fd 基线经真实请求栈）。
"""
from __future__ import annotations

import os
import threading
import unittest
from http.server import ThreadingHTTPServer

from http_api.app import Application, handler_factory
from tests.common.fakes import AppFixture


class PragmaTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()

    def tearDown(self):
        self.fx.close()

    def test_foreign_keys_and_wal_on_connection(self):
        conn = self.fx.app.store.connection()
        self.assertEqual(1, conn.execute("PRAGMA foreign_keys").fetchone()[0])
        self.assertEqual("wal", conn.execute("PRAGMA journal_mode").fetchone()[0].lower())

    def test_thread_local_connections(self):
        conn_main = self.fx.app.store.connection()
        seen = {}
        def worker():
            seen["conn"] = self.fx.app.store.connection()
        t = threading.Thread(target=worker); t.start(); t.join()
        self.assertIsNot(conn_main, seen["conn"])
        self.assertIs(conn_main, self.fx.app.store.connection())

    def test_close_releases_connection(self):
        store = self.fx.app.store
        conn = store.connection()
        store.close()
        self.assertIsNone(getattr(store._local, "connection", None))
        self.assertRaises(Exception, conn.execute, "SELECT 1")


class FdBaselineTests(unittest.TestCase):
    """组装后 fd 基线：N 次 HTTP 请求后 fd 数不随请求增长（M001 finally close × M007）。"""

    @classmethod
    def setUpClass(cls):
        cls.fx = AppFixture(); cls.fx.seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(cls.fx.app))
        cls.port = cls.server.server_address[1]
        import threading
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.fx.close()

    def _open_fds(self):
        return len(os.listdir("/dev/fd"))

    def test_fd_baseline_stable_across_requests(self):
        import urllib.request
        baseline = None
        for round_no in range(3):
            for _ in range(15):
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/healthz") as resp:
                    resp.read()
            current = self._open_fds()
            if round_no == 0:
                baseline = current
        self.assertLessEqual(current, baseline + 2)


if __name__ == "__main__":
    unittest.main()
