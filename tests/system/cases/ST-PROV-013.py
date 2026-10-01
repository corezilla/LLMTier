"""Case ID: ST-PROV-013

Endpoint: PATCH /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 usage 子对象更新（max_concurrent_requests）。

断言：
- HTTP 200
- version == original_version+1；新 ETag == "<prov_b>.v<new>"
- 更新后 GET 能读到新值（持久化）
- teardown（finally 强制）：复位 usage 并断言已恢复原值（不得静默污染共享 prov_b）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_prov_13_usage_subobject_update(admin_client_b):
    current = admin_client_b.get("/v1/providers/prov_b")
    assert current.status_code == 200, f"GET prov_b 失败: {current.status_code}: {current.text}"
    etag = current.headers.get("ETag")
    assert etag, "GET prov_b 缺 ETag"
    before = current.json()
    original = before.get("usage", {}).get("max_concurrent_requests")
    original_version = before["version"]

    try:
        patch_resp = admin_client_b.patch(
            "/v1/providers/prov_b",
            json={"usage": {"max_concurrent_requests": 5}},
            headers={"If-Match": etag},
        )
        assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
        patched = patch_resp.json()
        assert patched["usage"]["max_concurrent_requests"] == 5
        expected_version = original_version + 1
        assert patched["version"] == expected_version, (
            f"version 期望 {expected_version}，实际 {patched['version']}")
        new_etag = patch_resp.headers.get("ETag")
        assert new_etag == f'"prov_b.v{expected_version}"', (
            f"新 ETag 期望 '\"prov_b.v{expected_version}\"', 实际 {new_etag!r}")

        get_resp = admin_client_b.get("/v1/providers/prov_b")
        assert get_resp.status_code == 200
        assert get_resp.json().get("usage", {}).get("max_concurrent_requests") == 5, (
            "usage 更新未持久化（仅响应回显）")
    finally:
        # Restore the original value; assert it actually took effect so a silent
        # restore failure cannot pollute the shared prov_b baseline.
        restore = admin_client_b.get("/v1/providers/prov_b")
        assert restore.status_code == 200, "teardown GET prov_b 失败"
        if original is not None and restore.json().get("usage", {}).get("max_concurrent_requests") != original:
            restored = admin_client_b.patch(
                "/v1/providers/prov_b",
                json={"usage": {"max_concurrent_requests": original}},
                headers={"If-Match": restore.headers["ETag"]},
            )
            assert restored.status_code == 200, (
                f"teardown 复位 PATCH 期望 200，实际 {restored.status_code}: {restored.text}")
        check = admin_client_b.get("/v1/providers/prov_b")
        assert check.status_code == 200
        assert check.json().get("usage", {}).get("max_concurrent_requests") == original, (
            f"teardown 复位失败：期望 {original!r}，实际 "
            f"{check.json().get('usage', {}).get('max_concurrent_requests')!r}")
