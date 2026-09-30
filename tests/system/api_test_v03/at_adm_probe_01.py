"""Case ID: ADM-PROBE-01

Endpoint: POST /v1/probes (缺 confirm_external_call)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 400
- error.code == "confirmation_required"
- error.type == "request_error"、param is None、retryable is False（doc §4 步 3）

诊断力：拒绝路径无中间产物；`AdminService.probe` 首行 `require` 在
`get_deployment` 之前，故不触上游、不写 probe_results/health/审计，零副作用。
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.conftest import error_envelope


@pytest.mark.api_a
def test_adm_probe_01_no_confirm(admin_client):
    resp = admin_client.post("/v1/probes", json={})
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"

    err = error_envelope(resp)
    assert err["code"] == "confirmation_required", f"error.code != 'confirmation_required': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"
