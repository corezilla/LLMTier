from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backends import register_backend
from backends.deepseek import _api_call
from backends.base import BaseBackendClient
from backends.api_backend import ApiBackendMixin


# 用途：
# - 封装 OpenCode Go OpenAI-compatible API backend
# 输入：
# - api_key/api_key_file/base_url/timeout_seconds: backend API 认证和请求配置
# 输出：
# - llm_tier 可注册和调度的 OpenCode Go API client
class OpenCodeGoClient(BaseBackendClient, ApiBackendMixin):
    # 用途：
    # - 初始化 OpenCode Go API client，并解析显式 key、key 文件或环境变量
    # 输入：
    # - api_key/api_key_file/base_url/timeout_seconds/kwargs: backend 配置参数
    # 输出：
    # - 无返回值，初始化实例状态
    def __init__(
        self,
        api_key: str = "",
        api_key_file: str = "",
        base_url: str = "",
        timeout_seconds: int = 600,
        **kwargs: Any,
    ) -> None:
        self._api_key = (
            str(api_key or "").strip()
            or _read_secret_file(api_key_file)
            or os.environ.get("LLMTIER_OPENCODE_GO_API_KEY", "").strip()
        )
        self._base_url = str(
            base_url
            or os.environ.get("LLMTIER_OPENCODE_GO_BASE_URL")
            or "https://opencode.ai/zen/go/v1"
        ).rstrip("/")
        self._timeout_seconds = int(timeout_seconds or 600)

    @property
    def backend(self) -> str:
        return "opencode_go"

    @property
    def backend_type(self) -> str:
        return "API"

    # 用途：
    # - 声明 OpenCode Go 当前配置支持的模型 ID
    # 输入：
    # - 无
    # 输出：
    # - 可用于 settings.json `model_key` 的模型列表
    def supported_models(self) -> list[str]:
        return ["deepseek-v4-flash", "deepseek-v4-pro"]

    # 用途：
    # - 为 OpenCode Go API 请求补充浏览器/CLI 常见 header，避免 provider 网关拒绝 Python 默认 UA
    # 输入：
    # - url/payload/headers/timeout: JSON POST 请求上下文
    # 输出：
    # - provider 返回的 JSON payload
    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
    ) -> dict[str, Any]:
        enriched_headers = dict(headers)
        enriched_headers.setdefault("Accept", "application/json")
        enriched_headers.setdefault("User-Agent", "Slinky llm_tier/1.0")
        return super()._post_json(url, payload, enriched_headers, timeout)

    # 用途：
    # - 执行一次 OpenAI-compatible chat completions 调用
    # 输入：
    # - model_name/prompt/system_prompt/temperature/timeout_seconds/metadata/kwargs: 单次请求参数
    # 输出：
    # - llm_tier 统一格式的调用结果字典
    def call(
        self,
        model_name: str = "",
        prompt: str = "",
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = 600,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return _api_call(
            self,
            model_name,
            prompt,
            system_prompt,
            temperature,
            timeout_seconds or self._timeout_seconds,
            self._base_url,
            self._api_key,
        )


# 用途：
# - 读取 API key 文件并兼容 workspace 相对路径
# 输入：
# - path_value: settings.json 中的 api_key_file
# 输出：
# - 文件首行 key；不可读时返回空字符串
def _read_secret_file(path_value: str) -> str:
    raw_path = str(path_value or "").strip()
    if not raw_path:
        return ""
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        return candidate.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


register_backend("opencode_go", OpenCodeGoClient)
