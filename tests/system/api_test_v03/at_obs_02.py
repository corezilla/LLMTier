"""Case ID: OBS-02 / HEALTH-02

Endpoint: GET /readyz
Upstream Provider: 无
Model: 无
Auth: 无（公开端点 security:[]）——必须用**裸客户端**构造零凭据请求

断言（HEALTH-02）：
- 客户端发送头中**不含** Authorization（构造证据）
- HTTP 200
- 响应头含 X-Request-ID
- body 键集恰为 {status, models}
- body.status == "ready"
- body.models 恰为 7 个 FIXED_TIERS（无缺无多），逐元素键集恰 {id, availability}，全部 availability == "available"
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest


@pytest.mark.api_a
def test_obs_02_readyz_returns_7_tiers(bare_client):
    # 证据：裸客户端不携带 Authorization（security:[] 零凭据契约点）。
    assert "authorization" not in {k.lower() for k in bare_client.headers}, (
        f"裸客户端不得携带 Authorization: {dict(bare_client.headers)}"
    )

    resp = bare_client.get("/readyz")
    assert resp.status_code == 200, f"readyz 返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("X-Request-ID"), (
        f"readyz 响应缺 X-Request-ID: {dict(resp.headers)}"
    )

    body = resp.json()
    assert set(body.keys()) == {"status", "models"}, (
        f"ReadinessView 键集不符（期望恰 {{status, models}}）: {sorted(body.keys())}"
    )
    assert body["status"] == "ready", f"readyz status != 'ready': {body}"

    models = body["models"]
    ids = {m["id"] for m in models}
    assert len(models) == len(FIXED_TIERS), (
        f"readyz 期望 {len(FIXED_TIERS)} 个 tier，实际 {len(models)}: {sorted(ids)}"
    )
    assert ids == set(FIXED_TIERS), (
        f"readyz tier 集合不符: missing={sorted(set(FIXED_TIERS) - ids)}, "
        f"extra={sorted(ids - set(FIXED_TIERS))}"
    )

    for m in models:
        assert set(m.keys()) == {"id", "availability"}, (
            f"tier 元素键集不符（期望恰 {{id, availability}}）: {sorted(m.keys())}"
        )
        assert m["availability"] == "available", (
            f"tier {m['id']} availability={m['availability']}, expect 'available'"
        )
