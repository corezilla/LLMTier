"""Case ID: HEALTH-03 / OBS-04

Endpoint: GET /readyz
Upstream Provider: prov_b（endpoint 为本机 LAN IP 上的 fake provider，TS-003）
Model: 无（无 probe）
Auth: 无（公开端点 security:[]）

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_unprobed），127.0.0.1:<临时端口>
  上游: LAN fake provider（provider_endpoint_b）——仅用于 bootstrap，不 probe
  Auth: 无（裸客户端）

目标：readyz 的 degraded 聚合分支——每个 fixed tier 有候选但无 healthy。

实现：src/http_api/health.py::readiness_view
  候选非空且 healthy==0 ⇒ availability=="degraded"；全部 tier degraded ⇒ status=="degraded"、HTTP 503。

断言：
- 构造证据：整班**从未调用** POST /v1/probes（llmtier_b_unprobed 不 probe）
- HTTP 503（精确，非 200）
- body 键集恰为 {status, models}
- models 长度 7，id 集合恰为 7 fixed tier
- 逐元素键集恰 {id, availability} 且 availability == "degraded"
- status == "degraded"
- 不得返回错误信封
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_b
def test_obs_04_readyz_degraded(llmtier_b_unprobed):
    # 未探测构造证据：实例自启动以来从未 probe，depl_b.health 保持 'unknown'。
    # 此处只读 /readyz，不调用 POST /v1/probes（契约点即"未探测"）。
    with httpx.Client(base_url=llmtier_b_unprobed.base_url, timeout=10.0) as client:
        resp = client.get("/readyz")

    assert resp.status_code == 503, (
        f"期望 503（degraded），实际 {resp.status_code}: {resp.text}"
    )
    assert resp.headers.get("content-type", "").startswith("application/json"), (
        f"Content-Type 不符: {resp.headers.get('content-type')!r}"
    )

    body = resp.json()
    assert set(body.keys()) == {"status", "models"}, (
        f"ReadinessView 键集不符（期望恰 {{status, models}}）: {sorted(body.keys())}"
    )
    assert "error" not in body, f"/readyz 不得返回 error 信封: {body}"

    models = body["models"]
    expected = {"Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1"}
    assert len(models) == 7, f"期望 7 个 FIXED_TIERS，实际 {len(models)}: {models}"
    ids = {m["id"] for m in models}
    assert ids == expected, f"ID 不匹配: {ids} vs {expected}"

    for m in models:
        assert set(m.keys()) == {"id", "availability"}, (
            f"tier 元素键集不符（期望恰 {{id, availability}}）: {sorted(m.keys())}"
        )
        assert m["availability"] == "degraded", (
            f"tier {m['id']} availability={m['availability']}, expect 'degraded'"
        )

    assert body["status"] == "degraded", f"期望 degraded，实际 {body['status']}"
