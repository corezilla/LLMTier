"""Case ID: ADM-SL-03

Endpoint: GET /tier/admin/v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- 含 id, deployment_ids, enabled, capabilities, version
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_sl_03_get_existing(admin_client):
    resp = admin_client.get("/tier/admin/v1/service-levels/Worker")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("id", "deployment_ids", "enabled", "capabilities", "version"):
        assert field in body, f"缺字段 {field}: {body}"
    assert body["id"] == "Worker"
    assert isinstance(body["deployment_ids"], list)
