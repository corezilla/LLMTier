import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from llmtier_v03.store import Store


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
    def test_transaction_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with self.store.transaction() as c: c.execute("UPDATE schema_meta SET bootstrap_sha256='x'"); raise RuntimeError()
        self.assertIsNone(self.store.one("SELECT bootstrap_sha256 FROM schema_meta")[0])
    def test_migration_is_idempotent(self): self.store.migrate(); self.assertEqual(self.store.one("SELECT count(*) FROM schema_meta")[0], 1)
    def test_thread_gets_connection(self):
        found=[]
        def run(): found.append(self.store.one("SELECT schema_version FROM schema_meta")[0]); self.store.close()
        t=threading.Thread(target=run); t.start(); t.join(); self.assertEqual(found,[1])
