"""MT-UTIL-002 — Store 组装后事务与迁移（M007 util，层①/层④ T12，recovery，P0）。

组装保证：回滚无半写、migrate 幂等、版本不匹配拒绝、并发启动安全。
ENV-1 组装隔离库。存储面注入按方案 §1.5 直接在真实 Store 上触发。
"""
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from http_api.errors import ApiError
from util.store import Store


class TxnRollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "state.sqlite3")
        self.store.migrate()

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def test_rollback_leaves_no_half_write(self):
        try:
            with self.store.transaction(True) as conn:
                conn.execute("INSERT INTO audit_events VALUES('a1','actor','act','t','success','2026-01-01T00:00:00Z',NULL)")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertEqual([], self.store.all("SELECT id FROM audit_events"))

    def test_migrate_idempotent(self):
        version1 = self.store.one("SELECT schema_version FROM schema_meta WHERE singleton=1")["schema_version"]
        self.store.migrate(); self.store.migrate()
        version2 = self.store.one("SELECT schema_version FROM schema_meta WHERE singleton=1")["schema_version"]
        self.assertEqual(version1, version2)

    def test_schema_version_mismatch_rejected(self):
        self.store.close()
        raw = sqlite3_connect(self.tmp.name)
        raw.execute("UPDATE schema_meta SET schema_version=99 WHERE singleton=1"); raw.close()
        store2 = Store(Path(self.tmp.name) / "state.sqlite3")
        with self.assertRaises(ApiError) as cm:
            store2.migrate()
        self.assertEqual((503, "schema_version_mismatch"), (cm.exception.status, cm.exception.code))
        store2.close()

    def test_concurrent_startup_both_migrate(self):
        self.store.close()
        errors = []
        def start():
            try:
                s = Store(Path(self.tmp.name) / "state.sqlite3"); s.migrate(); s.close()
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=start) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual([], errors)
        s = Store(Path(self.tmp.name) / "state.sqlite3"); s.migrate()
        self.assertEqual(1, len(s.all("SELECT * FROM schema_meta")))
        s.close()


def sqlite3_connect(directory):
    import sqlite3
    conn = sqlite3.connect(Path(directory) / "state.sqlite3", isolation_level=None)
    return conn


if __name__ == "__main__":
    unittest.main()
