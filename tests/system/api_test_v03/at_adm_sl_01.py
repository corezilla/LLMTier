"""Case ID: ADM-SL-01

Endpoint: GET /tier/admin/v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data[] 含 7 个 FIXED_TIERS（Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1）
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest


@pytest.mark.api_a
def test_adm_sl_01_list_service_levels(admin_client):
    resp = admin_client.get("/tier/admin/v1/service-levels")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    ids = {s.get("id") for s in data}
    missing = set(FIXED_TIERS) - ids
    assert not missing, f"缺 service level: {sorted(missing)}（实际: {ids}）"
