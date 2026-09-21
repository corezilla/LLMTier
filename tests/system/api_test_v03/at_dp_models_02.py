"""Case ID: DP-MODELS-02

Endpoint: GET /v1/models/{model}
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200
- body.id == "Worker"
- body.object == "model"
- body.created 是正整数（unix 秒）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_models_02_get_worker(api_client):
    resp = api_client.get("/v1/models/Worker")
    assert resp.status_code == 200, f"GET /v1/models/Worker 返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("id") == "Worker", f"id != 'Worker': {body}"
    assert body.get("object") == "model", f"object != 'model': {body}"
    created = body.get("created")
    assert isinstance(created, int) and created > 0, f"created 非正整数: {created}"
