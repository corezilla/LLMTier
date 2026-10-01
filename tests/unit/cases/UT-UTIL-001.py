from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from util.store import EXPECTED_SCHEMA_VERSION, Store


class StoreTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.store=Store(Path(self.tmp.name)/"s.db"); self.store.migrate()
    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def test_migration_creates_schema(self): self.assertGreaterEqual(len(self.store.all("SELECT name FROM sqlite_master WHERE type='table'")), 14)
    def test_integrity_is_ok(self): self.assertEqual(self.store.one("PRAGMA integrity_check")[0], "ok")
    def test_foreign_keys_enabled(self): self.assertEqual(self.store.one("PRAGMA foreign_keys")[0], 1)
    def test_wal_enabled(self): self.assertEqual(self.store.one("PRAGMA journal_mode")[0].lower(), "wal")
    def test_transaction_commits(self):
        with self.store.transaction() as c: c.execute("UPDATE schema_meta SET bootstrap_sha256='x'")
        self.assertEqual(self.store.one("SELECT bootstrap_sha256 FROM schema_meta")[0], "x")
    def test_thread_gets_connection(self):
        found=[]
        def run(): found.append(self.store.one("SELECT schema_version FROM schema_meta")[0]); self.store.close()
        t=threading.Thread(target=run); t.start(); t.join(); self.assertEqual(found,[EXPECTED_SCHEMA_VERSION])


"""Unit tests for M007 Store schema gating and path safety (VRC-UTIL-001/002).

Dependencies: none — each test uses an isolated temp SQLite file.
See docs/50_implementation_design/util.isd.md §5.1.1/§5.1.4/§7.2.3.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from http_api.errors import ApiError
from util.store import EXPECTED_SCHEMA_VERSION, Store


class StoreSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.sqlite3"

    def tearDown(self):
        self.temp.cleanup()





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
