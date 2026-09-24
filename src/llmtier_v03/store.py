from __future__ import annotations

import contextlib
import os
import sqlite3
import stat as stat_module
import threading
import warnings
from pathlib import Path
from typing import Iterator, Sequence

from .errors import ApiError

EXPECTED_SCHEMA_VERSION = 1


def _statements(sql: str) -> list[str]:
    out: list[str] = []
    for chunk in sql.split(";"):
        stmt = "\n".join(
            line for line in chunk.splitlines() if not line.strip().startswith("--")
        ).strip()
        if stmt:
            out.append(stmt)
    return out


@contextlib.contextmanager
def txn(store: "Store", conn: sqlite3.Connection | None = None) -> Iterator[sqlite3.Connection]:
    """Yield an existing connection (caller owns the transaction) or open a new one.

    Implements the ISD nested-transaction policy: callers already inside a
    transaction pass their Connection instead of opening a second one.
    """
    if conn is not None:
        yield conn
    else:
        with store.transaction(True) as nested:
            yield nested


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._local = threading.local()
        self._precheck()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def _precheck(self) -> None:
        # FUNC-UTIL-INIT / LSS-UTIL-DB: reject symlinked DB path, warn on world-writable.
        try:
            st = os.lstat(self.path)
        except FileNotFoundError:
            return
        if stat_module.S_ISLNK(st.st_mode):
            raise ApiError(503, "store_path_unsafe", "Database path must not be a symlink")
        if st.st_mode & 0o002:
            warnings.warn(f"database file is world-writable: {self.path}", RuntimeWarning, stacklevel=2)

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
        conn = self.connection()
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        user_tables = {t for t in tables if not t.startswith("sqlite_") and t != "schema_meta"}
        if "schema_meta" not in tables:
            if user_tables:
                # E-UTIL-SCHEMA-UNKNOWN: existing store without the version table.
                raise ApiError(503, "schema_unknown", "Existing database has no schema_meta table")
            self._initialize(conn)
        else:
            row = conn.execute(
                "SELECT schema_version FROM schema_meta WHERE singleton=1"
            ).fetchone()
            version = row[0] if row is not None else None
            if version != EXPECTED_SCHEMA_VERSION:
                # E-UTIL-SCHEMA-VERSION: init-only; no upgrade / downgrade / auto-repair.
                raise ApiError(
                    503,
                    "schema_version_mismatch",
                    f"schema_version {version!r} != expected {EXPECTED_SCHEMA_VERSION}",
                )
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            # E-UTIL-SCHEMA-INTEGRITY
            raise ApiError(503, "schema_integrity_failed", f"sqlite integrity_check failed: {result}")

    def _initialize(self, conn: sqlite3.Connection) -> None:
        # Atomic init: single transaction, statement-by-statement (no executescript).
        migrations = Path(__file__).with_name("migrations")
        statements: list[str] = []
        for sql_file in sorted(migrations.glob("*.sql")):
            statements.extend(_statements(sql_file.read_text()))
        conn.execute("BEGIN IMMEDIATE")
        try:
            for statement in statements:
                conn.execute(statement)
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

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
