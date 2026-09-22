"""Case ID: ADM-LOGS-01

Endpoint: GET /v1/logs?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data 是数组
- 无敏感信息泄露：message / module 字段不含 secret 字面值
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_logs_01_list_no_secret_leak(admin_client):
    resp = admin_client.get(
        "/v1/logs",
        params={"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    assert isinstance(data, list), f"data 非数组"

    forbidden_in_content = ("omlx-secret-key.txt", "mnm_api_key")
    for entry in data:
        for field in ("message", "module"):
            val = entry.get(field, "")
            for s in forbidden_in_content:
                assert s not in val, f"log entry[{field}] 含敏感字符串 '{s}': {val}"
