from __future__ import annotations

import os
import time
import urllib.error
from pathlib import Path
from typing import Any

from llm_tier.backends import register_backend
from llm_tier.backends.api_backend import ApiBackendMixin
from llm_tier.backends.base import BaseBackendClient
from llm_tier.exceptions import BackendCallError


# 用途：
# - 读取 MiniMax Token Plan API key，优先使用显式 api_key，其次使用环境变量和本地 key 文件
# 输入：
# - api_key: 配置中直接提供的 key
# - api_key_file: key 文件路径，默认相对当前运行目录
# 输出：
# - 可用于 Anthropic-compatible 请求的 API key 字符串
def _resolve_api_key(api_key: str = "", api_key_file: str = "") -> str:
    if api_key:
        return api_key.strip()

    env_key = os.environ.get("SLINKY_MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
    if env_key:
        return env_key.strip()

    if not api_key_file:
        return ""

    key_path = Path(api_key_file).expanduser()
    if not key_path.is_absolute():
        key_path = Path.cwd() / key_path
    try:
        return key_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# 用途：
# - 调用 MiniMax Token Plan 的 Anthropic-compatible messages API
# 输入：
# - model_name/prompt/system_prompt/temperature/timeout_seconds: 单次 LLM 调用参数
# 输出：
# - llm_tier 统一消费的 content、token_usage、raw_response 结果字典
class MiniMaxClient(BaseBackendClient, ApiBackendMixin):
    # 用途：
    # - 初始化 MiniMax Token Plan backend client
    # 输入：
    # - api_key/api_key_file/base_url/timeout_seconds/max_tokens/anthropic_version: backend 凭证和请求默认参数
    # 输出：
    # - 可被 llm_tier router 调用的 client 实例
    def __init__(
        self,
        api_key: str = "",
        api_key_file: str = "",
        base_url: str = "https://api.minimaxi.com/anthropic",
        timeout_seconds: int = 600,
        max_tokens: int = 32768,
        anthropic_version: str = "2023-06-01",
        **kwargs: Any,
    ) -> None:
        self._api_key = _resolve_api_key(api_key=api_key, api_key_file=api_key_file)
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens
        self._anthropic_version = anthropic_version

    @property
    # 用途：
    # - 返回 backend provider 注册名
    # 输入：
    # - 无
    # 输出：
    # - provider 名称 `minimax`
    def backend(self) -> str:
        return "minimax"

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
    # - 声明 MiniMax client 当前支持的 API model id
    # 输入：
    # - 无
    # 输出：
    # - 可用于 settings.json `model_key` 的模型列表
    def supported_models(self) -> list[str]:
        return ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "M2-her"]

    # 用途：
    # - 执行一次 MiniMax Anthropic-compatible messages 调用
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
        timeout_seconds: int = 600,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        started = time.time()
        url = f"{self._base_url}/v1/messages"
        payload: dict[str, Any] = {
            "model": model_name,
            "max_tokens": int(kwargs.get("max_tokens") or self._max_tokens),
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": self._anthropic_version,
        }

        request_timeout_seconds = int(timeout_seconds or self._timeout_seconds or 600)
        retry_deadline = self._api_retry_deadline(request_timeout_seconds)
        max_retry = 3
        for attempt in range(max_retry + 1):
            try:
                resp = self._post_json(url, payload, headers, self._remaining_api_timeout(retry_deadline, request_timeout_seconds))
                latency = (time.time() - started) * 1000
                content = self._extract_content(resp)
                usage = resp.get("usage", {})
                prompt_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                completion_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                return {
                    "ok": True,
                    "content": content,
                    "model_name": resp.get("model", model_name),
                    "latency_ms": latency,
                    "token_usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": int(usage.get("total_tokens") or prompt_tokens + completion_tokens),
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

    # 用途：
    # - 从 Anthropic-compatible content blocks 中抽取文本
    # 输入：
    # - resp: MiniMax messages API 响应
    # 输出：
    # - 拼接后的文本内容
    def _extract_content(self, resp: dict[str, Any]) -> str:
        blocks = resp.get("content", [])
        if isinstance(blocks, str):
            return blocks
        if not isinstance(blocks, list):
            return ""

        texts: list[str] = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
        return "\n".join(t for t in texts if t)


register_backend("minimax", MiniMaxClient)
