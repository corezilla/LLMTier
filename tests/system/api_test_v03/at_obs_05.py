"""Case ID: HEALTH-05

Endpoint: GET /healthz, GET /readyz
Upstream Provider: 无（引导失败实例，不接上游）
Model: 无
Auth: 无（公开端点）

依赖（TS-002）：
  Endpoint: http://127.0.0.1:<port>（临时 LLMTier 实例，fixture llmtier_b_no_bootstrap）
  构造：空库 + 无 settings（LLMTierInstance(settings=None)）⇒ 不提供 LLMTIER_SETTINGS，
        bootstrap_settings(None) 抛 bootstrap_required ⇒ app.bootstrap_error 非空
  上游: 无（本构造不接 provider）

断言（HEALTH-05）：
- GET /healthz → 200，status == "ok"（引导失败 ≠ 进程死亡）
- GET /readyz → 503；body 键集恰为 {status, models}；status == "not_ready"；models == []（空数组）
- /readyz body 不含 {"error":...} 信封（bootstrap envelope 码由单元层 UT-MGMT-001 断言）

注：核心区分点是 models == []（HEALTH-04 的 not_ready 为 7×unavailable）。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_obs_05_readyz_bootstrap_failure(llmtier_b_no_bootstrap):
    client = llmtier_b_no_bootstrap.admin_client()
    try:
        # 进程存活：/healthz 位于 bootstrap_error 检查之前，仍 200。
        health = client.get("/healthz")
        assert health.status_code == 200, (
            f"/healthz 返回 {health.status_code}（期望 200，引导失败 ≠ 进程死亡）: {health.text}"
        )
        hbody = health.json()
        assert hbody.get("status") == "ok", f"/healthz status != 'ok': {hbody}"
        assert isinstance(hbody.get("version"), str) and hbody["version"], (
            f"/healthz version 非非空 str: {hbody}"
        )

        # 就绪失败：/readyz 短路返回 503 + 空 models（非 HEALTH-04 的 7×unavailable）。
        resp = client.get("/readyz")
        assert resp.status_code == 503, (
            f"/readyz 返回 {resp.status_code}（期望 503，bootstrap 失败）: {resp.text}"
        )
        body = resp.json()
        assert set(body.keys()) == {"status", "models"}, (
            f"ReadinessView 键集不符（期望恰 {{status, models}}）: {sorted(body.keys())}"
        )
        assert body["models"] == [], (
            f"bootstrap 失败应返回空 models（HEALTH-04 路径应为 7×unavailable）: {body['models']}"
        )
        assert body["status"] == "not_ready", f"期望 not_ready，实际 {body['status']}"

        # 不得以错误信封表达引导失败。
        assert "error" not in body, f"/readyz 不得返回 error 信封: {body}"
    finally:
        client.close()
