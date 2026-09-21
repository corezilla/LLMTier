"""Case ID: ADM-AUDIT-02

Endpoint: GET /tier/admin/v1/audit?limit=1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data.length ≤ 1
- body.page.has_more 是 bool，has_more=true 时 next_cursor 非空
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_audit_02_pagination(admin_client):
    resp = admin_client.get("/tier/admin/v1/audit?limit=1")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert len(body.get("data", [])) <= 1, f"data.length > 1 但 limit=1: {body}"
    page = body.get("page") or {}
    assert isinstance(page.get("has_more"), bool), f"has_more 非 bool: {page}"
    if page.get("has_more") is True:
        assert page.get("next_cursor"), f"has_more=true 但 next_cursor 空: {page}"
