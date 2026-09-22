"""Case ID: ADM-RUNTIME-01

Endpoint: GET /v1/runtime
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 含 deployments/providers/queues（实际字段名，以实现为准）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_runtime_01_get_snapshot(admin_client):
    resp = admin_client.get("/v1/runtime")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("deployments", "providers", "queues"):
        assert field in body, f"runtime 缺 {field}: {list(body.keys())}"
    assert isinstance(body["providers"], dict)
    assert isinstance(body["deployments"], dict)
