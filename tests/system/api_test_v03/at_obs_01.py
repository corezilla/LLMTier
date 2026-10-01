"""Case ID: ST-health-001

Endpoint: GET /healthz
Upstream Provider: 无
Model: 无
Auth: 无（公开端点 security:[]）——必须用**裸客户端**构造零凭据请求

断言（ST-health-001）：
- 客户端发送头中**不含** Authorization（构造证据）
- HTTP 200
- 响应头含 X-Request-ID
- body 键集恰为 {status, version}
- body.status == "ok"
- body.version 为非空字符串
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a  # A 类标记；区分 B 类
def test_obs_01_healthz_returns_ok(bare_client):
    # 证据：裸客户端不携带 Authorization（security:[] 零凭据契约点）。
    assert "authorization" not in {k.lower() for k in bare_client.headers}, (
        f"裸客户端不得携带 Authorization: {dict(bare_client.headers)}"
    )

    resp = bare_client.get("/healthz")
    assert resp.status_code == 200, f"healthz 返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("X-Request-ID"), (
        f"healthz 响应缺 X-Request-ID: {dict(resp.headers)}"
    )

    body = resp.json()
    assert set(body.keys()) == {"status", "version"}, (
        f"HealthView 键集不符（期望恰 {{status, version}}）: {sorted(body.keys())}"
    )
    assert body["status"] == "ok", f"healthz status != 'ok': {body}"
    assert isinstance(body["version"], str), f"healthz version 非 str: {body}"
    assert body["version"], f"healthz version 为空: {body}"
