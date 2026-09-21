"""Case ID: DP-RESP-11

Endpoint: POST /v1/responses
Upstream Provider: 不可用 provider（如 provider 指向已关闭端口）
Model: Worker
Auth: Bearer dev-data

目标：验证上游 provider 返回 5xx 时 LLMTier 的错误传播行为。

断言（预期）：
- HTTP 502/503/504
- error.code 包含 upstream 错误标识
- body 含原始错误信息（不泄露 provider 内部细节）

前置条件：
- 需要一个指向不可达端点的 provider（如临时创建 kind=local + endpoint=http://127.0.0.1:1）
- 或者 upstream OMLX 真的返回 503
- 当前 m5air 上游均正常，此 case 无法在现有环境中触发

结论：
此 case 目前无法在 m5air 上执行（无故障注入机制）。
预期行为通过代码审查记录：
- responses.py 调用 adapter._call() → adapter 上游 httpx 调用
- 上游 503 → httpx.HTTPStatusError → app.py:176 记录 unhandled_error → 返回 500 internal_error
- 或 adapter 捕获后返回特定错误格式
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
@pytest.mark.skip(reason="需要故障注入环境；当前 m5air 上游均健康")
def test_dp_resp_11_upstream_503_propagation():
    pytest.skip("DP-RESP-11 需要可注入故障的上游 provider；当前环境不可行")
