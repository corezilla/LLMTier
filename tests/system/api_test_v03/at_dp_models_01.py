"""Case ID: DP-MODELS-01

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (LAN trust 可缺省)

断言：
- HTTP 200
- body.object == "list"
- body.data[] 含 7 个 FIXED_TIERS，全部 id 唯一
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest


@pytest.mark.api_a
def test_dp_models_01_list_contains_7_tiers(api_client):
    resp = api_client.get("/v1/models")
    assert resp.status_code == 200, f"/v1/models 返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("object") == "list", f"object != 'list': {body}"

    data = body.get("data") or []
    ids = [m.get("id") for m in data]
    assert len(ids) == len(set(ids)), f"id 不唯一: {ids}"
    missing = set(FIXED_TIERS) - set(ids)
    assert not missing, f"缺 tier: {sorted(missing)}"
