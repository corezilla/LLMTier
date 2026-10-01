"""Case ID: ST-USAGE-005

Endpoint: GET /v1/usage
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  动态窗口: constants.recent_window()

目标（VRC-MGMT-006 / ERR-REQ-VALIDATION）：Usage 查询请求校验契约。
缺 `from`/`to`（或空串）在 handler 层 400；非法 date-time 或 `from >= to`
在 `_page` 层 400——均在建立 snapshot / 读账本之前被拒（零副作用）。

断言（7 变体 + 1 对照）：
- 变体 1–7 均 400 + invalid_request + request_error，信封恰 5 键、param is None
- 对照合法查询 ?from&to → 200
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.system.constants import recent_window

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


@pytest.mark.api_a
def test_dp_usage_05_missing_or_invalid_window(api_client):
    since, until = recent_window()
    now = datetime.now(timezone.utc)

    invalid_variants = [
        ("no params", {}),
        ("from only", {"from": since}),
        ("to only", {"to": until}),
        ("empty strings", {"from": "", "to": ""}),
        ("bad from", {"from": "not-a-date", "to": until}),
        ("bad to", {"from": since, "to": "2026-13-45"}),
        ("reversed", {"from": _iso(now), "to": _iso(now - timedelta(days=30))}),
        ("equal from==to", {"from": _iso(now), "to": _iso(now)}),
    ]

    for label, params in invalid_variants:
        resp = api_client.get("/v1/usage", params=params)
        assert resp.status_code == 400, (
            f"[{label}] 返回 {resp.status_code}（期望 400）: {resp.text}")
        body = resp.json()
        assert set(body) == {"error"}, f"[{label}] 顶层键集不符: {set(body)}"
        err = body["error"]
        assert set(err) == ERROR_KEYS, f"[{label}] error 键集不符: {set(err)}"
        assert err["code"] == "invalid_request", f"[{label}] code != invalid_request: {err}"
        assert err["type"] == "request_error", f"[{label}] type != request_error: {err}"
        assert err["param"] is None, f"[{label}] param != None: {err}"

    control = api_client.get("/v1/usage", params={"from": since, "to": until})
    assert control.status_code == 200, (
        f"对照合法查询期望 200，实际 {control.status_code}: {control.text}")
