from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from http_api.errors import ApiError
from .base import ProviderResult


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class OpenAIProvider:
    def __init__(self, endpoint: str, secret_ref: str | None, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.secret_ref = secret_ref
        self.timeout = timeout
        self._https = self.endpoint.lower().startswith("https://")
        self._ssl = _ssl_context() if self._https else None

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
        req.add_header("Connection", "close")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl) as response:
                raw = response.read()
                return json.loads(raw), {k.lower(): v for k, v in response.headers.items()}
        except urllib.error.HTTPError as exc:
            # E-INF-UPSTREAM: upstream 5xx surfaces as 503 provider_unavailable.
            if exc.code >= 500:
                raise ApiError(503, "provider_unavailable", f"Provider returned HTTP {exc.code}", retryable=True) from exc
            raise ApiError(exc.code, "provider_error", f"Provider returned HTTP {exc.code}", retryable=exc.code in {408, 429}) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError(503, "provider_unavailable", "Provider request failed", retryable=True) from exc

    def complete(self, model: str, request: dict[str, Any]) -> ProviderResult:
        upstream = dict(request)
        upstream["model"] = model
        upstream["stream"] = True
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        secret = self._secret()
        if secret: headers["Authorization"] = f"Bearer {secret}"
        req = urllib.request.Request(self.endpoint + "/responses", data=json.dumps(upstream).encode(), headers=headers, method="POST")
        # Disable HTTP/1.1 keep-alive: each provider call opens a fresh
        # connection. urllib's default HTTPS handler keeps a small per-thread
        # connection pool whose SSL state has been observed to intermittently
        # fail verification on reused sockets (CERTIFICATE_VERIFY_FAILED
        # with a perfectly valid CA chain). Forcing Connection: close makes
        # the failure mode deterministic and one-shot per request.
        req.add_header("Connection", "close")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl) as response:
                content_type = response.headers.get_content_type()
                if content_type != "text/event-stream": raise ApiError(502, "provider_contract_error", "Provider did not return Responses SSE")
                terminal = None
                terminal_type = None
                for block in response.read().decode("utf-8").split("\n\n"):
                    for line in block.splitlines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            event = json.loads(line[6:])
                            if event.get("type") in {"response.completed", "response.failed", "response.incomplete"}:
                                if terminal is not None:
                                    raise ApiError(502, "provider_contract_error", "Provider SSE has more than one terminal response")
                                terminal_type = event["type"]
                                terminal = event.get("response")
                if not isinstance(terminal, dict) or not isinstance(terminal.get("output"), list): raise ApiError(502, "provider_contract_error", "Provider SSE has no valid terminal response")
                expected_status = terminal_type.removeprefix("response.") if terminal_type else None
                if terminal.get("status") != expected_status:
                    raise ApiError(502, "provider_contract_error", "Provider terminal event and response status disagree")
                return ProviderResult(
                    terminal["output"],
                    terminal.get("usage"),
                    response.headers.get("X-Request-ID"),
                    status=terminal["status"],
                    error=terminal.get("error"),
                    incomplete_details=terminal.get("incomplete_details"),
                )
        except ApiError: raise
        except urllib.error.HTTPError as exc:
            # E-INF-UPSTREAM: upstream 5xx surfaces as 503 provider_unavailable.
            if exc.code >= 500:
                raise ApiError(503, "provider_unavailable", f"Provider returned HTTP {exc.code}", retryable=True) from exc
            raise ApiError(exc.code, "provider_error", f"Provider returned HTTP {exc.code}", retryable=exc.code in {408, 429}) from exc
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(503, "provider_unavailable", f"Provider streaming request failed: {type(exc).__name__}: {str(exc)[:80]}", retryable=True) from exc

    def embed(self, model: str, request: dict[str, Any]) -> dict[str, Any]:
        upstream = dict(request)
        upstream["model"] = model
        data, _ = self._request("/embeddings", upstream)
        if data.get("object") != "list" or not isinstance(data.get("data"), list):
            raise ApiError(502, "provider_contract_error", "Provider returned an invalid Embeddings payload")
        return data

    def probe(self) -> bool:
        try:
            headers = {"Accept": "application/json"}
            secret = self._secret()
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            req = urllib.request.Request(self.endpoint + "/models", headers=headers, method="GET")
            req.add_header("Connection", "close")
            with urllib.request.urlopen(req, timeout=min(self.timeout, 5.0), context=self._ssl) as response:
                if not 200 <= response.status < 300:
                    return False
                payload = json.loads(response.read())
                return payload.get("object") == "list" and isinstance(payload.get("data"), list)
        except Exception:
            return False

    def list_models(self) -> list[str]:
        headers = {"Accept": "application/json"}
        secret = self._secret()
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        req = urllib.request.Request(self.endpoint + "/models", headers=headers, method="GET")
        req.add_header("Connection", "close")
        with urllib.request.urlopen(req, timeout=min(self.timeout, 10.0), context=self._ssl) as response:
            payload = json.loads(response.read())
        return [m["id"] for m in payload.get("data", []) if isinstance(m.get("id"), str)]
