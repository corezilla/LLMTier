"""Case ID: ADM-PROV-USAGE-01

Endpoint: GET /v1/providers/{id}/usage
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 键集恰为 ProviderAccountUsageSnapshot 的 12 个必填键
  {provider,source,status,used,quota,remaining,percent,reset_at,window,windows,checked_at,error}
- status 属于枚举 {ok,unavailable,unsupported,unlimited,not_refreshed}
- provider/source/window/reset_at/checked_at/error 为字符串；
  used/quota/remaining/percent 为 number 或 null；windows 为数组
"""
from __future__ import annotations

import pytest

SNAPSHOT_KEYS = {
    "provider", "source", "status", "used", "quota", "remaining",
    "percent", "reset_at", "window", "windows", "checked_at", "error",
}
SNAPSHOT_STATUSES = {"ok", "unavailable", "unsupported", "unlimited", "not_refreshed"}


@pytest.mark.api_a
def test_adm_prov_usage_01_get_snapshot(admin_client):
    resp = admin_client.get("/v1/providers/provider_local/usage")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == SNAPSHOT_KEYS, f"键集不符: {set(body)} != {SNAPSHOT_KEYS}"
    assert body["status"] in SNAPSHOT_STATUSES, f"status 非枚举: {body['status']!r}"
    for field in ("provider", "source", "window", "reset_at", "checked_at", "error"):
        assert isinstance(body[field], str), f"{field} 非字符串: {type(body[field]).__name__}"
    for field in ("used", "quota", "remaining", "percent"):
        assert body[field] is None or isinstance(body[field], (int, float)), (
            f"{field} 非 number/null: {type(body[field]).__name__}")
    assert isinstance(body["windows"], list), f"windows 非数组: {type(body['windows']).__name__}"
