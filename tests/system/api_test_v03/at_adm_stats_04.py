"""Case ID: ST-STATS-004

Endpoint: GET /v1/stats
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

目标：观测/管理读面角色门——data 凭据访问 admin 读端点即 403（先于参数校验）。

断言（doc §4 步 4/5）：
- HTTP 403（不是 200、不是 401、不是 400，即使缺 from/to）
- 顶层键集恰 {"error"}；error 恰 5 键；code=="permission_denied"、
  type=="request_error"、param is None、retryable is False
- body 不含 StatsView 业务载荷
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.conftest import error_envelope


@pytest.mark.api_a
def test_adm_stats_04_get_with_data_token(api_client):
    resp = api_client.get("/v1/stats")
    assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = error_envelope(resp)
    assert err["code"] == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"
    assert "data" not in body, f"拒绝路径不得泄露 StatsView 载荷: {body}"
