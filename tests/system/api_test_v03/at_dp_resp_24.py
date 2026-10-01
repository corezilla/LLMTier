"""Case ID: ST-resp-024

Endpoint: POST /v1/responses；GET/PATCH /v1/providers/prov_b
Upstream Provider: prov_b（secret_ref 改为不可读的 file: 引用）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_diag），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）；本 case 在 urlopen 前因凭据不可读抛错
  Auth: Bearer dev-data

目标：provider secret_ref 指向缺失文件 → 503 provider_secret_unavailable
（type server_error，retryable=false），在建立上游请求前拒绝。

实现：src/inference/providers/openai.py:45-49 `_secret()`
  file: 读取 OSError → ApiError(503, "provider_secret_unavailable",
                               "Provider secret file is unreadable")

断言：
- PATCH prov_b.secret_ref=file:/nonexistent/... → 200 且 has_secret 为真
- 被测 HTTP 503 + code "provider_secret_unavailable" + type "server_error"
  + param null + retryable False + 键集恰 5 键
- teardown：新 ETag PATCH 恢复 secret_ref 为原始值（None）
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}
MISSING_SECRET = "file:/nonexistent/llmtier-test/secret.txt"


def _get_provider(admin):
    resp = admin.get("/v1/providers/prov_b")
    assert resp.status_code == 200, f"GET provider 失败: {resp.text}"
    return resp.json(), resp.headers.get("ETag")


@pytest.mark.api_b
def test_dp_resp_24_provider_secret_unavailable(llmtier_b_diag):
    admin = llmtier_b_diag.admin_client()
    client = llmtier_b_diag.api_client()
    original = None
    try:
        original, etag = _get_provider(admin)
        assert etag, "GET provider 缺少 ETag"

        set_resp = admin.patch(
            "/v1/providers/prov_b",
            json={"secret_ref": MISSING_SECRET},
            headers={"If-Match": etag},
        )
        assert set_resp.status_code == 200, (
            f"PATCH secret_ref 失败: {set_resp.status_code}: {set_resp.text}"
        )
        assert set_resp.json().get("has_secret") is True, (
            f"改了 file: 引用后 has_secret 应为真: {set_resp.json()}"
        )

        resp = client.post(
            "/v1/responses",
            json={
                "model": "Senior",
                "input": [{"role": "user", "content": "hi"}],
                "stream": True,
                "store": False,
            },
        )
        assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
        assert resp.headers.get("content-type", "").startswith("application/json")
        err = resp.json().get("error") or {}
        assert err.get("code") == "provider_secret_unavailable", f"error.code 不符: {err}"
        assert err.get("type") == "server_error", f"error.type 不符: {err}"
        assert err.get("param") is None, f"error.param 非 null: {err}"
        assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
        assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
    finally:
        _, fresh_etag = _get_provider(admin)
        restore = admin.patch(
            "/v1/providers/prov_b",
            json={"secret_ref": None},
            headers={"If-Match": fresh_etag},
        )
        assert restore.status_code == 200, (
            f"恢复 secret_ref 失败: {restore.status_code}: {restore.text}"
        )
        assert restore.json().get("has_secret") == original.get("has_secret"), (
            "teardown 后 has_secret 与原值不一致"
        )
        client.close()
        admin.close()
