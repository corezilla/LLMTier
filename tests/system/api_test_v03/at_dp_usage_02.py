"""Case ID: DP-USAGE-02

Endpoint: GET /tier/v1/usage（生成过 usage 之后）
Upstream Provider: 取决于前置响应
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 200
- body.data.length ≥ 1（m5air 上跑过 DP-EMB-01/02/03 必留下记录）

注：依赖 m5air 上有 usage 数据。不显式前置（避免和 DP-RESP-02 耦合）。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_usage_02_has_records(api_client):
    resp = api_client.get(
        "/tier/v1/usage",
        params={"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert len(body.get("data", [])) >= 1, f"data 为空（m5air 应有历史 usage）: {body}"
    item = body["data"][0]
    for field in ("request_id", "model", "endpoint", "recorded_at"):
        assert field in item, f"缺字段 {field}: {item}"
