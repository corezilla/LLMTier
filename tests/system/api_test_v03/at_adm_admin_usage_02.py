"""Case ID: ST-AUSAGE-002

Endpoint: GET /v1/usage?limit=1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200
- data.length ≤ 1（下界边界；空表 0 亦合法）
- 五键齐全 {data,next_cursor,has_more,snapshot_id,snapshot_at}；has_more 为 bool
- 一致性：has_more is True ⇒ next_cursor 非空且前缀 == snapshot_id（cursor 绑定本次快照）；
           has_more is False ⇒ next_cursor is None
- 对照：默认 limit=100 返回条数 ≥ limit=1 的返回条数（排除"忽略 limit 恒返回固定数"）

注：本 case 会写临时 query_snapshots（读副作用，doc §2/§6 已声明）。
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.constants import recent_window

USAGE_PAGE_KEYS = {"data", "next_cursor", "has_more", "snapshot_id", "snapshot_at"}


@pytest.mark.api_a
def test_adm_admin_usage_02_pagination(admin_client):
    since, until = recent_window()
    resp = admin_client.get(
        "/v1/usage",
        params={"from": since, "to": until, "limit": 1},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == USAGE_PAGE_KEYS, (
        f"UsagePage 键集不符: {set(body)} != {USAGE_PAGE_KEYS}")
    data = body["data"]
    assert isinstance(data, list), f"data 非数组: {type(data)}"
    assert len(data) <= 1, f"data.length > 1 但 limit=1: {body}"
    assert isinstance(body["has_more"], bool), f"has_more 非 bool: {body['has_more']!r}"

    if body["has_more"] is True:
        cursor = body["next_cursor"]
        assert isinstance(cursor, str) and cursor, (
            f"has_more=true 但 next_cursor 非非空字符串: {cursor!r}")
        assert cursor.split(":", 1)[0] == body["snapshot_id"], (
            f"next_cursor 前缀未绑定本次 snapshot_id: {cursor!r} vs {body['snapshot_id']!r}")
    else:
        assert body["next_cursor"] is None, (
            f"has_more=false 但 next_cursor 非 null: {body['next_cursor']!r}")

    # 对照：默认 limit=100 返回条数不应小于 limit=1 的返回条数。
    control = admin_client.get("/v1/usage", params={"from": since, "to": until})
    assert control.status_code == 200, f"默认 limit 对照失败: {control.text}"
    control_len = len(control.json().get("data", []))
    assert control_len >= len(data), (
        f"默认 100 返回 {control_len} 条 < limit=1 的 {len(data)} 条")
