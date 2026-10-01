"""Case ID: ST-logs-002

Endpoint: GET /v1/logs (缺 from/to)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 400
- error 信封恰 5 键；code=="invalid_request"、type=="request_error"、
  param is None、retryable is False
- 三种缺参变体（都缺 / 仅 from / 仅 to）均 400
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.constants import recent_window
from tests.system.api_test_v03.conftest import error_envelope


def _assert_invalid_request(resp):
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    err = error_envelope(resp)
    assert err["code"] == "invalid_request", f"error.code != 'invalid_request': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"


@pytest.mark.api_a
def test_adm_logs_02_missing_time_range(admin_client):
    _assert_invalid_request(admin_client.get("/v1/logs"))

    since, until = recent_window()
    _assert_invalid_request(admin_client.get("/v1/logs", params={"from": since}))
    _assert_invalid_request(admin_client.get("/v1/logs", params={"to": until}))
