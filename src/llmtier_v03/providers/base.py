from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ProviderResult:
    output: list[dict[str, Any]]
    usage: dict[str, Any] | None
    provider_request_id: str | None = None
    status: str = "completed"
    error: dict[str, Any] | None = None
    incomplete_details: dict[str, Any] | None = None


class ProviderAdapter(Protocol):
    def complete(self, model: str, request: dict[str, Any]) -> ProviderResult: ...
    def embed(self, model: str, request: dict[str, Any]) -> dict[str, Any]: ...
    def probe(self) -> bool: ...
    def list_models(self) -> list[str]: ...
