from __future__ import annotations


LLM_PROXY_HTTP_ERROR = 3101
LLM_PROXY_CONNECTION_ERROR = 3102
LLM_PROXY_TIMEOUT = 3103
LLM_PROXY_BACKEND_ERROR = 3104
LLM_PROXY_INVALID_CONTENT_TYPE = 3105
LLM_PROXY_EMPTY_CONTENT = 3106


class TierRouterError(Exception):
    """Base exception for Tier routing and backend selection failures."""


class QuotaExhaustedError(TierRouterError):
    def __init__(self, backend: str, model_name: str, message: str = "") -> None:
        self.backend = backend
        self.model_name = model_name
        self.message = message or f"Quota exhausted for {backend}:{model_name}"
        super().__init__(self.message)


class AllModelsExhaustedError(TierRouterError):
    def __init__(self, tier_name: str) -> None:
        self.tier_name = tier_name
        super().__init__(f"All models in tier {tier_name} are exhausted")


# 用途：
# - 表示单个 backend 调用失败，并保留可审计 raw_response 信息
# 输入：
# - backend/message/original_error/raw_response: 失败 backend、错误描述、原始异常和审计材料
# 输出：
# - 可被 router 捕获的 backend 调用异常
class BackendCallError(TierRouterError):
    # 用途：
    # - 初始化 backend 调用失败异常
    # 输入：
    # - backend/message/original_error/raw_response: 失败上下文和可选 stdout/stderr 路径
    # 输出：
    # - BackendCallError 实例
    def __init__(
        self,
        backend: str,
        message: str,
        original_error: Exception | None = None,
        raw_response: dict | None = None,
    ) -> None:
        self.backend = backend
        self.original_error = original_error
        self.raw_response = dict(raw_response or {})
        super().__init__(f"{backend} error: {message}")


class ConcurrencyTimeoutError(TierRouterError):
    """Raised when an account concurrency lease cannot be acquired in time."""
