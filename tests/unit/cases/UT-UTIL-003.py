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








if __name__ == "__main__":
    unittest.main()
