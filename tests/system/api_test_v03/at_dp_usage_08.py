"""Case ID: DP-USAGE-08

Endpoint: GET /v1/usage (store 不可用)
Upstream Provider: provider_endpoint_b（LAN fake provider，TS-003）
Model: 无
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 本 case 专用临时 LLMTier 实例（llmtier_b_diag_store，独立临时
            SQLite/端口，function-scope）
  上游: provider_endpoint_b（LAN fake provider，TS-003）
  fixture: llmtier_b_diag_store + store_triplet

目标（VRC-MGMT-006 / R-MET-04 / CON-METER-005 / ERR-STORE）：Usage store
不可用时返回 typed 503 usage_store_unavailable，**不得**以 200+空 data 冒充
"无记录"；恢复存储后查询回到 200。

断言：
- 基线：GET /v1/usage → 200 UsagePage
- 破坏 store 后：503 + code=="usage_store_unavailable" + type=="server_error"
- 响应为错误信封（顶层无 data/has_more/snapshot_id，有 error）
- finally：恢复后同一查询 → 200 UsagePage
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.system.api_test_v03 import conftest as _conftest


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


@pytest.mark.api_b
def test_dp_usage_08_store_unavailable_not_empty_page(llmtier_b_diag_store):
    inst = llmtier_b_diag_store
    client = inst.api_client()
    now = datetime.now(timezone.utc)
    since, until = _iso(now - timedelta(days=30)), _iso(now)
    params = {"from": since, "to": until}

    breaker = _conftest.StoreTriplet(inst.db_path)
    try:
        baseline = client.get("/v1/usage", params=params)
        assert baseline.status_code == 200, (
            f"基线查询期望 200，实际 {baseline.status_code}: {baseline.text}")
        assert "data" in baseline.json(), "基线不是 UsagePage"

        breaker.break_store()
        resp = client.get("/v1/usage", params=params)
        assert resp.status_code == 503, (
            f"store 不可用期望 503，实际 {resp.status_code}: {resp.text}")
        body = resp.json()
        assert "error" in body, f"响应缺 error 信封: {body}"
        for key in ("data", "has_more", "snapshot_id"):
            assert key not in body, f"503 不得返回 UsagePage 字段 {key!r}: {body}"
        err = body["error"]
        assert err.get("code") == "usage_store_unavailable", (
            f"code != usage_store_unavailable: {err}")
        assert err.get("type") == "server_error", f"type != server_error: {err}"
    finally:
        breaker.restore()

    recovered = client.get("/v1/usage", params=params)
    assert recovered.status_code == 200, (
        f"恢复后期望 200，实际 {recovered.status_code}: {recovered.text}")
    assert "data" in recovered.json(), "恢复后不是 UsagePage"
