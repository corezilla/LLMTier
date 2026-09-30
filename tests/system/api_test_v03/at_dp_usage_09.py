"""Case ID: DP-USAGE-09

Endpoint: POST /v1/responses（触发义务）; GET /v1/usage（观察）
Upstream Provider: orig（path B: LAN fake provider via depl_b blackend_model + SlowAdapter）
Model: Senior（指向 depl_b）
Auth: 触发 Bearer dev-data；查询 Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b_crash，独立临时 SQLite/端口）；
            llmtier_b_restart 用于路径 A
  上游: LAN fake provider（provider_endpoint_b）——路径 B 由 SlowAdapter 占住 up-stream
  模型: Senior（service level，指向 depl_b）
  环境: LLMTIER_SLOW_ADAPTER_DELAY=30（路径 B）

目标（T-MET-CRASH）：账本核心不变量 `authorize_dispatch` 在 dispatch 前提交
*义务 + v1 unknown + head=1*（单事务）；此后进程**真实崩溃**（SIGKILL）后重启，
该 orphan unknown 仍在、**不重复**且绝不回填为 0。

两条路径（互补证明不变量两半）：
- 路径 A（准入失败法）：depl_b 未 probe → Router.admit 503，admitted=False ⇒ 无 finish；
  查询仍在且 unknown + token NULL（不丢失 half）。
- 路径 B（真实崩溃法）：depl_b healthy + SlowAdapter sleep；请求在 in-flight 时
  SIGKILL（非 graceful SIGTERM）；重启后查询仍在该 request_id，且**唯一**：
  直接读账本表证明 obligation/head/version 各恰 1 行（不重复 half）。
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

RESPONSES_BODY = {
    "model": "Senior",
    "input": [{"role": "user", "content": "hi"}],
    "stream": True,
    "store": False,
}


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _count(db_path, table: str, request_id: str) -> int:
    """Read the ledger tables directly (path B uniqueness evidence)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE request_id=?", (request_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def _wait_for_obligation(db_path, timeout: float = 15.0) -> str:
    """Poll the ledger until exactly one obligation appears; return its id.

    The in-flight request never returns its X-Request-ID (the client is killed
    with the process), so the committed obligation row is the authoritative
    source of the request id.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                rows = conn.execute("SELECT request_id FROM usage_obligations").fetchall()
            finally:
                conn.close()
            if rows:
                assert len(rows) == 1, f"fresh instance 应恰 1 条 obligation: {rows}"
                return rows[0][0]
        except sqlite3.Error:
            pass
        time.sleep(0.1)
    raise AssertionError("15s 内未观察到已提交的 usage obligation（路径 B 未进入 in-flight）")


@pytest.mark.api_b
def test_dp_usage_09_orphan_unknown_survives_real_crash(llmtier_b_crash):
    inst = llmtier_b_crash
    t0 = datetime.now(timezone.utc) - timedelta(minutes=5)
    api = api_client = inst.api_client()
    admin = inst.admin_client()

    # Step 1: fire the request on a background thread and let it block in
    # SlowAdapter.complete() AFTER authorize_dispatch committed the obligation.
    result: dict = {}

    def _fire():
        try:
            result["resp"] = api.post("/v1/responses", json=RESPONSES_BODY)
        except Exception as exc:  # process is SIGKILLed mid-flight
            result["error"] = exc

    thread = threading.Thread(target=_fire, daemon=True)
    thread.start()
    request_id = _wait_for_obligation(inst.db_path)

    # Step 2: REAL ungraceful kill (SIGKILL) with the obligation in-flight.
    inst.kill()
    thread.join(timeout=5)

    # Step 3: restart on the SAME db/settings.
    inst._spawn()
    inst.start()
    t1 = datetime.now(timezone.utc) + timedelta(minutes=5)
    health = admin.get("/healthz")
    assert health.status_code == 200, f"重启后 /healthz != 200: {health.status_code}"

    # Step 4: no-loss half — the orphan survived and is unknown (never 0).
    page = admin.get(
        "/v1/usage",
        params={"from": _iso(t0), "to": _iso(t1), "request_id": request_id},
    )
    assert page.status_code == 200, f"重启后 GET /v1/usage 期望 200: {page.status_code}: {page.text}"
    data = page.json()["data"]
    records = [r for r in data if r["request_id"] == request_id]
    assert records, f"重启后 orphan 记录丢失：request_id={request_id} 不在页中: {data}"
    assert len(records) == 1, f"重启后同 request_id 出现多条记录（重复 obligation）: {records}"
    record = records[0]
    assert record["measurement_status"] == "unknown", f"measurement_status 不符: {record}"
    assert record["source"] == "unavailable", f"source 不符: {record}"
    assert record["input_tokens"] is None, f"input_tokens 必须为 None（非 0）: {record}"
    assert record["output_tokens"] is None, f"output_tokens 必须为 None（非 0）: {record}"
    assert record["total_tokens"] is None, f"total_tokens 必须为 None（非 0）: {record}"
    assert record["is_final"] is False, f"is_final 必须 False: {record}"
    assert record["record_version"] == 1, f"record_version 必须 1: {record}"

    # Step 5: no-duplication half — read the ledger tables directly. The `_page`
    # projection JOINs `usage_heads`, so a duplicate obligation/head/version would
    # be structurally invisible through the API; query the raw tables.
    assert _count(inst.db_path, "usage_obligations", request_id) == 1, "重复 obligation"
    assert _count(inst.db_path, "usage_heads", request_id) == 1, "重复 head"
    assert _count(inst.db_path, "usage_record_versions", request_id) == 1, "多余 record version"

    api.close()
    admin.close()


@pytest.mark.api_b
def test_dp_usage_09_orphan_unknown_survives_restart(llmtier_b_restart):
    """Path A control: graceful restart after an admission-rejected obligation.

    Proves the same no-loss / unknown≠0 invariant on the committed-before-
    dispatch path, and asserts the record is unique.
    """
    inst = llmtier_b_restart
    t0 = datetime.now(timezone.utc) - timedelta(minutes=5)
    api = inst.api_client()
    admin = inst.admin_client()
    try:
        resp = api.post("/v1/responses", json=RESPONSES_BODY)
        assert resp.status_code == 503, (
            f"期望准入失败 503，实际 {resp.status_code}: {resp.text}"
        )
        request_id = resp.headers.get("X-Request-ID")
        assert request_id, "触发响应缺少 X-Request-ID"

        t1 = datetime.now(timezone.utc) + timedelta(minutes=5)
        inst.restart()
        health = admin.get("/healthz")
        assert health.status_code == 200, f"重启后 /healthz != 200: {health.status_code}"

        page = admin.get(
            "/v1/usage",
            params={"from": _iso(t0), "to": _iso(t1), "request_id": request_id},
        )
        assert page.status_code == 200, f"重启后 GET /v1/usage 期望 200: {page.status_code}: {page.text}"
        data = page.json()["data"]
        records = [r for r in data if r["request_id"] == request_id]
        assert records, (
            f"重启后 orphan 记录丢失：request_id={request_id} 不在页中: {data}"
        )
        assert len(records) == 1, f"重启后同 request_id 出现多条记录: {records}"
        record = records[0]
        assert record["measurement_status"] == "unknown", f"measurement_status 不符: {record}"
        assert record["source"] == "unavailable", f"source 不符: {record}"
        assert record["input_tokens"] is None, f"input_tokens 必须为 None（非 0）: {record}"
        assert record["output_tokens"] is None, f"output_tokens 必须为 None（非 0）: {record}"
        assert record["total_tokens"] is None, f"total_tokens 必须为 None（非 0）: {record}"
        assert record["is_final"] is False, f"is_final 必须 False: {record}"
        assert record["record_version"] == 1, f"record_version 必须 1: {record}"

        assert _count(inst.db_path, "usage_obligations", request_id) == 1, "重复 obligation"
        assert _count(inst.db_path, "usage_heads", request_id) == 1, "重复 head"
        assert _count(inst.db_path, "usage_record_versions", request_id) == 1, "多余 record version"
    finally:
        api.close()
        admin.close()
