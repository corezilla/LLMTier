"""Case ID: ADM-PROBE-01

Endpoint: POST /v1/probes (缺 confirm_external_call)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 400
- error.code == "confirmation_required"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_probe_01_no_confirm(admin_client):
    resp = admin_client.post("/v1/probes", json={})
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "confirmation_required", f"error.code != 'confirmation_required': {err}"
