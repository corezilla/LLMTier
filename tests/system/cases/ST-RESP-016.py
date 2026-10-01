"""Case ID: ST-RESP-016

Endpoint: POST /v1/responses（原始字节 body）
Upstream Provider: 无（解析层拒绝，早于路由）
Model: —
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b），127.0.0.1:<临时端口>
  上游: 不需要（解析阶段拒绝）
  Auth: Bearer dev-data

目标：非法 JSON body / 非对象 JSON → 400 invalid_json，dispatch 前拒绝。

实现：src/http_api/app.py `_body()`
  json.loads 失败 → ApiError(400, "invalid_json", "Request body is not valid JSON")
  解析成功但非对象 → ApiError(400, "invalid_json", "Request body must be a JSON object")

断言：
- HTTP 400
- error.code == "invalid_json"、type == "request_error"
- param is None、retryable is False、键集恰 5 键
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


def _assert_invalid_json(resp, expected_message: str, raw: bytes) -> None:
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json"), (
        f"应返回 JSON 错误信封，content-type={resp.headers.get('content-type')!r}"
    )
    body = resp.json()
    assert "error" in body, f"缺少 error 信封: {body}"
    err = body["error"]
    assert err.get("code") == "invalid_json", f"error.code 不符: {err}"
    assert err.get("type") == "request_error", f"error.type 不符: {err}"
    assert err.get("param") is None, f"error.param 非 null: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
    assert expected_message in err.get("message", ""), (
        f"message 与违规不符（raw={raw!r}）: {err.get('message')}"
    )


@pytest.mark.api_b
def test_dp_resp_16_malformed_json_body(api_client_b):
    raw = b'{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false,'
    resp = api_client_b.post(
        "/v1/responses",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    _assert_invalid_json(resp, "not valid JSON", raw)


@pytest.mark.api_b
def test_dp_resp_16_non_object_json_body(api_client_b):
    raw = b"[1,2,3]"
    resp = api_client_b.post(
        "/v1/responses",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    _assert_invalid_json(resp, "must be a JSON object", raw)
