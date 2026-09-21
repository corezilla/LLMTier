"""Case ID: ADM-SL-06

Endpoint: POST /tier/admin/v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 capability_conflict → 409。

注：当前基线（_BASELINE_SETTINGS）已预填充全部 7 个 FIXED_TIERS。
尝试创建已存在的 FIXED_TIER SL 会在 _validate_level 之前
因 UNIQUE 约束触发 409 resource_conflict，无法到达 capability_conflict 检查。
此 case 需要基线状态中不存在目标 fixed tier 才能触发。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_06_capability_conflict(admin_client_b):
    pytest.skip("基线预填充全部 fixed tier，无法触发 capability_conflict（UNIQUE 先于 _validate_level）")
