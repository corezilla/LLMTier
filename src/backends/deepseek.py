from __future__ import annotations

import urllib.error
from typing import Any

from backends import register_backend
from backends.api_backend import ApiBackendMixin
from backends.base import BaseBackendClient
from exceptions import BackendCallError


# 用途：
# - 调用 OpenAI-compatible chat completions API，并让 DeepSeek/Local backend 共享统一结果解析和 retry deadline
# 输入：
# - self/model_name/prompt/system_prompt/temperature/timeout_seconds/base_url/api_key: backend 实例与单次调用上下文
# 输出：
# - llm_tier 统一格式的调用结果字典
def _api_call(self, model_name, prompt, system_prompt, temperature, timeout_seconds, base_url, api_key, max_tokens=0):
    import time
    started = time.time()
    url = f"{base_url}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model_name, "messages": messages, "temperature": temperature}
    if int(max_tokens or 0) > 0:
        payload["max_tokens"] = int(max_tokens)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    request_timeout_seconds = int(timeout_seconds or 300)
    retry_deadline = self._api_retry_deadline(request_timeout_seconds)
    max_retry = 3
    for attempt in range(max_retry + 1):
        try:
            resp = self._post_json(url, payload, headers, self._remaining_api_timeout(retry_deadline, request_timeout_seconds))
            latency = (time.time() - started) * 1000
            choice = resp.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = resp.get("usage", {})
            return {"ok": True, "content": content, "model_name": resp.get("model", model_name),
                    "latency_ms": latency,
                    "token_usage": {"prompt_tokens": usage.get("prompt_tokens", 0),
                                    "completion_tokens": usage.get("completion_tokens", 0),
                                    "total_tokens": usage.get("total_tokens", 0)},
                    "raw_response": resp, "error_code": 0, "error_message": ""}
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


class DeepSeekClient(BaseBackendClient, ApiBackendMixin):
    def __init__(self, api_key: str = "", base_url: str = "", timeout_seconds: int = 300, **kwargs: Any) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    @property
    def backend(self) -> str:
        return "deepseek"

    @property
    def backend_type(self) -> str:
        return "API"

    def supported_models(self) -> list[str]:
        return ["v4-pro", "v4-flash"]

    def call(self, model_name="", prompt="", system_prompt="", temperature=0.0, timeout_seconds=300, metadata=None, **kwargs):
        return _api_call(
            self,
            model_name,
            prompt,
            system_prompt,
            temperature,
            timeout_seconds,
            self._base_url,
            self._api_key,
            max_tokens=kwargs.get("max_tokens", 0),
        )


class LocalClient(BaseBackendClient, ApiBackendMixin):
    def __init__(self, api_key: str = "", base_url: str = "", timeout_seconds: int = 120, **kwargs: Any) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._api_key = api_key

    @property
    def backend(self) -> str:
        return "local"

    @property
    def backend_type(self) -> str:
        return "API"

    def supported_models(self) -> list[str]:
        return [
            "qwen2.5-coder-7b",
            "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            "Qwen3.6-35B-A3B",
            "Qwen3.6-35B-A3B-4bit-MTPLX-Optimized-Speed",
        ]

    def call(self, model_name="", prompt="", system_prompt="", temperature=0.0, timeout_seconds=120, metadata=None, **kwargs):
        return _api_call(
            self,
            model_name,
            prompt,
            system_prompt,
            temperature,
            timeout_seconds,
            self._base_url,
            self._api_key,
            max_tokens=kwargs.get("max_tokens", 0),
        )


register_backend("deepseek", DeepSeekClient)
register_backend("local", LocalClient)
register_backend("llama_cpp", LocalClient)
register_backend("omlx", LocalClient)
