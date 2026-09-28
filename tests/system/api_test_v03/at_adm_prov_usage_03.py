"""Case ID: ADM-PROV-USAGE-03

Endpoint: POST /v1/providers/{id}/usage (带 confirm)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 键集恰为 ProviderAccountUsageSnapshot 的 12 个必填键
- status 属于枚举 {ok,unavailable,unsupported,unlimited,not_refreshed}
- provider_local 为 local：status == "unlimited"、source == "quota_config"

注：provider_local 是 local 类型，refresh 返回 "unlimited" snapshot（account_usage.py:167）。
"""
from __future__ import annotations

import pytest

SNAPSHOT_KEYS = {
    "provider", "source", "status", "used", "quota", "remaining",
    "percent", "reset_at", "window", "windows", "checked_at", "error",
}
SNAPSHOT_STATUSES = {"ok", "unavailable", "unsupported", "unlimited", "not_refreshed"}


@pytest.mark.api_a
def test_adm_prov_usage_03_refresh_with_confirm(admin_client):
    resp = admin_client.post(
        "/v1/providers/provider_local/usage",
        json={"confirm_external_call": True},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == SNAPSHOT_KEYS, f"键集不符: {set(body)} != {SNAPSHOT_KEYS}"
    assert body["status"] in SNAPSHOT_STATUSES, f"status 非枚举: {body['status']!r}"
    assert body["status"] == "unlimited", f"local 臂 status 期望 unlimited，实际 {body['status']!r}"
    assert body["source"] == "quota_config", f"local 臂 source 期望 quota_config，实际 {body['source']!r}"
