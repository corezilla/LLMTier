from __future__ import annotations

import urllib.error
from typing import Any

from llm_tier.backends import register_backend
from llm_tier.backends.api_backend import ApiBackendMixin
from llm_tier.backends.base import BaseBackendClient
from llm_tier.exceptions import BackendCallError


class XfyunClient(BaseBackendClient, ApiBackendMixin):
    def __init__(self, api_key: str = "", base_url: str = "", timeout_seconds: int = 600, **kwargs: Any) -> None:
        import os
        self._api_key = api_key or os.environ.get("LLMTIER_XFYUN_API_KEY") or ""
        self._base_url = base_url or os.environ.get("LLMTIER_XFYUN_BASE_URL", "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2")
        self._timeout_seconds = timeout_seconds
        self._current_model: str = ""

    @property
    def backend(self) -> str:
        return "xfyun"

    @property
    def backend_type(self) -> str:
        return "API"

    def supported_models(self) -> list[str]:
        return ["astron-code-latest-2", "astron-code-latest-1"]

    # 用途：
    # - 调用讯飞 MaaS OpenAI-compatible chat completions 接口，并按整次请求预算执行 retry
    # 输入：
    # - model_name/prompt/system_prompt/temperature/timeout_seconds/metadata/kwargs: 单次 LLM 调用上下文
    # 输出：
    # - llm_tier 统一格式的调用结果字典
    def call(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = 600,
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

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        request_timeout_seconds = int(timeout_seconds or self._timeout_seconds or 600)
        retry_deadline = self._api_retry_deadline(request_timeout_seconds)
        max_retry = 3
        for attempt in range(max_retry + 1):
            try:
                resp = self._post_json(url, payload, headers, self._remaining_api_timeout(retry_deadline, request_timeout_seconds))
                latency = (time.time() - started) * 1000
                choice = resp.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = resp.get("usage", {})
                return {
                    "ok": True,
                    "content": content,
                    "model_name": resp.get("model", model_name),
                    "latency_ms": latency,
                    "token_usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    "raw_response": resp,
                    "error_code": 0,
                    "error_message": "",
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


register_backend("xfyun", XfyunClient)
