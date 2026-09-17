from __future__ import annotations

import contextlib
import sqlite3
import threading
from pathlib import Path
from typing import Iterator, Sequence


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()

    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.connection = conn
        return conn

    def migrate(self) -> None:
        sql = Path(__file__).with_name("migrations").joinpath("001_initial.sql").read_text()
        self.connection().executescript(sql)
        result = self.connection().execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"sqlite_integrity_check_failed:{result}")

    @contextlib.contextmanager
    def transaction(self, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        conn = self.connection()
        conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    def one(self, sql: str, params: Sequence[object] = ()) -> sqlite3.Row | None:
        return self.connection().execute(sql, params).fetchone()

    def all(self, sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]:
        return list(self.connection().execute(sql, params).fetchall())

    def close(self) -> None:
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            conn.close()
            self._local.connection = None
