"""Case ID: ADM-LOGS-01

Endpoint: GET /tier/admin/v1/logs?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data 是数组
- 无敏感信息泄露（响应 body 不含 secret 字面值）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_logs_01_list_no_secret_leak(admin_client):
    resp = admin_client.get(
        "/tier/admin/v1/logs",
        params={"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    assert isinstance(data, list), f"data 非数组"

    body_text = resp.text
    for s in ("9832", "omlx-secret-key.txt", "mnm_api_key"):
        assert s not in body_text, f"logs 响应含敏感字符串 '{s}'"
