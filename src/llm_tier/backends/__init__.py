from __future__ import annotations

import importlib
from typing import Any

from llm_tier.backends.base import BaseBackendClient

_registry: dict[str, type[BaseBackendClient]] = {}
_registry_loaded = False


def register_backend(name: str, cls: type[BaseBackendClient]) -> None:
    _registry[name] = cls


def get_backend_client(name: str, **init_kwargs: Any) -> BaseBackendClient | None:
    cls = _registry.get(name)
    if cls is None:
        return None
    return cls(**init_kwargs)


def list_backends() -> list[str]:
    return list(_registry.keys())


# 用途：
# - 显式加载所有内置 backend 模块，确保 provider 注册不依赖偶然 import 副作用
# 输入：
# - 无；使用 llm_tier 内置 backend 模块清单
# 输出：
# - 无；模块加载后通过 register_backend 写入当前 registry
def ensure_backend_registry_loaded() -> None:
    global _registry_loaded
    if _registry_loaded:
        return
    _registry_loaded = True
    for module_name in (
        "llm_tier.backends.claude",
        "llm_tier.backends.codex",
        "llm_tier.backends.debug",
        "llm_tier.backends.deepseek",
        "llm_tier.backends.minimax",
        "llm_tier.backends.mlexp",
        "llm_tier.backends.opencode",
        "llm_tier.backends.opencode_go",
        "llm_tier.backends.volc",
        "llm_tier.backends.xfyun",
    ):
        importlib.import_module(module_name)


ensure_backend_registry_loaded()
