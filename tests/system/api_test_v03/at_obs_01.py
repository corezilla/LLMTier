"""Case ID: OBS-01

Endpoint: GET /healthz
Upstream Provider: 无
Model: 无
Auth: 无（公开端点）

断言：
- HTTP 200
- body.status == "ok"
- body 含 version 字段
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a  # A 类标记；区分 B 类
def test_obs_01_healthz_returns_ok(api_client):  # noqa: api_a mark 仅供过滤用
    resp = api_client.get("/healthz")
    assert resp.status_code == 200, f"healthz 返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("status") == "ok", f"healthz status != 'ok': {body}"
