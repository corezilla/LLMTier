from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseBackendClient(ABC):
    @property
    @abstractmethod
    def backend(self) -> str:
        ...

    @property
    @abstractmethod
    def backend_type(self) -> str:
        ...

    @abstractmethod
    def supported_models(self) -> list[str]:
        ...

    @abstractmethod
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
        ...
