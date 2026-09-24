"""Unit tests for M007 Store schema gating and path safety (VRC-UTIL-001/002).

Dependencies: none — each test uses an isolated temp SQLite file.
See docs/50_implementation_design/util.isd.md §5.1.1/§5.1.4/§7.2.3.
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from llmtier_v03.errors import ApiError
from llmtier_v03.store import Store


class StoreSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_init_sets_expected_version_and_rerun_is_safe(self):
        store = Store(self.path)
        store.migrate()
        self.assertEqual(store.one("SELECT schema_version FROM schema_meta WHERE singleton=1")[0], 1)
        store.migrate()
        store.close()

    def test_persistence_across_reopen(self):
        Store(self.path).migrate()
        reopened = Store(self.path)
        reopened.migrate()
        self.assertGreater(len(reopened.all("SELECT name FROM sqlite_master WHERE type='table'")), 1)
        reopened.close()

    def test_version_mismatch_rejected(self):
        store = Store(self.path)
        store.migrate()
        store.connection().execute("UPDATE schema_meta SET schema_version=99 WHERE singleton=1")
        with self.assertRaises(ApiError) as ctx:
            store.migrate()
        self.assertEqual((ctx.exception.status, ctx.exception.code), (503, "schema_version_mismatch"))
        store.close()

    def test_legacy_store_without_schema_meta_rejected(self):
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE providers(id TEXT)")
        conn.commit()
        conn.close()
        with self.assertRaises(ApiError) as ctx:
            Store(self.path).migrate()
        self.assertEqual(ctx.exception.code, "schema_unknown")

    def test_symlink_path_rejected(self):
        target = Path(self.temp.name) / "real.sqlite3"
        target.write_bytes(b"")
        link = Path(self.temp.name) / "link.sqlite3"
        link.symlink_to(target)
        with self.assertRaises(ApiError) as ctx:
            Store(link)
        self.assertEqual(ctx.exception.code, "store_path_unsafe")


if __name__ == "__main__":
    unittest.main()
