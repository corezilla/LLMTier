"""Case ID: ST-MODEL-005

Endpoint: GET /v1/models/Senior%20（URL 编码空格）
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- 发送目标保留 `%20` 编码（请求行/raw_path 快照证据）
- HTTP 404（精确，非 200/400/500）
- Content-Type: application/json；存在 X-Request-ID
- 顶层键集恰 {error}；error 恰 5 键 {message,type,code,param,retryable}
- error.code == "model_not_found"、type == "request_error"、param is None、retryable is False

注：Oracle 只锁 status==404 + code==model_not_found，不断言 404 的具体成因
（字面 `Senior%20` 未命中 vs decode 后 `Senior ` 未命中皆可）。
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_models_05_url_encoded_space_rejected(api_client):
    # 证据：httpx 原样发送 `%20`（不还原为裸空格），raw_path 保留编码。
    request = api_client.build_request("GET", "/v1/models/Senior%20")
    assert b"%20" in request.url.raw_path, (
        f"请求目标应保留 %20 编码: raw_path={request.url.raw_path!r}"
    )

    resp = api_client.send(request)
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert resp.headers.get("X-Request-ID"), f"缺 X-Request-ID: {dict(resp.headers)}"

    err = error_envelope(resp)
    assert err["code"] == "model_not_found", f"error.code != 'model_not_found': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 非 null: {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
    assert isinstance(err["message"], str) and err["message"], f"message 非非空字符串: {err}"
