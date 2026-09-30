"""Case ID: ADM-SL-03

Endpoint: GET /v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 键集恰为 ServiceLevelView 的 5 键（additionalProperties:false）
- id == "Worker"、deployment_ids 为数组、enabled 为布尔、version 为 int ≥1
- capabilities 键集恰 12 键
- 响应头 ETag == f'"{id}.v{version}"'
"""
from __future__ import annotations

import pytest

SERVICE_LEVEL_VIEW_KEYS = {"id", "deployment_ids", "enabled", "capabilities", "version"}
CAPABILITY_KEYS = {
    "responses", "embeddings", "tools", "structured_outputs", "input_modalities",
    "output_modalities", "context_window", "max_output_tokens", "embedding_space_id",
    "embedding_dimensions", "embedding_max_batch_inputs", "embedding_max_input_tokens",
}


@pytest.mark.api_a
def test_adm_sl_03_get_existing(admin_client):
    resp = admin_client.get("/v1/service-levels/Worker")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == SERVICE_LEVEL_VIEW_KEYS, f"ServiceLevelView 键集不符: {set(body)}"
    assert body["id"] == "Worker"
    assert isinstance(body["deployment_ids"], list)
    assert isinstance(body["enabled"], bool), f"enabled 非布尔: {body['enabled']!r}"
    assert isinstance(body["version"], int) and body["version"] >= 1, (
        f"version 非 int≥1: {body['version']!r}")
    assert set(body["capabilities"]) == CAPABILITY_KEYS, (
        f"capabilities 键集不符: {set(body['capabilities'])}")

    etag = resp.headers.get("ETag")
    assert etag == f'"{body["id"]}.v{body["version"]}"', (
        f"ETag 与 version 不一致: {etag!r} vs \"{body['id']}.v{body['version']}\"")
