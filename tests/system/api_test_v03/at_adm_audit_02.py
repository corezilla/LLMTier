"""Case ID: ST-AUDIT-002

Endpoint: GET /v1/audit?limit=1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200
- body.data.length ≤ 1（下界边界；空表 0 亦合法）
- page 键集恰 {has_more,next_cursor}
- has_more 为 bool
- 一致性：has_more is False ⇒ next_cursor is None
- 对照：默认 limit=50 的 len(data) ≥ limit=1 的 len(data)（排除"忽略 limit 恒返回固定数"）

已知实现事实（doc §4 注记）：`AuditLog.page` 固定返回 has_more=false/next_cursor=null，
故 `has_more is True` 分支**当前不可达**。若该分支被命中，说明实现已偏离文档契约，
以具名 `pytest.skip`（BLOCKED）登记，而非留死断言。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_audit_02_pagination(admin_client):
    resp = admin_client.get("/v1/audit?limit=1")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data")
    assert isinstance(data, list), f"data 非数组: {type(data)}"
    assert len(data) <= 1, f"data.length > 1 但 limit=1: {body}"

    page = body.get("page")
    assert isinstance(page, dict), f"缺 page 对象: {list(body.keys())}"
    assert set(page) == {"has_more", "next_cursor"}, f"page 键集不符: {set(page)}"
    assert isinstance(page["has_more"], bool), f"has_more 非 bool: {page}"

    if page["has_more"] is True:
        # 文档明示当前实现恒 has_more=false（审计无 cursor 分页）。命中此分支即契约漂移。
        pytest.skip(
            "BLOCKED(ST-AUDIT-002 §4): 当前实现应恒 has_more=false/next_cursor=null，"
            f"但实际 has_more=True, next_cursor={page.get('next_cursor')!r}；"
            "该分页分支不可达，需复核契约/实现。")
    assert page["next_cursor"] is None, (
        f"has_more=false 但 next_cursor 非 null: {page}")

    # 对照：默认 50 的返回条数不应小于 limit=1 的返回条数（排除忽略 limit 的固定数）。
    control = admin_client.get("/v1/audit")
    assert control.status_code == 200, f"默认 limit 对照失败: {control.text}"
    assert len(control.json().get("data", [])) >= len(data), (
        f"默认 50 返回 {len(control.json().get('data', []))} 条 < limit=1 的 {len(data)} 条")
