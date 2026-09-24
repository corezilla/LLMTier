from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApiError(Exception):
    status: int
    code: str
    message: str
    param: str | None = None
    retryable: bool = False
    headers: dict[str, str] | None = None
    extra: dict[str, Any] | None = None

    def envelope(self) -> dict[str, Any]:
        err = {
            "message": self.message,
            "type": "request_error" if self.status < 500 else "server_error",
            "code": self.code,
            "param": self.param,
            "retryable": self.retryable,
        }
        if self.extra:
            err.update(self.extra)
        return {"error": err}


def require(condition: bool, status: int, code: str, message: str, param: str | None = None) -> None:
    if not condition:
        raise ApiError(status, code, message, param)
