from __future__ import annotations

import threading
from typing import Any

_SQLITE_OPERATION_LOCK = threading.RLock()


# 用途：
# - 为进程内所有 SQLite 调用提供唯一绑定入口，避免同时加载 stdlib sqlite3 与 pysqlite3
# 输入：
# - 无；优先使用支持 sqlite-vec 的 pysqlite3，缺失时回退标准库 sqlite3
# 输出：
# - sqlite3-compatible module object
def load_sqlite_module() -> Any:
    try:
        import pysqlite3 as sqlite3
    except ImportError:  # pragma: no cover - only exercised on incomplete local environments
        import sqlite3  # type: ignore[no-redef]
    return sqlite3


# 用途：
# - 提供进程级 SQLite 操作锁，避免多线程同时 open/close SQLite 连接时卡住解释器
# 输入：
# - 无
# 输出：
# - 可重入锁对象，调用方用 `with sqlite_operation_lock():` 包裹 SQLite 操作
def sqlite_operation_lock() -> threading.RLock:
    return _SQLITE_OPERATION_LOCK
