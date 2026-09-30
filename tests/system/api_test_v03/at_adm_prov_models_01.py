"""Case ID: ADM-PROV-MODELS-01

Endpoint: GET /v1/providers/{id}/models
Upstream Provider: provider_local
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  依赖 provider: provider_local（§2.1.6 必需）

目标（VRC-MGMT-001）：provider 上游模型目录读契约——HTTP 200 + ProviderModelsView
（`data: string[]`，additionalProperties:false，required=[data]）；同步只读，不改本地资源。

断言：
- HTTP 200，Content-Type 含 application/json
- body 键集恰为 {data}
- data 为数组且元素全为字符串（允许空数组）
- 交叉核对：GET /v1/providers/provider_local 200（佐证 provider 存在）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_models_01_list_provider_models(admin_client):
    resp = admin_client.get("/v1/providers/provider_local/models")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    ctype = resp.headers.get("Content-Type", "")
    assert "application/json" in ctype, f"Content-Type 不含 application/json: {ctype!r}"

    body = resp.json()
    assert isinstance(body, dict), f"body 非对象: {type(body).__name__}"
    assert set(body) == {"data"}, f"键集不符（additionalProperties:false）: {set(body)}"
    data = body["data"]
    assert isinstance(data, list), f"data 非数组: {type(data).__name__}"
    for element in data:
        assert isinstance(element, str), f"data 含非字符串元素: {element!r}"

    # Cross-check: the provider itself exists (200 is a real directory read, not a fallback).
    detail = admin_client.get("/v1/providers/provider_local")
    assert detail.status_code == 200, (
        f"provider_local 详情期望 200，实际 {detail.status_code}: {detail.text}")
