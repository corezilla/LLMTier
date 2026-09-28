"""Case ID: ADM-AUDIT-01

Endpoint: GET /v1/audit
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data 是数组，每条记录键集恰为 AuditEvent 必填 7 键
  {id,actor,action,target,result,created_at,request_id}
- 默认 limit=50：len(data) <= 50
- 无敏感信息泄露：响应 body 不含 secret 字面值 "9832" / "omlx-secret-key.txt"
"""
from __future__ import annotations

import pytest

AUDIT_EVENT_KEYS = {"id", "actor", "action", "target", "result", "created_at", "request_id"}


@pytest.mark.api_a
def test_adm_audit_01_list_no_secret_leak(admin_client):
    resp = admin_client.get("/v1/audit")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    assert isinstance(data, list), f"data 非数组: {type(data).__name__}"

    page = body.get("page")
    assert isinstance(page, dict), f"缺 page 对象: {list(body.keys())}"
    assert set(page) == {"has_more", "next_cursor"}, f"page 键集不符: {set(page)}"

    assert len(data) <= 50, f"默认 limit=50 被突破: len(data)={len(data)}"
    for event in data:
        assert set(event) == AUDIT_EVENT_KEYS, (
            f"事件键集不符（缺/多）: {set(event)} != {AUDIT_EVENT_KEYS}")

    body_text = resp.text
    forbidden_strings = ["9832", "omlx-secret-key.txt", "mnm_api_key"]
    for s in forbidden_strings:
        assert s not in body_text, f"audit 响应含敏感字符串 '{s}'（敏感信息泄露）"
