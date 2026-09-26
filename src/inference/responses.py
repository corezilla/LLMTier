from __future__ import annotations

import os
import time
import uuid
from typing import Any

from http_api.errors import ApiError, require
from .providers.local import LocalProvider
from .providers.openai import OpenAIProvider
from management.registry import Registry
from .routing import Router
from .usage import UsageRecorder


class ResponsesService:
    def __init__(self, registry: Registry, router: Router, usage: UsageRecorder, diagnostics=None):
        self.registry, self.router, self.usage, self.diagnostics = registry, router, usage, diagnostics
        self._test_adapter = None

    def _adapter(self, candidate):
        if self._test_adapter is not None:
            return self._test_adapter
        slow = os.environ.get("LLMTIER_SLOW_ADAPTER_DELAY")
        if slow:
            from .providers.base import ProviderResult
            delay = float(slow)
            class SlowAdapter:
                def complete(self, model, request):
                    time.sleep(delay)
                    return ProviderResult(
                        [{"type": "message", "id": "msg_1", "role": "assistant", "status": "completed",
                          "content": [{"type": "output_text", "text": "ok", "annotations": []}]}],
                        {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
                        status="completed",
                        incomplete_details=None
                    )
                def embed(self, model, request):
                    raise NotImplementedError
                def probe(self):
                    return True
            return SlowAdapter()
        row = self.registry.store.one("SELECT secret_ref FROM providers WHERE id=?", (candidate.provider_id,))
        cls = LocalProvider if candidate.kind == "local" else OpenAIProvider
        profile = self.registry.store.one("SELECT connect_timeout_ms,stream_idle_timeout_ms FROM deployment_runtime_profiles WHERE deployment_id=?", (candidate.deployment_id,))
        return cls(
            candidate.endpoint,
            row["secret_ref"] if row else None,
            connect_timeout_s=(profile["connect_timeout_ms"] if profile else 30000) / 1000.0,
            stream_idle_timeout_s=(profile["stream_idle_timeout_ms"] if profile else 60000) / 1000.0,
        )

    def create(self, principal: str, request_id: str, body: dict[str, Any], diagnostics=None,
               correlation_id: str | None = None, out: dict[str, Any] | None = None) -> dict[str, Any]:
        diag = diagnostics if diagnostics is not None else self.diagnostics
        t0 = time.monotonic()

        def _trace(stage: str, detail: dict[str, Any] | None = None) -> None:
            if diag: diag.record_trace(request_id, stage, detail, correlation_id)

        def _stats(status: int | None, deployment_id: str | None = None) -> None:
            if diag: diag.record_latency(deployment_id, body.get("model"), status, (time.monotonic() - t0) * 1000)

        try:
            require({"model", "input", "stream", "store"} <= set(body), 400, "invalid_request", "model, input, stream, and store are required")
            require(body.get("stream") is True and body.get("store") is False, 400, "unsupported_request", "Only stream=true and store=false are supported")
            forbidden = {"prompt_cache_key", "prompt_cache_retention", "previous_response_id"}
            require(not (forbidden & set(body)), 400, "unsupported_field", "Unsupported provider continuation or cache field")
            model = body["model"]
            try:
                caps = self.registry.get_service_level(model)[0]["capabilities"]
            except ApiError as exc:
                if exc.status == 404:
                    raise ApiError(404, "model_not_found", "Model not found") from exc
                raise
            require(caps.get("responses") is True, 400, "unsupported_model", "Selected model does not support Responses", "model")
        except ApiError as exc:
            _trace("validated", {"ok": False, "code": exc.code, "status": exc.status}); _stats(exc.status)
            raise
        _trace("validated", {"ok": True})
        self.usage.authorize_dispatch(principal, request_id, model, "/v1/responses")
        admitted = False
        try:
            with self.router.admit(model) as candidate:
                admitted = True
                if out is not None: out.update({"deployment_id": candidate.deployment_id, "backend_model": candidate.backend_model})
                _trace("routed", {"deployment_id": candidate.deployment_id, "provider_id": candidate.provider_id})
                injection = diag.enabled_injection(candidate.deployment_id) if diag else None
                if injection:
                    kind = injection["injection_type"]
                    if kind in ("fault_502", "fault_503"):
                        status = injection["fault_status"] or (502 if kind == "fault_502" else 503)
                        code = "provider_failure" if kind == "fault_502" else "provider_unavailable"
                        fault = ApiError(status, code, injection["fault_body"] or "injected upstream failure", retryable=True)
                        fault.piko_injected = {"deployment_id": candidate.deployment_id, "type": kind}
                        _stats(status, candidate.deployment_id); raise fault
                    if kind == "rate_limit":
                        retry = injection["retry_after_sec"] or 1
                        limit = ApiError(429, "rate_limit_exceeded", "Injected rate limit", retryable=True, headers={"Retry-After": str(retry)})
                        limit.piko_injected = {"deployment_id": candidate.deployment_id, "type": kind}
                        _stats(429, candidate.deployment_id); raise limit
                    if kind == "delay":
                        time.sleep((injection["delay_ms"] or 0) / 1000)
                self.usage.bind_backend(principal, request_id, candidate.provider_id, candidate.deployment_id)
                provider_row = self.registry.store.one("SELECT endpoint FROM providers WHERE id=?", (candidate.provider_id,))
                upstream_url = provider_row["endpoint"] if provider_row else candidate.provider_id
                _trace("upstream_started", {"deployment_id": candidate.deployment_id, "upstream_url": upstream_url})
                upstream_started = time.monotonic()
                try:
                    result = self._adapter(candidate).complete(candidate.backend_model, body)
                except Exception as exc:
                    latency = (time.monotonic() - upstream_started) * 1000
                    if diag:
                        diag.capture_snapshot(request_id, candidate.deployment_id, model, upstream_url, candidate.backend_model, None, latency, str(exc))
                        diag.record_trace(request_id, "upstream_ended", {"deployment_id": candidate.deployment_id, "status": None})
                    _stats(503, candidate.deployment_id)
                    raise
                latency = (time.monotonic() - upstream_started) * 1000
                if diag:
                    snap_id = diag.capture_snapshot(request_id, candidate.deployment_id, model, upstream_url, candidate.backend_model, 200, latency, None)
                    diag.record_trace(request_id, "upstream_ended", {"deployment_id": candidate.deployment_id, "status": 200, "snapshot_id": snap_id})
                _stats(200, candidate.deployment_id)
                if result.provider_request_id is not None:
                    self.usage.record_provider_request_id(principal, request_id, result.provider_request_id)
            self.usage.finish(principal, request_id, result.usage)
            return {
                "id": f"resp_{uuid.uuid4().hex}",
                "object": "response",
                "created_at": int(time.time()),
                "status": result.status,
                "model": model,
                "output": result.output,
                "usage": result.usage,
                "error": result.error,
                "incomplete_details": result.incomplete_details,
            }
        except Exception as exc:
            # E-INF-ADMIT: admission rejection never reached the backend -> no usage side effect.
            if admitted:
                source = "injected" if getattr(exc, "piko_injected", False) else None
                self.usage.finish(principal, request_id, None, source)
            raise
