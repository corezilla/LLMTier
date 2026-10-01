"""Case ID: ST-USAGE-001

Endpoint: GET /v1/usage
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言（对齐 OpenAPI UsagePage/UsageRecord, additionalProperties:false）：
- HTTP 200；content-type application/json（非错误信封）
- 顶层键集恰为 {data,next_cursor,has_more,snapshot_id,snapshot_at}
- has_more 为 bool；has_more=false ⇒ next_cursor is null；snapshot_id 非空字符串；
  snapshot_at 为合法 RFC3339（key 存在且有值，不空 null）
- data 每条满足 UsageRecord（键集/枚举/时间戳）；unknown ⇒ token 全 null（非 0）
- 每条 recorded_at ∈ [from,to)（半开区间）
"""
from __future__ import annotations

import pytest

from tests.system.constants import (
    USAGE_PAGE_KEYS,
    assert_usage_record,
    parse_ts,
    recent_window,
)


@pytest.mark.api_a
def test_dp_usage_01_queryable(api_client):
    since, until = recent_window()
    resp = api_client.get("/v1/usage", params={"from": since, "to": until})
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "error" not in body, f"成功响应不应含 error: {body}"

    assert set(body) == USAGE_PAGE_KEYS, f"顶层键集不符: {sorted(body)}"
    data = body["data"]
    assert isinstance(data, list), "data 非数组"
    has_more = body["has_more"]
    next_cursor = body["next_cursor"]
    assert isinstance(has_more, bool), f"has_more 非 bool: {has_more!r}"
    if has_more is False:
        assert next_cursor is None, f"has_more=false 但 next_cursor={next_cursor!r}"
    else:
        assert isinstance(next_cursor, str) and next_cursor, (
            f"has_more=true ⇒ next_cursor 非空字符串: {next_cursor!r}"
        )

    snapshot_id = body["snapshot_id"]
    assert isinstance(snapshot_id, str) and snapshot_id, f"snapshot_id 非非空字符串: {snapshot_id!r}"
    snapshot_at = body["snapshot_at"]
    assert isinstance(snapshot_at, str) and snapshot_at, f"snapshot_at 非非空字符串: {snapshot_at!r}"
    parse_ts(snapshot_at)

    lo, hi = parse_ts(since), parse_ts(until)
    for i, record in enumerate(data):
        assert_usage_record(record, where=f"data[{i}]")
        ts = parse_ts(record["recorded_at"])
        assert lo <= ts < hi, (
            f"data[{i}].recorded_at={record['recorded_at']} 越界 [from,to)=[{since},{until})"
        )
