"""Case ID: OBS-02

Endpoint: GET /readyz
Upstream Provider: 无
Model: 无
Auth: 无（公开端点）

断言：
- HTTP 200
- body.status == "ready"
- body.models 含 7 个 FIXED_TIERS，全部 availability == "available"
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest


@pytest.mark.api_a
def test_obs_02_readyz_returns_7_tiers(api_client):
    resp = api_client.get("/readyz")
    assert resp.status_code == 200, f"readyz 返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("status") == "ready", f"readyz status != 'ready': {body}"

    models = body.get("models") or body.get("tiers") or []
    ids = {m.get("id") if isinstance(m, dict) else m for m in models}
    missing = set(FIXED_TIERS) - ids
    assert not missing, f"readyz missing tiers: {sorted(missing)}"

    for m in models:
        if isinstance(m, dict) and m.get("id") in FIXED_TIERS:
            assert m.get("availability") == "available", (
                f"tier {m.get('id')} availability={m.get('availability')}, expect 'available'"
            )
