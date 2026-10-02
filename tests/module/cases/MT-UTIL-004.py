"""MT-UTIL-004 — migrate 四拒绝出口 + 幂等（M007 util，层②，recovery，P0）。

出口：schema_unknown（有表无 schema_meta）→503、schema_version_mismatch→503、
schema_integrity_failed（页损坏注入）→503、重复 migrate 幂等。
存储面注入按方案 §1.5 直接在真实 Store/文件上触发（§1.5.1 a31/a32/a33）。
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from http_api.errors import ApiError
from util.store import Store


class MigrateRejectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "state.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def _raw(self):
        conn = sqlite3.connect(self.db, isolation_level=None)
        return conn

    def test_tables_without_schema_meta_is_schema_unknown(self):
        raw = self._raw()
        raw.execute("CREATE TABLE legacy (id INTEGER)"); raw.close()
        store = Store(self.db)
        with self.assertRaises(ApiError) as cm:
            store.migrate()
        self.assertEqual((503, "schema_unknown"), (cm.exception.status, cm.exception.code))
        store.close()

    def test_version_mismatch_rejected(self):
        store = Store(self.db); store.migrate(); store.close()
        raw = self._raw()
        raw.execute("UPDATE schema_meta SET schema_version=3 WHERE singleton=1"); raw.close()
        store = Store(self.db)
        with self.assertRaises(ApiError) as cm:
            store.migrate()
        self.assertEqual((503, "schema_version_mismatch"), (cm.exception.status, cm.exception.code))
        store.close()

    def test_corrupted_page_is_integrity_failed(self):
        store = Store(self.db); store.migrate()
        cols = [r[1] for r in store.connection().execute("PRAGMA table_info(audit_events)")]
        for i in range(200):
            store.connection().execute(f"INSERT INTO audit_events VALUES({','.join('?' * len(cols))})", tuple([f"a{i}"] + ["x"] * (len(cols) - 1)))
        store.connection().execute("PRAGMA wal_checkpoint(TRUNCATE)")
        page_size = store.connection().execute("PRAGMA page_size").fetchone()[0]
        store.close()
        with open(self.db, "r+b") as f:
            f.seek(page_size * 3)
            f.write(b"\xde\xad\xbe\xef" * (page_size // 4))
        store2 = Store(self.db)
        with self.assertRaises(ApiError) as cm:
            store2.migrate()
        self.assertEqual((503, "schema_integrity_failed"), (cm.exception.status, cm.exception.code))
        store2.close()

    def test_repeated_migrate_is_idempotent(self):
        store = Store(self.db)
        store.migrate()
        tables1 = {r[0] for r in store.connection().execute("SELECT name FROM sqlite_master WHERE type='table'")}
        store.migrate()
        tables2 = {r[0] for r in store.connection().execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables1, tables2)
        store.close()


if __name__ == "__main__":
    unittest.main()
