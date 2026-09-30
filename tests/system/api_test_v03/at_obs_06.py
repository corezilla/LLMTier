"""Case ID: HEALTH-06

Endpoint: GET /healthz, GET /readyz
Upstream Provider: 无（未配置鉴权的空实例）
Model: 无
Auth: 无（裸客户端，完全不带 Authorization 头）

依赖（TS-002）：
  Endpoint: http://127.0.0.1:<port>（临时 LLMTier 实例，fixture llmtier_b_no_auth）
  构造：_NO_AUTH_SETTINGS（三空 section）+ dev_mode=False ⇒ 不设任何 LLMTIER_*_TOKEN
  上游: 无

关键构造：必须使用**不携带 Authorization 的裸 httpx.Client**。
  不得复用 admin_client_b_no_auth —— 它由 _make_client 注入 Bearer dev-admin，
  在未配置 token 的实例上会走 authenticate() → 503 auth_not_configured，
  与本 case 的「健康端点免鉴权」契约无关。

断言（HEALTH-06）：
- GET /healthz（无凭据）→ 200，body 键集 {status, version}，status == "ok"，version 非空 str
- GET /readyz（无凭据）→ 200/503，body 键集 {status, models}，status ∈ {ready, degraded, not_ready}
- 两者均非 401/403，且 503 不得是 {"error":{"code":"auth_not_configured",...}}
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_b
def test_obs_06_health_endpoints_need_no_auth(llmtier_b_no_auth):
    # 裸客户端：完全不带 Authorization 头。
    with httpx.Client(base_url=llmtier_b_no_auth.base_url, timeout=10.0) as client:
        # 证据：发送头中无 Authorization。
        assert "authorization" not in {k.lower() for k in client.headers}, (
            f"裸客户端不得携带 Authorization: {dict(client.headers)}"
        )

        health = client.get("/healthz")
        assert health.status_code == 200, (
            f"/healthz 返回 {health.status_code}（期望 200，健康端点免鉴权）: {health.text}"
        )
        hbody = health.json()
        assert set(hbody.keys()) == {"status", "version"}, (
            f"HealthView 键集不符（期望恰 {{status, version}}）: {sorted(hbody.keys())}"
        )
        assert hbody["status"] == "ok", f"/healthz status != 'ok': {hbody}"
        assert isinstance(hbody["version"], str) and hbody["version"], (
            f"/healthz version 非非空 str: {hbody}"
        )

        ready = client.get("/readyz")
        assert ready.status_code in (200, 503), (
            f"/readyz 返回 {ready.status_code}（期望 200/503，合法 ReadinessView）: {ready.text}"
        )
        rbody = ready.json()
        assert set(rbody.keys()) == {"status", "models"}, (
            f"ReadinessView 键集不符（期望恰 {{status, models}}）—— 若为 "
            f"{{'error':...}} 说明命中了鉴权错误信封: {sorted(rbody.keys())}"
        )
        assert rbody["status"] in {"ready", "degraded", "not_ready"}, (
            f"/readyz status 非合法 ReadinessView 取值: {rbody['status']}"
        )

        # 两个健康端点均不得返回鉴权错误。
        for resp in (health, ready):
            assert resp.status_code not in (401, 403), (
                f"健康端点不得返回鉴权错误 {resp.status_code}: {resp.text}"
            )
            body = resp.json()
            code = (body.get("error") or {}).get("code")
            assert code != "auth_not_configured", (
                f"健康端点不得返回 auth_not_configured 信封: {body}"
            )
