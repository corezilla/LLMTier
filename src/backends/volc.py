from __future__ import annotations

import urllib.error
from typing import Any

from backends import register_backend
from backends.api_backend import ApiBackendMixin
from backends.base import BaseBackendClient
from exceptions import BackendCallError


# 用途：
# - 封装火山 Ark coding endpoint 的 API backend 调用能力
# 输入：
# - api_key/base_url/timeout_seconds/kwargs: backend 初始化配置
# 输出：
# - llm_tier 可注册和调度的火山 backend client
class VolcClient(BaseBackendClient, ApiBackendMixin):
    # 用途：
    # - 初始化火山 API client，并读取显式配置或环境变量
    # 输入：
    # - api_key/base_url/timeout_seconds/kwargs: backend 配置参数
    # 输出：
    # - 无返回值，初始化实例状态
    def __init__(self, api_key: str = "", base_url: str = "", timeout_seconds: int = 300, **kwargs: Any) -> None:
        import os
        self._api_key = api_key or os.environ.get("LLMTIER_VOLC_API_KEY") or ""
        self._base_url = base_url or os.environ.get("LLMTIER_VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3")
        self._timeout_seconds = timeout_seconds
        self._current_model = ""

    @property
    # 用途：
    # - 返回 backend 名称
    # 输入：
    # - 无
    # 输出：
    # - backend 标识
    def backend(self) -> str:
        return "volc"

    @property
    # 用途：
    # - 返回 backend 类型
    # 输入：
    # - 无
    # 输出：
    # - API backend 类型标识
    def backend_type(self) -> str:
        return "API"

    # 用途：
    # - 声明 Volc client 当前支持的 API model id
    # 输入：
    # - 无
    # 输出：
    # - 可用于 settings.json `model_key` 的模型列表
    def supported_models(self) -> list[str]:
        return [
            "Auto",
            "Doubao-Seed-2.0-Code",
            "Doubao-Seed-2.0-pro",
            "Doubao-Seed-2.0-lite",
            "Doubao-Seed-Code",
            "doubao-seed-2.1-turbo",
            "MiniMax-M2.7",
            "MiniMax-M2.5",
            "Kimi-K2.6",
            "Kimi-K2.5",
            "kimi-k2.7-code",
            "GLM-5.1",
            "GLM-4.7",
            "glm-5.3",
            "DeepSeek-V3-2",
            "DeepSeek-V4-Flash",
            "DeepSeek-V4-Pro",
        ]

    # 用途：
    # - 执行一次火山 chat completions 调用
    # 输入：
    # - model_name/prompt/system_prompt/temperature/timeout_seconds/metadata/kwargs: 单次请求参数
    # 输出：
    # - llm_tier 统一格式的调用结果字典
    def call(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = 300,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self._current_model = model_name
        import time
        started = time.time()
        url = f"{self._base_url}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model_name, "messages": messages, "temperature": temperature}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        request_timeout_seconds = int(timeout_seconds or self._timeout_seconds or 300)
        retry_deadline = self._api_retry_deadline(request_timeout_seconds)
        max_retry = 3
        for attempt in range(max_retry + 1):
            try:
                resp = self._post_json(url, payload, headers, self._remaining_api_timeout(retry_deadline, request_timeout_seconds))
                latency = (time.time() - started) * 1000
                if not isinstance(resp, dict):
                    raise BackendCallError(self.backend, "malformed provider response: expected object")
                choices = resp.get("choices")
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    raise BackendCallError(self.backend, "malformed provider response: missing choices")
                choice = choices[0]
                message = choice.get("message")
                content = message.get("content") if isinstance(message, dict) else None
                if not isinstance(content, str) or not content.strip():
                    raise BackendCallError(self.backend, "malformed provider response: empty completion")
                if str(choice.get("finish_reason") or "").strip().lower() == "length":
                    raise BackendCallError(self.backend, "provider completion truncated at output limit")
                usage = resp.get("usage", {})
                return {
                    "ok": True, "content": content,
                    "model_name": resp.get("model", model_name), "latency_ms": latency,
                    "token_usage": {"prompt_tokens": usage.get("prompt_tokens", 0),
                                    "completion_tokens": usage.get("completion_tokens", 0),
                                    "total_tokens": usage.get("total_tokens", 0)},
                    "raw_response": resp, "error_code": 0, "error_message": "",
                }
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                self._handle_http_error(
                    exc.code,
                    body,
                    attempt,
                    max_retry,
                    model_name,
                    retry_deadline=retry_deadline,
                    timeout_seconds=request_timeout_seconds,
                )
            except Exception as exc:
                if attempt < max_retry:
                    self._sleep_before_api_retry(attempt, retry_deadline, request_timeout_seconds)
                    continue
                raise BackendCallError(self.backend, str(exc), original_error=exc)
        raise BackendCallError(self.backend, "max retries exceeded")


register_backend("volc", VolcClient)
