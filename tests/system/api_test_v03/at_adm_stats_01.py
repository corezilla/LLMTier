"""Case ID: ST-stats-001

Endpoint: GET /v1/stats?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200，Content-Type 含 application/json
- body 键集恰 {from,to,group_by,data}；from==请求 from、to==请求 to（回显）、
  group_by=="tier"（默认）、data 为数组
- 每个 data 元素键集恰为 10 键 {tier,calls,measured_calls,unknown_calls,
  input_tokens,output_tokens,total_tokens,cached_tokens,cache_write_tokens,
  reasoning_tokens}，且 calls 为 int

半开窗 `[from,to)`：本 case 不断言具体数值；判别性边界见 ST-ausage-003 的
精确 `to` 排除用例。
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.constants import recent_window

TIER_ROW_KEYS = {
    "tier", "calls", "measured_calls", "unknown_calls",
    "input_tokens", "output_tokens", "total_tokens",
    "cached_tokens", "cache_write_tokens", "reasoning_tokens",
}


@pytest.mark.api_a
def test_adm_stats_01_basic(admin_client):
    since, until = recent_window()
    resp = admin_client.get("/v1/stats", params={"from": since, "to": until})
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert "application/json" in resp.headers.get("Content-Type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('Content-Type')!r}")

    body = resp.json()
    assert set(body) == {"from", "to", "group_by", "data"}, (
        f"stats 键集不符: {set(body)}")
    assert body["from"] == since, f"from 回显错: {body['from']!r} != {since!r}"
    assert body["to"] == until, f"to 回显错: {body['to']!r} != {until!r}"
    assert body["group_by"] == "tier", f"默认 group_by != 'tier': {body['group_by']!r}"
    assert isinstance(body["data"], list), f"data 非数组: {type(body['data'])}"

    for row in body["data"]:
        assert set(row) == TIER_ROW_KEYS, (
            f"tier 行键集不符: {set(row)} != {TIER_ROW_KEYS}")
        assert isinstance(row["calls"], int), f"calls 非 int: {row['calls']!r}"
