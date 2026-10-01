"""Case ID: ST-AUSAGE-001

Endpoint: GET /v1/usage?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200，Content-Type 含 application/json
- body 键集恰 {data,next_cursor,has_more,snapshot_id,snapshot_at}
- data 为数组；has_more 为 bool；snapshot_id 非空 str；snapshot_at 为 RFC3339 str
- 一致性：has_more is False ⇒ next_cursor is None；
           has_more is True ⇒ next_cursor 非空且前缀 == snapshot_id（cursor 绑定本次快照）
- 每个 data 元素键集恰为 UsageRecord 的 15 键

注：无 cursor 的读会写一条 kind=usage 的 query_snapshots（10 min TTL）——读副作用，
本 case 不断言其清理（doc §2/§6 已声明）。
"""
from __future__ import annotations

import re

import pytest

from tests.system.api_test_v03.constants import recent_window

USAGE_PAGE_KEYS = {"data", "next_cursor", "has_more", "snapshot_id", "snapshot_at"}
USAGE_RECORD_KEYS = {
    "request_id", "record_version", "is_final", "model", "endpoint",
    "recorded_at", "updated_at", "measurement_status", "source",
    "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens",
    "cache_write_tokens", "reasoning_tokens",
}
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


@pytest.mark.api_a
def test_adm_admin_usage_01(admin_client):
    since, until = recent_window()
    resp = admin_client.get("/v1/usage", params={"from": since, "to": until})
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert "application/json" in resp.headers.get("Content-Type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('Content-Type')!r}")

    body = resp.json()
    assert set(body) == USAGE_PAGE_KEYS, (
        f"UsagePage 键集不符: {set(body)} != {USAGE_PAGE_KEYS}")
    assert isinstance(body["data"], list), f"data 非数组: {type(body['data'])}"
    assert isinstance(body["has_more"], bool), f"has_more 非 bool: {body['has_more']!r}"
    assert isinstance(body["snapshot_id"], str) and body["snapshot_id"], (
        f"snapshot_id 非非空字符串: {body['snapshot_id']!r}")
    assert isinstance(body["snapshot_at"], str) and _RFC3339.match(body["snapshot_at"]), (
        f"snapshot_at 非 RFC3339 字符串: {body['snapshot_at']!r}")

    if body["has_more"] is False:
        assert body["next_cursor"] is None, (
            f"has_more=false 但 next_cursor 非 null: {body['next_cursor']!r}")
    else:
        cursor = body["next_cursor"]
        assert isinstance(cursor, str) and cursor, (
            f"has_more=true 但 next_cursor 非非空字符串: {cursor!r}")
        assert cursor.split(":", 1)[0] == body["snapshot_id"], (
            f"next_cursor 前缀未绑定本次 snapshot_id: {cursor!r} vs {body['snapshot_id']!r}")

    for row in body["data"]:
        assert set(row) == USAGE_RECORD_KEYS, (
            f"UsageRecord 键集不符: {set(row)} != {USAGE_RECORD_KEYS}")
