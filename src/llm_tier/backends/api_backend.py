from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from llm_tier.exceptions import BackendCallError, QuotaExhaustedError
from llm_tier.quota_manager import QuotaManager


# 用途：
# - 为 HTTP API backend 提供 JSON POST、quota error 识别和受总 deadline 约束的 retry 工具
# 输入：
# - backend 子类通过方法参数传入 URL、payload、headers、timeout 和 retry 上下文
# 输出：
# - 可复用的 HTTP JSON 响应解析、错误处理和 retry deadline 控制能力
class ApiBackendMixin:
    # 用途：
    # - 为带 retry 的 API backend 调用建立整次请求 deadline，避免每次 retry 都重新获得完整超时预算
    # 输入：
    # - timeout_seconds: 当前 backend 调用总超时秒数
    # 输出：
    # - monotonic deadline 时间戳
    def _api_retry_deadline(self, timeout_seconds: int) -> float:
        return time.monotonic() + max(1, int(timeout_seconds or 1))

    # 用途：
    # - 计算当前 API retry 剩余超时秒数，超出整次预算时抛出 backend timeout
    # 输入：
    # - deadline/timeout_seconds: 整次调用 deadline 和原始预算
    # 输出：
    # - 可传给 urllib 的本次请求 timeout 秒数
    def _remaining_api_timeout(self, deadline: float, timeout_seconds: int) -> int:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BackendCallError(self.backend, f"API call timed out after {int(timeout_seconds or 0)}s")
        return max(1, int(remaining))

    # 用途：
    # - 在 retry 前执行受 deadline 约束的退避等待
    # 输入：
    # - retry_count/deadline/timeout_seconds: 当前 retry 序号、整次 deadline 和原始预算
    # 输出：
    # - 无；预算耗尽时抛出 timeout
    def _sleep_before_api_retry(self, retry_count: int, deadline: float, timeout_seconds: int) -> None:
        delay_seconds = min(2.0 ** int(retry_count or 0), max(0.0, deadline - time.monotonic()))
        if delay_seconds <= 0:
            raise BackendCallError(self.backend, f"API call timed out after {int(timeout_seconds or 0)}s")
        time.sleep(delay_seconds)

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        import ssl
        context = ssl.create_default_context()
        try:
            import certifi
            context.load_verify_locations(certifi.where())
        except (ImportError, FileNotFoundError):
            context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _handle_http_error(
        self,
        status_code: int,
        body: str,
        retry_count: int,
        max_retry: int,
        model_name: str = "",
        retry_deadline: float | None = None,
        timeout_seconds: int = 0,
    ) -> None:
        if status_code == 429 or QuotaManager.is_quota_error(body):
            raise QuotaExhaustedError(self.backend, model_name, f"HTTP {status_code}: {body[:200]}")
        if 500 <= status_code < 600 and retry_count < max_retry:
            if retry_deadline is not None:
                self._sleep_before_api_retry(retry_count, retry_deadline, timeout_seconds)
            else:
                time.sleep(2.0 ** retry_count)
            return
        raise BackendCallError(self.backend, f"HTTP {status_code}: {body[:200]}")
