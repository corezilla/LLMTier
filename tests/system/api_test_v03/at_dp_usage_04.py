"""Case ID: ST-USAGE-004

Endpoint: GET /v1/usage (cursor replay)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 400
- error.code == "cursor_expired"

实现（design 决策：真造 expired cursor，不用 cursor="expired" 字面值）：
- A 类：GET /v1/usage 生成 snapshot（记录 snapshot_id）
- 直连 m5air `state.sqlite3`（ssh + sqlite3），记录原 expires_at 并 UPDATE 到过去
- 用同一 filter 的 cursor=<snapshot_id>:0 重放 → 400 cursor_expired
- finally 复位原 expires_at
- 无 ssh/sqlite3 权限 → `pytest.xfail` 记为 BLOCKED（可重试），不计 FAIL/SKIP
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time

import pytest

from tests.system.api_test_v03.constants import recent_window

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}
M5AIR_SSH_HOST = os.environ.get("LLMTIER_M5AIR_SSH", "m5air")
M5AIR_DB = os.environ.get("LLMTIER_M5AIR_DB", "/Users/mlp/LLMTier-dev/state.sqlite3")

# The live service holds WAL write locks on the shared DB while it serves
# traffic, so a `sqlite3` CLI call (default busy_timeout=0) can transiently hit
# `database is locked`. Retry with a bounded backoff and set the busy timeout
# inside sqlite3 itself so the lock wait happens in-process, not by busy-looping
# ssh. This is the test-side fix for the 503/`database is locked` shared-instance
# contention flake; no production code changes.
_SSH_SQLITE_RETRIES = 5
_SSH_SQLITE_BACKOFF_S = 0.5


def _ssh_sqlite_once(sql: str) -> subprocess.CompletedProcess:
    # `.timeout` (dot-command) sets the busy timeout without printing a value,
    # unlike `PRAGMA busy_timeout=...` which echoes the new timeout to stdout and
    # would corrupt the captured result. It makes sqlite3 wait for the live
    # writer instead of failing immediately with SQLITE_BUSY.
    remote = (
        f"sqlite3 -cmd {shlex.quote('.timeout 15000')} "
        f"{shlex.quote(M5AIR_DB)} {shlex.quote(sql)}"
    )
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", M5AIR_SSH_HOST, remote],
        capture_output=True, text=True, timeout=30,
    )


def _ssh_sqlite(sql: str) -> str:
    last = ""
    for attempt in range(_SSH_SQLITE_RETRIES):
        result = _ssh_sqlite_once(sql)
        if result.returncode == 0:
            return result.stdout.strip()
        last = result.stderr.strip()[:200]
        # Only the transient lock is retryable; anything else is a real error.
        if "locked" not in last and "busy" not in last:
            raise RuntimeError(f"ssh sqlite3 failed: {last}")
        time.sleep(_SSH_SQLITE_BACKOFF_S * (attempt + 1))
    raise RuntimeError(f"ssh sqlite3 failed after {_SSH_SQLITE_RETRIES} attempts: {last}")


@pytest.mark.api_a
def test_dp_usage_04_expired_cursor(api_client):
    if shutil.which("ssh") is None:
        pytest.xfail("BLOCKED (ST-USAGE-004): ssh not available for m5air sqlite3 access")

    since, until = recent_window()
    params = {"from": since, "to": until}

    first = api_client.get("/v1/usage", params=params)
    assert first.status_code == 200, f"首次查询失败: {first.status_code}: {first.text}"
    snapshot_id = first.json().get("snapshot_id")
    assert snapshot_id, f"响应缺 snapshot_id: {first.json()}"

    try:
        _ssh_sqlite("SELECT 1;")
    except Exception as exc:  # noqa: BLE001 - BLOCKED (xfail), not FAIL
        pytest.xfail(f"BLOCKED (ST-USAGE-004): m5air sqlite3 access unavailable: {exc}")

    original = _ssh_sqlite(
        f"SELECT expires_at FROM query_snapshots WHERE snapshot_id='{snapshot_id}';"
    )
    assert original, f"snapshot {snapshot_id} 不存在于 m5air DB"

    try:
        _ssh_sqlite(
            "UPDATE query_snapshots SET expires_at='2000-01-01T00:00:00.000Z' "
            f"WHERE snapshot_id='{snapshot_id}';"
        )
        resp = api_client.get("/v1/usage", params={**params, "cursor": f"{snapshot_id}:0"})
        assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
        body = resp.json()
        assert set(body) == {"error"}, f"错误信封顶层键集不符: {sorted(body)}"
        err = body["error"]
        assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
        assert err["code"] == "cursor_expired", f"error.code != 'cursor_expired': {err}"
        assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
        assert err["param"] is None, f"error.param 非 null: {err}"
        assert err["retryable"] is False, f"error.retryable 非 False: {err}"
    finally:
        _ssh_sqlite(
            f"UPDATE query_snapshots SET expires_at='{original}' WHERE snapshot_id='{snapshot_id}';"
        )
        # Cleanup integrity (doc §4 step6): the restore must be read back and
        # byte-identical to the original — a silent 0-row UPDATE would leave the
        # live snapshot expired and go undetected.
        restored = _ssh_sqlite(
            f"SELECT expires_at FROM query_snapshots WHERE snapshot_id='{snapshot_id}';"
        )
        assert restored == original, (
            f"快照 expires_at 复位失败: original={original!r} restored={restored!r}"
        )
