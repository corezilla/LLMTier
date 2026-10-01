"""Case ID: ST-model-007

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (LAN trust 可缺省)

目标：验证每个 tier 的 capabilities 字段键集恰为全部 12 个标准 key（无缺无多）。

断言：
- HTTP 200
- data[].capabilities 的键集恰为 12 个固定字段（openapi additionalProperties:false）：
  responses, embeddings, tools, structured_outputs,
  input_modalities, output_modalities,
  context_window, max_output_tokens,
  embedding_space_id, embedding_dimensions,
  embedding_max_batch_inputs, embedding_max_input_tokens
"""
from __future__ import annotations

import pytest

CAPABILITY_KEYS = frozenset({
    "responses", "embeddings", "tools", "structured_outputs",
    "input_modalities", "output_modalities",
    "context_window", "max_output_tokens",
    "embedding_space_id", "embedding_dimensions",
    "embedding_max_batch_inputs", "embedding_max_input_tokens",
})


@pytest.mark.api_a
def test_dp_models_07_capabilities_structure(api_client):
    resp = api_client.get("/v1/models")
    assert resp.status_code == 200, f"/v1/models 返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    assert len(data) > 0, "data 为空"

    for tier in data:
        tier_id = tier.get("id") or "?"
        caps = tier.get("capabilities") or {}
        actual = set(caps.keys())
        assert actual == CAPABILITY_KEYS, (
            f"tier {tier_id} capabilities 键集不符: "
            f"missing={sorted(CAPABILITY_KEYS - actual)}, extra={sorted(actual - CAPABILITY_KEYS)}"
        )
