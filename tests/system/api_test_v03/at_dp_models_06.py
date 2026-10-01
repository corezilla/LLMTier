"""Case ID: ST-model-006

Endpoint: GET /v1/models/NonExistent
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 404（精确，非 200/400/500）
- Content-Type: application/json；存在 X-Request-ID
- 顶层键集恰 {error}；error 恰 5 键 {message,type,code,param,retryable}
- error.code == "model_not_found"（精确，非泛化 not_found）
  、type == "request_error"、param is None、retryable is False
- 交叉核对：`NonExistent` 不在 `GET /v1/models` 的 id 集合（存在性差集证据）
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_models_06_unknown_model(api_client):
    # 交叉核对：证明目标 id 不在清单中（存在性维度）。
    listing = api_client.get("/v1/models")
    assert listing.status_code == 200, f"/v1/models 返回 {listing.status_code}: {listing.text}"
    known = {m["id"] for m in listing.json()["data"]}
    assert "NonExistent" not in known, (
        f"NonExistent 不应出现在清单中（存在性证据）: {sorted(known)}"
    )

    resp = api_client.get("/v1/models/NonExistent")
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert resp.headers.get("X-Request-ID"), f"缺 X-Request-ID: {dict(resp.headers)}"

    err = error_envelope(resp)
    assert err["code"] == "model_not_found", f"error.code != 'model_not_found': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 非 null: {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
    assert isinstance(err["message"], str) and err["message"], f"message 非非空字符串: {err}"
