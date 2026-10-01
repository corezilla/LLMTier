"""Case ID: ST-STATS-002

Endpoint: GET /v1/stats?from=...&to=...&group_by=tier
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200
- body.group_by == "tier"（回显）
- data 为数组；每个元素为 **tier 行形状**：含 `tier` 键，且**不含** deployment
  分支的键（deployment_id/deployment_name/backend_model/provider_id/provider_name/
  provider_kind）——锁定显式 tier 分支，避免"实现忽略 group_by 仍回显 tier"漏测。

空窗（data==[]）合法，只断形状/回显。
"""
from __future__ import annotations

import pytest

from tests.system.constants import recent_window

TIER_ROW_KEYS = {
    "tier", "calls", "measured_calls", "unknown_calls",
    "input_tokens", "output_tokens", "total_tokens",
    "cached_tokens", "cache_write_tokens", "reasoning_tokens",
}
DEPLOYMENT_ROW_KEYS = {
    "deployment_id", "deployment_name", "backend_model",
    "provider_id", "provider_name", "provider_kind",
}


@pytest.mark.api_a
def test_adm_stats_02_group_by_tier(admin_client):
    since, until = recent_window()
    resp = admin_client.get(
        "/v1/stats",
        params={"from": since, "to": until, "group_by": "tier"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("group_by") == "tier", f"group_by != 'tier': {body}"
    assert isinstance(body.get("data"), list), f"data 非数组: {type(body.get('data'))}"

    for row in body["data"]:
        assert isinstance(row, dict), f"tier 行非对象: {row}"
        assert set(row) == TIER_ROW_KEYS, (
            f"tier 行键集不符（须为 tier 分支形状）: {set(row)} != {TIER_ROW_KEYS}")
        assert "tier" in row, f"tier 行缺 tier 键: {row}"
        stray = DEPLOYMENT_ROW_KEYS & set(row)
        assert not stray, f"tier 行混入 deployment 分支键: {stray}"
        assert isinstance(row["calls"], int), f"calls 非 int: {row['calls']!r}"
