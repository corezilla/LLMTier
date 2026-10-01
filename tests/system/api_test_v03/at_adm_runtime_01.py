"""Case ID: ST-RUNTIME-001

Endpoint: GET /v1/runtime
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200，Content-Type 含 application/json
- body 键集恰为 {deployments,providers,queues}；三键均为 dict
- providers 元素键集 == {running,max_concurrent,min_request_interval_ms,requests_per_minute}
  （Router.snapshot 契约，routing.py:59-67）
- deployments 元素键集 == {running,max_concurrent}
- （一致性）deployments 键 ⊆ GET /v1/deployments 的 id 集合

不设数值门限（running/max_concurrent 为运行时动态值）。
"""
from __future__ import annotations

import pytest

PROVIDER_KEYS = {"running", "max_concurrent", "min_request_interval_ms", "requests_per_minute"}
DEPLOYMENT_KEYS = {"running", "max_concurrent"}


@pytest.mark.api_a
def test_adm_runtime_01_get_snapshot(admin_client):
    resp = admin_client.get("/v1/runtime")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert "application/json" in resp.headers.get("Content-Type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('Content-Type')!r}")

    body = resp.json()
    assert set(body) == {"deployments", "providers", "queues"}, (
        f"runtime 顶层键集不符: {set(body)}")
    assert isinstance(body["deployments"], dict), f"deployments 非 dict: {type(body['deployments'])}"
    assert isinstance(body["providers"], dict), f"providers 非 dict: {type(body['providers'])}"
    assert isinstance(body["queues"], dict), f"queues 非 dict: {type(body['queues'])}"

    for pid, entry in body["providers"].items():
        assert isinstance(entry, dict), f"provider[{pid}] 非对象: {entry}"
        assert set(entry) == PROVIDER_KEYS, (
            f"provider[{pid}] 键集不符: {set(entry)} != {PROVIDER_KEYS}")
        for key in ("running", "max_concurrent"):
            assert isinstance(entry[key], int), f"provider[{pid}].{key} 非 int: {entry[key]!r}"

    for did, entry in body["deployments"].items():
        assert isinstance(entry, dict), f"deployment[{did}] 非对象: {entry}"
        assert set(entry) == DEPLOYMENT_KEYS, (
            f"deployment[{did}] 键集不符: {set(entry)} != {DEPLOYMENT_KEYS}")
        for key in ("running", "max_concurrent"):
            assert isinstance(entry[key], int), f"deployment[{did}].{key} 非 int: {entry[key]!r}"

    # 一致性：快照中的 deployment 键必须来自注册表。
    listing = admin_client.get("/v1/deployments")
    assert listing.status_code == 200, f"GET /v1/deployments 失败: {listing.text}"
    known_ids = {d["id"] for d in listing.json().get("data", [])}
    unknown = set(body["deployments"]) - known_ids
    assert not unknown, f"runtime 快照出现未注册 deployment: {unknown}"
