"""MT-UTIL-005 — 嵌套事务 409 + 迁移中途失败回滚（M007 util，层②/层④ T13，recovery，P1）。

E-UTIL-NESTED-TXN：同连接重复 BEGIN→409；迁移中途失败（缺列索引注入）→
整体回滚为可启动空库。存储面注入按方案 §1.5 直接在真实 Store 上触发。
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from http_api.errors import ApiError
from util.store import Store


class NestedTxnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "state.sqlite3")
        self.store.migrate()

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def test_nested_begin_is_409_nested_txn(self):
        with self.store.transaction(True) as conn:
            with self.assertRaises(ApiError) as cm:
                with self.store.transaction(True):
                    pass
            self.assertEqual((409, "E-UTIL-NESTED-TXN"), (cm.exception.status, cm.exception.code))

    def test_txn_helper_yields_caller_connection_without_nested_begin(self):
        with self.store.transaction(True) as outer:
            from util.store import txn
            with txn(self.store, outer) as inner:
                self.assertIs(outer, inner)


class MigrationRollbackTests(unittest.TestCase):
    def test_mid_migration_failure_rolls_back_to_reusable_empty(self):
        tmp = tempfile.TemporaryDirectory()
        db = Path(tmp.name) / "state.sqlite3"
        store = Store(db)
        # 存储面注入：SQLite 页配额（经 Store 公开 connection()）逼停迁移中途语句
        store.connection().execute("PRAGMA max_page_count=3")
        with self.assertRaises(sqlite3.OperationalError):
            store.migrate()
        # 回滚证据：零残留（无半写）
        tables = [r[0] for r in store.connection().execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertEqual([], tables)
        store.close()
        # 可重新启动：新连接（默认配额）完整迁移
        store2 = Store(db)
        store2.migrate()
        self.assertEqual(2, store2.one("SELECT schema_version AS v FROM schema_meta WHERE singleton=1")["v"])
        tables2 = {r[0] for r in store2.connection().execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("service_levels", tables2)
        store2.close(); tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
