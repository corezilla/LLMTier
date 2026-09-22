"""Case ID: ADM-ADMIN-USAGE-03

Endpoint: DELETE /tier/admin/v1/usage
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证清空 usage 统计记录功能。

断言：
- DELETE 无参数 → 200，body.deleted >= 0
- DELETE ?model=Worker → 200，body.deleted >= 0
- DELETE ?deployment_id=xxx → 200，body.deleted >= 0
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
@pytest.mark.skip(reason="新接口，需先 deploy 到 m5air（SSH 连不上 m5air 待恢复）")
def test_adm_admin_usage_03_reset_usage_all(admin_client):
    resp = admin_client.delete("/tier/admin/v1/usage")
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "deleted" in body
    assert isinstance(body["deleted"], int)
