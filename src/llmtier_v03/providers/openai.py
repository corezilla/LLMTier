from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ..errors import ApiError
from .base import ProviderResult


class OpenAIProvider:
    def __init__(self, endpoint: str, secret_ref: str | None, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.secret_ref = secret_ref
        self.timeout = timeout

    def _secret(self) -> str | None:
        if not self.secret_ref:
            return None
        if self.secret_ref.startswith("env:"):
            return os.environ.get(self.secret_ref[4:])
        if self.secret_ref.startswith("file:"):
            return Path(self.secret_ref[5:]).read_text().strip()
        raise ApiError(503, "provider_secret_unavailable", "Unsupported provider secret reference")

    def _request(self, path: str, body: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        secret = self._secret()
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        req = urllib.request.Request(self.endpoint + path, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw), {k.lower(): v for k, v in response.headers.items()}
        except urllib.error.HTTPError as exc:
            retryable = exc.code in {408, 429, 500, 502, 503, 504}
            raise ApiError(exc.code, "provider_error", f"Provider returned HTTP {exc.code}", retryable=retryable) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError(503, "provider_unavailable", "Provider request failed", retryable=True) from exc

    def complete(self, model: str, request: dict[str, Any]) -> ProviderResult:
        upstream = dict(request)
        upstream["model"] = model
        upstream["stream"] = True
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        secret = self._secret()
        if secret: headers["Authorization"] = f"Bearer {secret}"
        req = urllib.request.Request(self.endpoint + "/v1/responses", data=json.dumps(upstream).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content_type = response.headers.get_content_type()
                if content_type != "text/event-stream": raise ApiError(502, "provider_contract_error", "Provider did not return Responses SSE")
                terminal = None
                for block in response.read().decode("utf-8").split("\n\n"):
                    for line in block.splitlines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            event = json.loads(line[6:])
                            if event.get("type") in {"response.completed", "response.failed", "response.incomplete"}: terminal = event.get("response")
                if not isinstance(terminal, dict) or not isinstance(terminal.get("output"), list): raise ApiError(502, "provider_contract_error", "Provider SSE has no valid terminal response")
                return ProviderResult(terminal["output"], terminal.get("usage"), response.headers.get("X-Request-ID"))
        except ApiError: raise
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, "provider_error", f"Provider returned HTTP {exc.code}", retryable=exc.code in {408,429,500,502,503,504}) from exc
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(503, "provider_unavailable", "Provider streaming request failed", retryable=True) from exc

    def embed(self, model: str, request: dict[str, Any]) -> dict[str, Any]:
        upstream = dict(request)
        upstream["model"] = model
        data, _ = self._request("/v1/embeddings", upstream)
        if data.get("object") != "list" or not isinstance(data.get("data"), list):
            raise ApiError(502, "provider_contract_error", "Provider returned an invalid Embeddings payload")
        return data

    def probe(self) -> bool:
        try:
            req = urllib.request.Request(self.endpoint + "/healthz", method="GET")
            with urllib.request.urlopen(req, timeout=min(self.timeout, 5.0)) as response:
                return 200 <= response.status < 300
        except Exception:
            return False
