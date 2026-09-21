"""Case ID: ADM-SL-07

Endpoint: POST /tier/admin/v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 embedding_space_conflict → 409。

注：当前基线 Embedding-v1 SL 已存在，尝试创建会先触发 UNIQUE 409 resource_conflict，
无法到达 embedding_space_conflict 检查。此 case 需要 Embedding-v1 SL 不存在才能触发。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_07_embedding_space_conflict(admin_client_b):
    pytest.skip("基线 Embedding-v1 SL 已存在，无法触发 embedding_space_conflict（UNIQUE 先于 _validate_level）")
