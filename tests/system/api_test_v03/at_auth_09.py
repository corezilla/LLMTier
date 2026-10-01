"""Case ID: ST-auth-009

Endpoint: GET /v1/providers/{id}
Upstream Provider: 无（只读，不触发上游）
Model: 无
Auth: Bearer dev-data（data token，admin 面要求 admin）

依赖（TS-002）：
  Endpoint: http://192.168.1.9:8181（m5air A 类实例）
  Auth: Bearer dev-data
  上游: 无

断言（ST-auth-009，access-trust INV-3：401/403 不泄露资源存在性）：
- 存在 id（provider_local）与不存在 id（provider_does_not_exist_auth09）均返回 403
- 两者 error.code == "permission_denied"、type == "request_error"、
  param is None、retryable is False，error 恰 5 键；两响应在 status/code 上不可区分
- 不存在的 id 不得返回 404/not_found；两 body 均不含 ProviderView 字段

注：app.py:248 principal = self._auth("admin") 先于 provider 详情分支与
app.registry.get_provider(rid)（app.py:288-295）；data token ⇒ 403，不触达存在性判定。
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_09_admin_denial_precedes_existence():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        headers = {"Authorization": "Bearer dev-data"}
        existing = client.get("/v1/providers/provider_local", headers=headers)
        missing = client.get("/v1/providers/provider_does_not_exist_auth09", headers=headers)

    results = {"existing": existing, "missing": missing}
    for label, resp in results.items():
        assert resp.status_code == 403, (
            f"[{label}] 返回 {resp.status_code}（期望 403，授权先于存在性）: {resp.text}"
        )

    codes: dict[str, object] = {}
    for label, resp in results.items():
        body = resp.json()
        assert set(body.keys()) == {"error"}, (
            f"[{label}] envelope must have exactly one 'error' key: {body}"
        )
        err = body["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"[{label}] error envelope must have exactly 5 keys: {sorted(err.keys())}"
        )
        assert err["code"] == "permission_denied", f"[{label}] error.code != 'permission_denied': {err}"
        assert err["type"] == "request_error", f"[{label}] error.type != 'request_error': {err}"
        assert err["param"] is None, f"[{label}] error.param != None: {err}"
        assert err["retryable"] is False, f"[{label}] error.retryable != False: {err}"
        codes[label] = err["code"]
        # 不存在的 id 不得泄露存在性（404/not_found）。
        assert err["code"] != "not_found", f"[{label}] 存在性泄露（not_found）: {err}"
        # 拒绝路径不得泄露 ProviderView 内容。
        for field in ("id", "name", "kind", "secret_ref"):
            assert field not in body, f"[{label}] body 不得含 ProviderView 字段 {field!r}: {body}"

    # 两条响应不可区分（status 与 code 一致）。
    assert existing.status_code == missing.status_code, (
        f"存在/不存在 id 的 status 可区分: {existing.status_code} vs {missing.status_code}"
    )
    assert codes["existing"] == codes["missing"], (
        f"存在/不存在 id 的 code 可区分: {codes}"
    )
