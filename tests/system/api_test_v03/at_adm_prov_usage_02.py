"""Case ID: ST-PUSAGE-002

Endpoint: POST /v1/providers/{id}/usage (body 不是 {confirm_external_call})
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- 输入 A `{}` → HTTP 400 error.code == "invalid_request"
- 输入 B `{"confirm_external_call": false}` → HTTP 400 error.code == "confirmation_required"
- 两臂信封均 5 键、type=="request_error"、param is None、retryable is False
- 零副作用：快照 checked_at 未变

注：app.py:278 先于 account_usage.py:158 检查 body 集合 == {confirm_external_call}。
空 body {} → set != → invalid_request；键在值非真 → 落入 refresh 的 require → confirmation_required。
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.conftest import error_envelope


@pytest.mark.api_a
def test_adm_prov_usage_02_invalid_body(admin_client):
    before = admin_client.get("/v1/providers/provider_local/usage")
    assert before.status_code == 200, f"前置 GET usage 失败: {before.status_code}: {before.text}"
    checked_before = before.json()["checked_at"]

    # Arm A: {} (missing required key) → invalid_request
    resp_a = admin_client.post("/v1/providers/provider_local/usage", json={})
    assert resp_a.status_code == 400, f"臂 A 返回 {resp_a.status_code}（期望 400）: {resp_a.text}"
    err_a = error_envelope(resp_a)
    assert err_a["code"] == "invalid_request", f"臂 A error.code != 'invalid_request': {err_a}"
    assert err_a["type"] == "request_error", f"臂 A error.type != 'request_error': {err_a}"
    assert err_a["param"] is None, f"臂 A error.param != None: {err_a}"
    assert err_a["retryable"] is False, f"臂 A error.retryable != False: {err_a}"

    # Arm B: {"confirm_external_call": false} (key present, value not true) → confirmation_required
    resp_b = admin_client.post(
        "/v1/providers/provider_local/usage", json={"confirm_external_call": False},
    )
    assert resp_b.status_code == 400, f"臂 B 返回 {resp_b.status_code}（期望 400）: {resp_b.text}"
    err_b = error_envelope(resp_b)
    assert err_b["code"] == "confirmation_required", f"臂 B error.code != 'confirmation_required': {err_b}"
    assert err_b["type"] == "request_error", f"臂 B error.type != 'request_error': {err_b}"
    assert err_b["param"] is None, f"臂 B error.param != None: {err_b}"
    assert err_b["retryable"] is False, f"臂 B error.retryable != False: {err_b}"

    after = admin_client.get("/v1/providers/provider_local/usage")
    assert after.status_code == 200
    assert after.json()["checked_at"] == checked_before, (
        "被拒请求却写入了快照（checked_at 变化）")
