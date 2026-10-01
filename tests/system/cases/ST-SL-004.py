"""Case ID: ST-SL-004

Endpoint: PATCH /v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：FIXED_TIER "Junior" 已存在（baseline 预创建）

断言：
- PATCH 带正确 If-Match，body 含 {"enabled": false}；HTTP 200
- enabled == false；version == original + 1（精确）
- 新 ETag == f'"{id}.v{version}"'
- 未提交字段 deployment_ids/capabilities 保持原值
- GET 回读：enabled 持久化且 ETag 与新响应头一致
- teardown（finally）：用最新 ETag 复位 enabled=True
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_04_update_service_level(admin_client_b):
    get_resp = admin_client_b.get("/v1/service-levels/Junior")
    assert get_resp.status_code == 200
    tier = get_resp.json()
    original_etag = get_resp.headers.get("ETag")

    try:
        assert tier["enabled"] is True, "期望 baseline Junior 为 enabled=True"
        original_version = tier["version"]

        patch_resp = admin_client_b.patch(
            "/v1/service-levels/Junior",
            json={"enabled": False},
            headers={"If-Match": original_etag},
        )
        assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
        updated = patch_resp.json()
        assert updated["enabled"] is False
        assert updated["version"] == original_version + 1, (
            f"version 应精确 +1：{original_version} -> {updated['version']}")
        new_etag = patch_resp.headers.get("ETag")
        assert new_etag == f'"Junior.v{updated["version"]}"', (
            f"新 ETag 不符: {new_etag!r} vs \"Junior.v{updated['version']}\"")
        assert updated["deployment_ids"] == tier["deployment_ids"], "deployment_ids 不应被更改"
        assert updated["capabilities"] == tier["capabilities"], "capabilities 不应被更改"

        readback_resp = admin_client_b.get("/v1/service-levels/Junior")
        assert readback_resp.status_code == 200
        readback = readback_resp.json()
        assert readback["enabled"] is False, "enabled=false 未持久化"
        assert readback["version"] == updated["version"]
        assert readback_resp.headers.get("ETag") == new_etag, "回读 ETag 与 PATCH 响应头不一致"
    finally:
        # Restore the baseline state (enabled=True) so later cases are unaffected.
        current = admin_client_b.get("/v1/service-levels/Junior")
        if current.status_code == 200 and current.json().get("enabled") is not True:
            restore = admin_client_b.patch(
                "/v1/service-levels/Junior",
                json={"enabled": True},
                headers={"If-Match": current.headers["ETag"]},
            )
            assert restore.status_code == 200, f"teardown 复位失败: {restore.text}"
            assert restore.json()["enabled"] is True, "teardown 后 Junior 未复位为 enabled=True"
