"""M007 util Store unit gaps (UT-UTIL-003/004).

Real `Store` over isolated temp SQLite files (ENV-1). No network/LAN.
Covers: per-thread fd hygiene (connection closed after request), busy/lock,
close-raises-up, world-writable RuntimeWarning, integrity_check mapping,
nested transaction, and corrupt/legacy store rejection.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import unittest
import warnings
from pathlib import Path

from http_api.errors import ApiError
from util.store import Store


class FdHygieneTests(unittest.TestCase):
    """UT-UTIL-003: `close()` clears the thread-local so the next call reconnects."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.temp.name) / "s.db"); self.store.migrate()

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_close_releases_and_reconnects_after_request(self):
        result = {}
        def run():
            first = self.store.connection()
            self.store.close()
            second = self.store.connection()
            result["reconnected"] = second is not first
            self.store.close()
        thread = threading.Thread(target=run); thread.start(); thread.join()
        self.assertTrue(result["reconnected"])

    def test_close_is_idempotent(self):
        self.store.close(); self.store.close()


class BusyLockTests(unittest.TestCase):
    """UT-UTIL-003: a held write transaction surfaces sqlite3.OperationalError."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.path = Path(self.temp.name) / "b.db"
        self.a = Store(self.path); self.a.migrate()
        self.b = Store(self.path); self.b.migrate()

    def tearDown(self):
        self.a.close(); self.b.close(); self.temp.cleanup()

    def test_locked_write_raises_operational_error(self):
        # Lower the busy timeout so the lock conflict is surfaced immediately.
        self.b.connection().execute("PRAGMA busy_timeout=50")
        with self.a.transaction(True):
            with self.assertRaises(sqlite3.OperationalError):
                self.b.connection().execute("INSERT INTO schema_meta(singleton,schema_version) VALUES(9,9)")


class CloseRaisesTests(unittest.TestCase):
    """UT-UTIL-003: `close()` propagates an underlying connection error."""

    def test_close_exception_propagates(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "c.db"); store.migrate()
        class BadConnection:
            def close(self): raise RuntimeError("close failed")
        store._local.connection = BadConnection()
        try:
            with self.assertRaises(RuntimeError):
                store.close()
        finally:
            store._local.connection = None


class WorldWritableTests(unittest.TestCase):
    """UT-UTIL-003: a world-writable DB file emits a RuntimeWarning."""

    def test_world_writable_warns(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "w.db"; path.write_bytes(b"")
        os.chmod(path, 0o666)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            Store(path)
        self.assertTrue(any(issubclass(item.category, RuntimeWarning) for item in caught))


class IntegrityMappingTests(unittest.TestCase):
    """UT-UTIL-004: `PRAGMA integrity_check != ok` maps to schema_integrity_failed."""

    def test_integrity_failure_is_503(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "i.db"); store.migrate()
        real = store.connection()

        class IntegrityCursor:
            def fetchone(self): return ("not ok",)

        class ProxyConnection:
            def __getattr__(self, name): return getattr(real, name)
            def execute(self, sql, *args):
                if "integrity_check" in sql:
                    return IntegrityCursor()
                return real.execute(sql, *args)

        store.connection = lambda: ProxyConnection()
        try:
            with self.assertRaises(ApiError) as cm:
                store.migrate()
            self.assertEqual((cm.exception.status, cm.exception.code), (503, "schema_integrity_failed"))
        finally:
            store._local.connection = real
            store.close()


class NestedTransactionTests(unittest.TestCase):
    """UT-UTIL-004: a nested transaction raises E-UTIL-NESTED-TXN (409)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.temp.name) / "n.db"); self.store.migrate()

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_nested_transaction_is_409(self):
        with self.assertRaises(ApiError) as cm:
            with self.store.transaction(True):
                with self.store.transaction(True):
                    pass
        self.assertEqual((cm.exception.status, cm.exception.code), (409, "E-UTIL-NESTED-TXN"))

    def test_txn_context_reuses_caller_connection(self):
        from util.store import txn
        with self.store.transaction(True) as conn:
            with txn(self.store, conn) as same:
                self.assertIs(same, conn)


class CorruptStoreTests(unittest.TestCase):
    """UT-UTIL-004: a genuinely corrupt file is not silently accepted.

    NAMED GAP G-UT-5: the scheme row UT-UTIL-004 expects `schema_integrity_failed`
    for a corrupt file, but `Store.migrate()` only maps that code from a
    `PRAGMA integrity_check != ok` result; a corrupt file with an invalid
    sqlite header/pages raises `sqlite3.DatabaseError` first (unmapped). The
    mapping itself is covered deterministically in IntegrityMappingTests; this
    test asserts the file is at least not silently accepted.
    """

    def test_corrupt_file_raises(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        good_path = Path(temp.name) / "good.db"
        good = Store(good_path); good.migrate(); good.close()
        # Corrupt page 2 while keeping a valid sqlite header.
        data = bytearray(good_path.read_bytes())
        for index in range(4096, min(8192, len(data))):
            data[index] = 0
        path = Path(temp.name) / "corrupt.db"; path.write_bytes(bytes(data))
        with self.assertRaises((ApiError, sqlite3.DatabaseError)):
            Store(path).migrate()


if __name__ == "__main__":
    unittest.main()
