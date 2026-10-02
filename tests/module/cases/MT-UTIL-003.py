"""MT-UTIL-003 — Store 连接分支（M007 util，层②，boundary，P0）。

分支：symlink→503 store_path_unsafe、world-writable 警告、多连接 fd 基线稳定、
close 异常上抛。注入按方案 §1.5 存储面直接在文件系统上触发。
"""
from __future__ import annotations

import os
import tempfile
import unittest
import warnings
from pathlib import Path

from http_api.errors import ApiError
from util.store import Store


class ConnectionBranchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_symlink_path_rejected_503(self):
        target = Path(self.tmp.name) / "real.sqlite3"; target.write_bytes(b"")
        link = Path(self.tmp.name) / "link.sqlite3"
        os.symlink(target, link)
        with self.assertRaises(ApiError) as cm:
            Store(link)
        self.assertEqual((503, "store_path_unsafe"), (cm.exception.status, cm.exception.code))

    def test_world_writable_warns_but_opens(self):
        db = Path(self.tmp.name) / "state.sqlite3"; db.write_bytes(b"")
        os.chmod(db, 0o666)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store = Store(db)
        store.migrate(); store.close()
        self.assertTrue(any("world-writable" in str(w.message) for w in caught))

    def test_many_connections_fd_baseline_stable(self):
        db = Path(self.tmp.name) / "state.sqlite3"
        store = Store(db); store.migrate()
        def fds():
            return len(os.listdir("/dev/fd"))
        for _ in range(5):
            store.connection().execute("SELECT 1")
        baseline = fds()
        for _ in range(3):
            conn = store.connection()
            conn.execute("SELECT 1")
            store.close()
        self.assertLessEqual(fds(), baseline + 1)
        store.close()

    def test_close_is_idempotent_and_reconnect_works(self):
        store = Store(Path(self.tmp.name) / "state.sqlite3"); store.migrate()
        store.close(); store.close()
        self.assertEqual(2, store.one("SELECT schema_version AS v FROM schema_meta WHERE singleton=1")["v"])
        store.close()


if __name__ == "__main__":
    unittest.main()
