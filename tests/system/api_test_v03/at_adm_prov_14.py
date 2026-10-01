"""Case ID: ST-prov-014

Endpoint: GET /v1/providers, GET /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  依赖 provider: provider_omlx_m5mac（§2.1.5 保证 has_secret=true）

目标（VRC-MGMT-001 / T-CFG-SECRET）：provider 读取响应体永不回显秘密值——
列表与详情均不含 `secret_ref` 键，仅 `has_secret: boolean`；原始响应字节的
否定扫描不含 key 文件内容 / 上游 Bearer 字面 `9832` / `Authorization` 凭据。

断言：
- GET /v1/providers 与 GET /v1/providers/provider_omlx_m5mac 均 200
- 每个 provider 元素键集恰为 ProviderView 9 键，无 `secret_ref` 键
- detail.has_secret is True
- 原始 body 文本不含 "9832" / "secret_ref" / "Bearer "
"""
from __future__ import annotations

import re

import pytest

PROVIDER_VIEW_KEYS = {
    "id", "name", "kind", "endpoint", "has_secret",
    "enabled", "usage", "request_usage", "version",
}

# "9832" is a 4-digit token that can coincidentally appear inside a random
# request-id hex run / RFC3339 timestamp / counter value, so match it only as a
# standalone alphanumeric token (not surrounded by [0-9A-Za-z]) — this still
# catches a real `Bearer 9832`-style echo without the substring false positive.
# A digit-only boundary is insufficient because hex ids contain letters.
_SECRET_NEEDLES = ("secret_ref", "Bearer ")
_TOKEN_RE = re.compile(r"(?<![0-9A-Za-z])9832(?![0-9A-Za-z])")


def _assert_no_secret_fields(raw_text: str, label: str) -> None:
    for needle in _SECRET_NEEDLES:
        assert needle not in raw_text, f"{label} 响应含敏感串 {needle!r}（秘密泄露）"
    assert not _TOKEN_RE.search(raw_text), (
        f"{label} 响应含敏感 token 字面 '9832'（秘密泄露）"
    )


@pytest.mark.api_a
def test_adm_prov_14_provider_read_never_leaks_secret(admin_client):
    list_resp = admin_client.get("/v1/providers")
    assert list_resp.status_code == 200, f"列表返回 {list_resp.status_code}: {list_resp.text}"
    list_body = list_resp.json()
    items = list_body.get("data") or []
    assert isinstance(items, list), f"data 非数组: {type(items).__name__}"
    assert items, "provider 列表为空，无法覆盖列表读路径"
    for item in items:
        assert "secret_ref" not in item, f"列表元素回显 secret_ref: {item}"
        assert set(item) == PROVIDER_VIEW_KEYS, (
            f"列表元素键集不符: {set(item)} != {PROVIDER_VIEW_KEYS}")
    _assert_no_secret_fields(list_resp.text, "列表")

    detail_resp = admin_client.get("/v1/providers/provider_omlx_m5mac")
    assert detail_resp.status_code == 200, (
        f"详情返回 {detail_resp.status_code}: {detail_resp.text}")
    detail = detail_resp.json()
    assert set(detail) == PROVIDER_VIEW_KEYS, (
        f"详情键集不符: {set(detail)} != {PROVIDER_VIEW_KEYS}")
    assert "secret_ref" not in detail, f"详情回显 secret_ref: {detail}"
    assert detail["has_secret"] is True, (
        f"provider_omlx_m5mac.has_secret 期望 True，实际 {detail['has_secret']!r}")
    assert isinstance(detail["has_secret"], bool), "has_secret 非布尔"
    _assert_no_secret_fields(detail_resp.text, "详情")
