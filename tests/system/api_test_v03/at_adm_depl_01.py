"""Case ID: ADM-DEPL-01

Endpoint: GET /v1/deployments
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data[] 含 m5air 现有 4 个 deployment
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_depl_01_list_deployments(admin_client):
    resp = admin_client.get("/v1/deployments")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    ids = {d.get("id") for d in data}
    expected = {"dep_local_gemma", "dep_local_bge_m3", "dep_omlx_qwen36", "dep_minimax_m27"}
    missing = expected - ids
    assert not missing, f"缺 deployment: {sorted(missing)}（实际: {ids}）"
