"""Case ID: ADM-PROBE-02

Endpoint: POST /v1/probes (带 confirm + deployment_id)
Upstream Provider: 取决于 deployment
Model: 取决于 deployment
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 含 deployment_id, status (healthy/unhealthy), checked_at, may_have_incurred_cost

注：probe body 必须恰好是 {deployment_id, confirm_external_call}（admin.py:106）。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_probe_02_with_confirm(admin_client):
    resp = admin_client.post(
        "/v1/probes",
        json={"deployment_id": "dep_local_gemma", "confirm_external_call": True},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("deployment_id", "status", "checked_at", "may_have_incurred_cost"):
        assert field in body, f"缺 {field}: {body}"
    assert body["status"] in ("healthy", "unhealthy"), f"status 非法: {body['status']}"
