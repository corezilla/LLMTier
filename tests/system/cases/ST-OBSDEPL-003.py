"""Case ID: ST-OBSDEPL-003

Endpoint: PATCH /v1/deployments/{deployment_id}/diagnostics
Upstream Provider: 无（写路径存在性校验；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003，本 case 不触）
  模型: depl_b（backend_model=test-model）

TS-003：本 case 不触发推理，无 provider endpoint 请求。

目标：PATCH /v1/deployments/{id}/diagnostics 对未知 deployment：HTTP 404 not_found，
不写入任何注入行。存在性优先于 items 校验（未知 id + items:[] / 非法 type 均 404）。
"""
from __future__ import annotations

import pytest

UNKNOWN = "does_not_exist"
DIAG_PATH = f"/v1/deployments/{UNKNOWN}/diagnostics"
BODIES = [
    {"items": [{"type": "delay", "config": {"delay_ms": 1000}, "enabled": True}]},
    {"items": []},
    {"items": [{"type": "bogus", "config": {}, "enabled": True}]},
    {"items": "not-a-list"},
]


@pytest.mark.api_b
def test_obs_depl_03_unknown_deployment_404(llmtier_b):
    client = llmtier_b.admin_client()
    get_resp = client.get(DIAG_PATH)
    assert get_resp.status_code == 404, (
        f"GET 未知 deployment 期望 404，实际 {get_resp.status_code}: {get_resp.text}"
    )
    assert get_resp.json()["error"]["code"] == "not_found", f"GET code 不符: {get_resp.json()}"

    for body in BODIES:
        resp = client.patch(DIAG_PATH, json=body)
        assert resp.status_code == 404, (
            f"PATCH {body} 期望 404（存在性优先），实际 {resp.status_code}: {resp.text}"
        )
        err = resp.json()["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"错误信封键集不符: {sorted(err.keys())}"
        )
        assert err["code"] == "not_found", f"PATCH {body} code 不符: {err}"
        assert err["type"] == "request_error", f"PATCH {body} type 不符: {err}"
        assert err["retryable"] is False, f"PATCH {body} retryable 应为 False: {err}"
    client.close()
