"""Case ID: DP-USAGE-04

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
- finally 复位原 expires_at；无 ssh/sqlite3 权限 → skip（BLOCKED，不计 FAIL）
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess

import pytest

from tests.system.api_test_v03.constants import recent_window

M5AIR_SSH_HOST = os.environ.get("LLMTIER_M5AIR_SSH", "m5air")
M5AIR_DB = os.environ.get("LLMTIER_M5AIR_DB", "/Users/mlp/LLMTier-dev/state.sqlite3")


def _ssh_sqlite(sql: str) -> str:
    remote = f"sqlite3 {shlex.quote(M5AIR_DB)} {shlex.quote(sql)}"
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", M5AIR_SSH_HOST, remote],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ssh sqlite3 failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


@pytest.mark.api_a
def test_dp_usage_04_expired_cursor(api_client):
    if shutil.which("ssh") is None:
        pytest.skip("ssh not available for m5air sqlite3 access")

    since, until = recent_window()
    params = {"from": since, "to": until}

    first = api_client.get("/v1/usage", params=params)
    assert first.status_code == 200, f"首次查询失败: {first.status_code}: {first.text}"
    snapshot_id = first.json().get("snapshot_id")
    assert snapshot_id, f"响应缺 snapshot_id: {first.json()}"

    try:
        _ssh_sqlite("SELECT 1;")
    except Exception as exc:  # noqa: BLE001 - BLOCKED, not FAIL
        pytest.skip(f"m5air sqlite3 access unavailable: {exc}")

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
        err = resp.json().get("error") or {}
        assert err.get("code") == "cursor_expired", f"error.code != 'cursor_expired': {err}"
    finally:
        _ssh_sqlite(
            f"UPDATE query_snapshots SET expires_at='{original}' WHERE snapshot_id='{snapshot_id}';"
        )
