"""Case ID: ST-DEPL-003

Endpoint: GET /v1/deployments/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 键集恰为 DeploymentView 的 8 键（additionalProperties:false）
- id == "dep_local_gemma"、enabled 为布尔、version 为正整数、health ∈ 枚举
- capabilities 键集恰 12 键
- 响应头 ETag == f'"{id}.v{version}"'
"""
from __future__ import annotations

import pytest

DEPLOYMENT_VIEW_KEYS = {
    "id", "name", "provider_id", "backend_model", "capabilities", "enabled", "health", "version",
}
CAPABILITY_KEYS = {
    "responses", "embeddings", "tools", "structured_outputs", "input_modalities",
    "output_modalities", "context_window", "max_output_tokens", "embedding_space_id",
    "embedding_dimensions", "embedding_max_batch_inputs", "embedding_max_input_tokens",
}
HEALTH_VALUES = {"unknown", "healthy", "degraded", "unhealthy"}


@pytest.mark.api_a
def test_adm_depl_03_get_existing(admin_client):
    resp = admin_client.get("/v1/deployments/dep_local_gemma")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == DEPLOYMENT_VIEW_KEYS, f"DeploymentView 键集不符: {set(body)}"
    assert body["id"] == "dep_local_gemma"
    for field in ("name", "provider_id", "backend_model"):
        assert isinstance(body[field], str), f"{field} 非字符串: {body[field]!r}"
    assert isinstance(body["enabled"], bool), f"enabled 非布尔: {body['enabled']!r}"
    assert isinstance(body["version"], int) and body["version"] >= 1, (
        f"version 非正整数: {body['version']!r}")
    assert body["health"] in HEALTH_VALUES, f"health 非枚举: {body['health']!r}"
    assert set(body["capabilities"]) == CAPABILITY_KEYS, (
        f"capabilities 键集不符: {set(body['capabilities'])}")

    etag = resp.headers.get("ETag")
    assert etag == f'"{body["id"]}.v{body["version"]}"', (
        f"ETag 与 version 不一致: {etag!r} vs \"{body['id']}.v{body['version']}\"")
