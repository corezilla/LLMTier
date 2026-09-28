"""Case ID: OBS-01

Endpoint: GET /healthz
Upstream Provider: 无
Model: 无
Auth: 无（公开端点）

断言：
- HTTP 200
- body.status == "ok"
- body.version 为非空字符串（HEALTH-01 要求 version:str）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a  # A 类标记；区分 B 类
def test_obs_01_healthz_returns_ok(api_client):  # noqa: api_a mark 仅供过滤用
    resp = api_client.get("/healthz")
    assert resp.status_code == 200, f"healthz 返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("status") == "ok", f"healthz status != 'ok': {body}"
    assert isinstance(body.get("version"), str), f"healthz version 非 str: {body}"
    assert body["version"], f"healthz version 为空: {body}"
