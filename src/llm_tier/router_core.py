from __future__ import annotations

import re
import time
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from llm_tier.backends import get_backend_client
from llm_tier.concurrency import BackendConcurrencyManager
from llm_tier.exceptions import AllModelsExhaustedError, BackendCallError, QuotaExhaustedError
from llm_tier.quota_manager import QuotaManager
from llm_tier.redaction import redact_sensitive_text, redact_sensitive_value
from llm_tier.tier_config import TierConfig
from llm_tier.tier_model import (
    TierCallResult,
    TierModel,
    backend_call_model_name,
    backend_client_name,
    backend_readable_label,
)

DEFAULT_MAX_OUTPUT_TOKENS = 32768
UPSHIFT_TARGET_BY_TIER = {
    "Associate": "Worker",
    "Worker": "Junior",
    "Junior": "Senior",
}
TraceHook = Callable[[str, str, str, dict[str, Any]], None]


# 用途：
# - 将 stage/phase/task/stem 片段转换为安全路径名
# 输入：
# - value: 原始路径片段
# 输出：
# - 仅包含字母、数字、下划线、点和连字符的路径片段
def _safe_path_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return normalized.strip("._-")


# 用途：
# - 判断 backend 输出是否打满 max_tokens，打满时按截断失败处理
# 输入：
# - token_usage/max_tokens/backend/model_name: backend 返回用量和本次请求输出上限
# 输出：
# - 截断错误信息；未截断时返回空字符串
def _completion_truncation_error(
    *,
    token_usage: dict[str, Any],
    max_tokens: int,
    backend: str,
    model_name: str,
) -> str:
    completion_tokens = int((token_usage or {}).get("completion_tokens") or 0)
    if max_tokens <= 0 or completion_tokens < max_tokens:
        return ""
    return (
        "completion_truncated: "
        f"completion_tokens={completion_tokens}, "
        f"max_tokens={max_tokens}, "
        f"backend={backend}, model={model_name}"
    )


# 用途：
# - 根据 role 到 tier/backend 的配置执行 LLM 路由、fallback、quota 与并发控制
# 输入：
# - TierConfig、runtime state_dir 和可选 trace hook
# 输出：
# - call 返回 TierCallResult 和 stats event
class LLMRouter:
    # 用途：
    # - 初始化 router 的配置、quota、并发池、runtime 状态和 trace hook
    # 输入：
    # - tier_config/state_dir/trace_hook: tier 配置、状态目录和可选事件回调
    # 输出：
    # - 无；构建可复用 router 实例
    def __init__(
        self,
        tier_config: TierConfig,
        state_dir: str = "",
        trace_hook: TraceHook | None = None,
    ) -> None:
        self._config = tier_config
        self._quota = QuotaManager(tier_config, state_dir=state_dir)
        self._trace_hook = trace_hook
        self._concurrency = self._build_concurrency()
        breaker_config = self._config.get_breaker_config()
        self._failure_threshold = int(breaker_config.get("failure_threshold") or 3)
        self._weighted_cursor_by_tier: dict[str, int] = {}
        self._weight_state_lock = threading.Lock()
        self._admin_state_by_backend: dict[str, bool] = {
            self.backend_key(model.backend, model.model_name, tier_name=str(tier_name), account=model.account): bool(model.enabled)
            for tier_name in self._config._config.get("llm_tiers", {})
            for model in self._config.get_tier_models(str(tier_name))
        }
        self._runtime_status_by_backend: dict[str, str] = {}
        self._runtime_error_by_backend: dict[str, dict[str, Any]] = {}
        self._failure_count_by_backend: dict[str, int] = {}
        self._upshift_count = 0
        self._state_lock = threading.Lock()

    # 用途：
    # - 将 router 内部调度事件转交给 tier server 的 runtime trace writer
    # 输入：
    # - event_type/level/event/fields: 事件类别、级别、事件名和结构化字段
    # 输出：
    # - 无；trace hook 失败时静默跳过，避免影响 LLM 调用主路径
    def _trace(
        self,
        event_type: str,
        level: str,
        event: str,
        fields: dict[str, Any] | None = None,
    ) -> None:
        if self._trace_hook is None:
            return
        try:
            self._trace_hook(event_type, level, event, dict(fields or {}))
        except Exception:
            return

    # 用途：
    # - 根据每个 llm_accounts 配置构建账号级并发管理器
    # 输入：
    # - 无；读取当前 TierConfig 中的 llm_tiers
    # 输出：
    # - 使用 account identity 控制并发、backend identity 记录运行数的 BackendConcurrencyManager
    def _build_concurrency(self) -> BackendConcurrencyManager:
        account_configs: dict[str, dict[str, Any]] = {}
        for account in self._config.get_accounts():
            account_configs[account.account_id] = self._config.get_account_concurrency(account.account_id)
        return BackendConcurrencyManager(account_configs)

    # 用途：
    # - 按 role 配置选择 backend 并执行一次 LLM 调用，失败时在同一 tier 内 fallback
    # 输入：
    # - role_name/prompt/temperature/timeout_seconds/metadata: 调用上下文
    # 输出：
    # - TierCallResult 与可写入 StatsCollector 的 stats event
    def call(
        self,
        role_name: str,
        prompt: str,
        temperature: float = 0.0,
        timeout_seconds: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> tuple[TierCallResult, dict[str, Any]]:
        trace_context = dict(metadata or {})
        trace_base = {
            "job_id": str(trace_context.get("job_id") or ""),
            "client_request_id": str(trace_context.get("client_request_id") or ""),
            "role_name": role_name,
            "project_name": str(trace_context.get("project_name") or ""),
            "stage_name": str(trace_context.get("stage_name") or ""),
            "phase_name": str(trace_context.get("phase_name") or ""),
            "task_id": str(trace_context.get("task_id") or ""),
            "task_key": str(trace_context.get("task_key") or ""),
            "prompt_chars": len(str(prompt or "")),
        }
        self._trace("router", "debug", "router.call.start", trace_base)

        tier_name = self._config.get_tier_for_role(role_name)
        if not tier_name:
            self._trace(
                "router",
                "warn",
                "router.call.finish",
                {**trace_base, "ok": False, "error_code": 1002, "error_message": f"role_not_mapped: {role_name}"},
            )
            return (
                TierCallResult(
                    ok=False, content="", backend="", model_name="", backend_type="",
                    tier="", tier_priority=0, latency_ms=0, token_usage={},
                    error_code=1002, error_message=f"role_not_mapped: {role_name}",
                ),
                {"tier": "", "error_code": 1002},
            )

        tier_name = self._resolve_upshift_tier(
            tier_name=tier_name,
            prompt=prompt,
            trace_base=trace_base,
        )
        models = self._config.get_tier_models(tier_name)
        if not models:
            self._trace(
                "router",
                "warn",
                "router.call.finish",
                {**trace_base, "tier": tier_name, "ok": False, "error_code": 1001},
            )
            return (
                TierCallResult(
                    ok=False, content="", backend="", model_name="", backend_type="",
                    tier=tier_name, tier_priority=0, latency_ms=0, token_usage={},
                    error_code=1001, error_message=f"tier_config_missing: {tier_name}",
                ),
                {"tier": tier_name, "error_code": 1001},
            )

        fallback_count = 0
        last_error: str = ""
        last_error_code: int = 1005
        last_raw_response: dict[str, Any] = {}
        last_failure: dict[str, Any] = {}
        failed_backend_keys: set[str] = set()
        busy_backend_keys: set[str] = set()
        busy_retry_after_seconds: float = 0.5

        for _ in range(len(models)):
            selected, selected_backend_key, selected_account_key, busy_retry_after_seconds = self._select_and_acquire_backend(
                models,
                failed_backend_keys,
                tier_name=tier_name,
                busy_backend_keys=busy_backend_keys,
            )
            if selected is None:
                break

            current_exclusion = self._backend_exclusion_reason(
                selected,
                tier_name=tier_name,
                failed_backend_keys=failed_backend_keys,
                busy_backend_keys=busy_backend_keys,
            )
            if current_exclusion != "available":
                self._concurrency.release(selected_backend_key, selected_account_key)
                failed_backend_keys.add(selected_backend_key)
                last_error = f"backend became unavailable after selection: {current_exclusion}"
                continue

            selected_fields = {
                **trace_base,
                "tier": tier_name,
                "backend_key": selected_backend_key,
                "account": selected_account_key,
                "backend": selected.backend,
                "model_name": selected.model_name,
                "model_key": selected.model_key,
                "provider": selected.provider,
                "backend_type": selected.backend_type,
                "fallback_count": fallback_count,
            }
            self._trace("router", "debug", "router.backend.selected", selected_fields)
            start_ts = time.time()
            try:
                creds = self._get_backend_credentials(
                    selected.backend,
                    selected.provider,
                    selected.model_name,
                    selected.model_key,
                    selected.account,
                )
                context_error = self._context_limit_error(selected, prompt, creds)
                if context_error:
                    self._concurrency.release(selected_backend_key, selected_account_key)
                    self._trace(
                        "backend",
                        "warn",
                        "backend.context_limit",
                        {**selected_fields, **dict(context_error or {})},
                    )
                    token_usage = {
                        "prompt_tokens": int(context_error["estimated_prompt_tokens"]),
                        "completion_tokens": 0,
                        "total_tokens": int(context_error["estimated_total_tokens"]),
                    }
                    return (
                        TierCallResult(
                            ok=False,
                            content="",
                            backend=selected.backend,
                            model_name=selected.model_name,
                            backend_type=selected.backend_type,
                            tier=tier_name,
                            tier_priority=0,
                            latency_ms=0,
                            token_usage=token_usage,
                            account=selected.account,
                            error_code=1006,
                            error_message=str(context_error["message"]),
                            is_fallback=fallback_count > 0,
                            fallback_count=fallback_count,
                        ),
                        self._build_stats_event(
                            tier_name=tier_name,
                            backend=selected.backend,
                            account=selected.account,
                            backend_type=selected.backend_type,
                            model=selected.model_name,
                            ok=False,
                            latency_ms=0,
                            token_usage=token_usage,
                            is_fallback=fallback_count > 0,
                            fallback_count=fallback_count,
                        ),
                    )
                client_name = backend_client_name(selected)
                client = get_backend_client(client_name, **creds)
                if client is None:
                    self._concurrency.release(selected_backend_key, selected_account_key)
                    self._trace("backend", "warn", "backend.client_missing", {**selected_fields, "client": client_name})
                    failed_backend_keys.add(selected_backend_key)
                    fallback_count += 1
                    self._record_unhealthy_failure(
                        selected.backend,
                        selected.model_name,
                        "no backend client",
                        tier_name=tier_name,
                        account=selected.account,
                        source="call",
                    )
                    continue

                max_tokens = self._max_tokens_for_model(selected, creds)
                timeout_value = timeout_seconds or selected.timeout_seconds or 600
                self._trace(
                    "backend",
                    "info",
                    "backend.call.start",
                    {
                        **selected_fields,
                        "timeout_seconds": int(timeout_value),
                        "max_tokens": int(max_tokens),
                    },
                )
                result = client.call(
                    model_name=backend_call_model_name(selected),
                    prompt=prompt,
                    temperature=temperature,
                    timeout_seconds=timeout_value,
                    metadata={
                        **(metadata or {}),
                        "role_name": role_name,
                        "tier_name": tier_name,
                        "backend": selected.backend,
                        "account": selected.account,
                        "model_name": selected.model_name,
                    },
                    max_tokens=max_tokens,
                )
                latency = (time.time() - start_ts) * 1000
                token_usage = dict(result.get("token_usage") or {})
                self._trace(
                    "backend",
                    "info",
                    "backend.call.finish",
                    {
                        **selected_fields,
                        "ok": True,
                        "latency_ms": latency,
                        "prompt_tokens": int(token_usage.get("prompt_tokens") or 0),
                        "completion_tokens": int(token_usage.get("completion_tokens") or 0),
                        "total_tokens": int(token_usage.get("total_tokens") or 0),
                    },
                )
                truncation_error = _completion_truncation_error(
                    token_usage=token_usage,
                    max_tokens=max_tokens,
                    backend=selected.backend,
                    model_name=selected.model_name,
                )
                if truncation_error:
                    self._concurrency.release(selected_backend_key, selected_account_key)
                    self._trace(
                        "backend",
                        "warn",
                        "backend.completion_truncated",
                        {**selected_fields, "latency_ms": latency, "error_message": truncation_error},
                    )
                    self._record_unhealthy_failure(
                        selected.backend,
                        selected.model_name,
                        truncation_error,
                        tier_name=tier_name,
                        account=selected.account,
                        source="call",
                    )
                    failed_backend_keys.add(selected_backend_key)
                    fallback_count += 1
                    last_error = truncation_error
                    last_error_code = 1007
                    last_raw_response = dict(result.get("raw_response", {}) or {})
                    last_failure = {
                        "backend": selected.backend,
                        "model_name": selected.model_name,
                        "backend_type": selected.backend_type,
                        "account": selected.account,
                        "latency_ms": latency,
                        "token_usage": token_usage,
                    }
                    continue

                if str(result.get("content") or "") == "":
                    empty_response_error = "empty_response: backend returned no usable response content"
                    self._concurrency.release(selected_backend_key, selected_account_key)
                    self._trace(
                        "backend",
                        "warn",
                        "backend.empty_response",
                        {**selected_fields, "latency_ms": latency, "error_message": empty_response_error},
                    )
                    self._record_unhealthy_failure(
                        selected.backend,
                        selected.model_name,
                        empty_response_error,
                        tier_name=tier_name,
                        account=selected.account,
                        source="call",
                    )
                    return (
                        TierCallResult(
                            ok=False,
                            content="",
                            backend=selected.backend,
                            model_name=selected.model_name,
                            backend_type=selected.backend_type,
                            tier=tier_name,
                            tier_priority=0,
                            latency_ms=latency,
                            token_usage=token_usage,
                            account=selected.account,
                            is_fallback=fallback_count > 0,
                            fallback_count=fallback_count,
                            raw_response=result.get("raw_response", {}),
                            error_code=1005,
                            error_message=empty_response_error,
                        ),
                        self._build_stats_event(
                            tier_name=tier_name,
                            backend=selected.backend,
                            account=selected.account,
                            backend_type=selected.backend_type,
                            model=selected.model_name,
                            ok=False,
                            latency_ms=latency,
                            token_usage=token_usage,
                            is_fallback=fallback_count > 0,
                            fallback_count=fallback_count,
                        ),
                    )

                tier_result = TierCallResult(
                    ok=True,
                    content=result.get("content", ""),
                    backend=selected.backend,
                    model_name=selected.model_name,
                    backend_type=selected.backend_type,
                    tier=tier_name,
                    tier_priority=0,
                    latency_ms=latency,
                    token_usage=result.get("token_usage", {}),
                    account=selected.account,
                    is_fallback=fallback_count > 0,
                    fallback_count=fallback_count,
                    raw_response=result.get("raw_response", {}),
                )
                stats_event = self._build_stats_event(
                    tier_name=tier_name,
                    backend=selected.backend,
                    account=selected.account,
                    backend_type=selected.backend_type,
                    model=selected.model_name,
                    ok=True,
                    latency_ms=latency,
                    token_usage=result.get("token_usage", {}),
                    is_fallback=fallback_count > 0,
                    fallback_count=fallback_count,
                )
                stats_event["prompt_chars"] = len(str(prompt or ""))
                self._concurrency.release(selected_backend_key, selected_account_key)
                self._record_backend_success(
                    selected.backend,
                    selected.model_name,
                    tier_name=tier_name,
                    account=selected.account,
                )
                self._trace(
                    "router",
                    "debug",
                    "router.call.finish",
                    {
                        **selected_fields,
                        "ok": True,
                        "latency_ms": latency,
                        "fallback_count": fallback_count,
                    },
                )
                return tier_result, stats_event

            except QuotaExhaustedError as e:
                self._concurrency.release(selected_backend_key, selected_account_key)
                safe_error_message = redact_sensitive_text(e)
                self._trace(
                    "backend",
                    "warn",
                    "backend.call.error",
                    {**selected_fields, "error_type": "quota", "error_message": safe_error_message},
                )
                self._quota.mark_exhausted(selected.backend, selected.model_name, safe_error_message)
                failed_backend_keys.add(selected_backend_key)
                fallback_count += 1
                last_error = "quota_exhausted"
                last_error_code = 1005
                last_failure = {
                    "backend": selected.backend,
                    "model_name": selected.model_name,
                    "backend_type": selected.backend_type,
                    "account": selected.account,
                    "latency_ms": (time.time() - start_ts) * 1000,
                    "token_usage": self._estimated_prompt_token_usage(prompt),
                }
                self.set_backend_runtime_status(
                    selected.backend,
                    selected.model_name,
                    "exhausted",
                    tier_name=tier_name,
                    account=selected.account,
                )
                self._record_backend_error(
                    selected.backend,
                    selected.model_name,
                    safe_error_message,
                    tier_name=tier_name,
                    account=selected.account,
                    failure_type="quota",
                )
                continue

            except BackendCallError as e:
                self._concurrency.release(selected_backend_key, selected_account_key)
                safe_error_message = redact_sensitive_text(e)
                self._trace(
                    "backend",
                    "warn",
                    "backend.call.error",
                    {**selected_fields, "error_type": "backend", "error_message": safe_error_message},
                )
                last_raw_response = redact_sensitive_value(dict(getattr(e, "raw_response", {}) or {}))
                client_error_message = self._client_request_error_message(safe_error_message)
                if client_error_message:
                    token_usage = self._estimated_prompt_token_usage(prompt)
                    return (
                        TierCallResult(
                            ok=False,
                            content="",
                            backend=selected.backend,
                            model_name=selected.model_name,
                            backend_type=selected.backend_type,
                            tier=tier_name,
                            tier_priority=0,
                            latency_ms=0,
                            token_usage=token_usage,
                            account=selected.account,
                            error_code=1008,
                            error_message=client_error_message,
                            is_fallback=fallback_count > 0,
                            fallback_count=fallback_count,
                            raw_response=last_raw_response,
                        ),
                        self._build_stats_event(
                            tier_name=tier_name,
                            backend=selected.backend,
                            account=selected.account,
                            backend_type=selected.backend_type,
                            model=selected.model_name,
                            ok=False,
                            latency_ms=0,
                            token_usage=token_usage,
                            is_fallback=fallback_count > 0,
                            fallback_count=fallback_count,
                        ),
                    )
                failed_backend_keys.add(selected_backend_key)
                fallback_count += 1
                last_error = safe_error_message
                last_error_code = 1005
                last_failure = {
                    "backend": selected.backend,
                    "model_name": selected.model_name,
                    "backend_type": selected.backend_type,
                    "account": selected.account,
                    "latency_ms": (time.time() - start_ts) * 1000,
                    "token_usage": self._estimated_prompt_token_usage(prompt),
                }
                self._record_unhealthy_failure(
                    selected.backend,
                    selected.model_name,
                    safe_error_message,
                    tier_name=tier_name,
                    account=selected.account,
                    source="call",
                )
                continue

            except Exception:
                self._concurrency.release(selected_backend_key, selected_account_key)
                self._trace(
                    "backend",
                    "error",
                    "backend.call.error",
                    {**selected_fields, "error_type": "unexpected", "error_message": "unexpected_error"},
                )
                failed_backend_keys.add(selected_backend_key)
                fallback_count += 1
                last_error = "unexpected_error"
                last_error_code = 1005
                last_failure = {
                    "backend": selected.backend,
                    "model_name": selected.model_name,
                    "backend_type": selected.backend_type,
                    "account": selected.account,
                    "latency_ms": (time.time() - start_ts) * 1000,
                    "token_usage": self._estimated_prompt_token_usage(prompt),
                }
                self._record_unhealthy_failure(
                    selected.backend,
                    selected.model_name,
                    "unexpected_error",
                    tier_name=tier_name,
                    account=selected.account,
                    source="call",
                )
                continue

        selection_debug = self._selection_debug_summary(
            models,
            failed_backend_keys=failed_backend_keys,
            busy_backend_keys=busy_backend_keys,
            tier_name=tier_name,
        )
        transient_busy = self._selection_has_transient_busy(selection_debug)
        error_code = last_error_code
        if transient_busy or busy_backend_keys:
            error_msg = "all_backends_busy"
        else:
            error_msg = last_error if last_error and last_error != "quota_exhausted" else "all_backends_unavailable"
        if error_msg == "all_backends_unavailable" and selection_debug:
            error_msg = f"all_backends_unavailable: {selection_debug}"
        if error_msg == "all_backends_busy" and selection_debug:
            error_msg = f"all_backends_busy: {selection_debug}"
        raw_response = {"retry_after_seconds": busy_retry_after_seconds}
        if selection_debug:
            raw_response["selection_debug"] = selection_debug
        if last_raw_response:
            raw_response["last_backend_raw_response"] = last_raw_response
        self._trace(
            "router",
            "warn",
            "router.call.finish",
            {
                **trace_base,
                "tier": tier_name,
                "ok": False,
                "error_code": error_code,
                "error_message": error_msg,
                "selection_debug": selection_debug,
                "retry_after_seconds": round(float(busy_retry_after_seconds), 3),
                "fallback_count": fallback_count,
            },
        )
        return (
            TierCallResult(
                ok=False,
                content="",
                backend=str(last_failure.get("backend") or ""),
                model_name=str(last_failure.get("model_name") or ""),
                backend_type=str(last_failure.get("backend_type") or ""),
                tier=tier_name,
                tier_priority=0,
                latency_ms=float(last_failure.get("latency_ms") or 0),
                token_usage=dict(last_failure.get("token_usage") or {}),
                account=str(last_failure.get("account") or ""),
                is_fallback=fallback_count > 0,
                fallback_count=fallback_count,
                raw_response=raw_response,
                error_code=error_code, error_message=error_msg,
            ),
            self._build_stats_event(
                tier_name=tier_name,
                backend=str(last_failure.get("backend") or ""),
                account=str(last_failure.get("account") or ""),
                backend_type=str(last_failure.get("backend_type") or ""),
                model=str(last_failure.get("model_name") or ""),
                ok=False,
                latency_ms=float(last_failure.get("latency_ms") or 0),
                token_usage=dict(last_failure.get("token_usage") or {}),
                is_fallback=fallback_count > 0, fallback_count=fallback_count,
                selection_debug=selection_debug,
            ),
        )

    # 用途：
    # - 按 enabled、quota、runtime 状态、失败集合、配置顺序和 weight 选择 backend，并原子占用并发槽
    # 输入：
    # - models/failed_backend_keys/tier_name/busy_backend_keys: 当前 Tier 候选和请求内排除集合
    # 输出：
    # - 已占用 account 槽位的 TierModel、backend key、account key 和下一次 busy retry 建议秒数
    def _select_and_acquire_backend(
        self,
        models: list[TierModel],
        failed_backend_keys: set[str] | None = None,
        tier_name: str = "",
        busy_backend_keys: set[str] | None = None,
    ) -> tuple[TierModel | None, str, str, float]:
        # 用途：
        # - 生成当前调度使用的 backend identity
        # 输入：
        # - model: 候选 TierModel
        # 输出：
        # - `tier:account:model_name`
        def backend_identity(model: TierModel) -> str:
            return self.backend_key(model.backend, model.model_name, tier_name=tier_name, account=model.account)

        available = [
            m for m in models
            if not self._quota.is_exhausted(m.backend, m.model_name)
            and str(m.account or "").strip()
            and self.is_backend_enabled(m.backend, m.model_name, tier_name=tier_name, account=m.account)
            and self.backend_routable(m.backend, m.model_name, tier_name=tier_name, account=m.account)
            and (failed_backend_keys is None or backend_identity(m) not in failed_backend_keys)
            and (busy_backend_keys is None or backend_identity(m) not in busy_backend_keys)
        ]
        if not available:
            return None, "", "", 0.5
        return self._select_and_acquire_weighted_backend(
            tier_name,
            available,
            busy_backend_keys=busy_backend_keys,
        )

    # 用途：
    # - 解释某个候选 backend 为什么没有进入当前请求的可路由候选池
    # 输入：
    # - model/failed_backend_keys/busy_backend_keys: 候选模型和请求内排除集合
    # 输出：
    # - 当前 backend 被排除的稳定原因标签
    def _backend_exclusion_reason(
        self,
        model: TierModel,
        *,
        tier_name: str = "",
        failed_backend_keys: set[str] | None = None,
        busy_backend_keys: set[str] | None = None,
    ) -> str:
        backend_key = self.backend_key(model.backend, model.model_name, tier_name=tier_name, account=model.account)
        if not str(model.account or "").strip():
            return "account_missing"
        if not self.is_backend_enabled(model.backend, model.model_name, tier_name=tier_name, account=model.account):
            return "disabled"
        runtime_status = self.backend_runtime_status(model.backend, model.model_name, tier_name=tier_name, account=model.account)
        if not self.backend_routable(model.backend, model.model_name, tier_name=tier_name, account=model.account):
            return f"runtime_{runtime_status}"
        if self._quota.is_exhausted(model.backend, model.model_name):
            return "exhausted"
        if busy_backend_keys is not None and backend_key in busy_backend_keys:
            return "request_busy"
        if failed_backend_keys is not None and backend_key in failed_backend_keys:
            return "request_failed"
        return "available"

    # 用途：
    # - 在 all_backends_unavailable 场景下生成候选 backend 排除原因摘要，供日志和 dashboard 排查
    # 输入：
    # - models/failed_backend_keys/busy_backend_keys/tier_name: 当前 Tier 候选、请求内排除集合和 Tier 名称
    # 输出：
    # - 形如 `Tier:account/model=reason` 或 `Tier:agent:account/model=reason` 的简要诊断字符串
    def _selection_debug_summary(
        self,
        models: list[TierModel],
        *,
        failed_backend_keys: set[str] | None = None,
        busy_backend_keys: set[str] | None = None,
        tier_name: str = "",
    ) -> str:
        parts: list[str] = []
        for model in models:
            readable_backend = backend_readable_label(model)
            backend_label = f"{tier_name}:{readable_backend}" if tier_name else readable_backend
            reason = self._backend_exclusion_reason(
                model,
                tier_name=tier_name,
                failed_backend_keys=failed_backend_keys,
                busy_backend_keys=busy_backend_keys,
            )
            parts.append(f"{backend_label}={reason}")
        return "; ".join(parts)

    # 用途：
    # - 判断候选池不可用是否包含 quota exhausted / probe / request busy 这类可等待状态
    # 输入：
    # - selection_debug: `_selection_debug_summary` 生成的排除原因摘要
    # 输出：
    # - True 表示 client 应按 all_backends_busy 等待重试，而不是立即消耗失败重试
    def _selection_has_transient_busy(self, selection_debug: str) -> bool:
        normalized = str(selection_debug or "").strip().lower()
        return (
            "=exhausted" in normalized
            or "runtime_probing" in normalized
            or "request_busy" in normalized
            or "account_concurrency_full" in normalized
            or "account_interval_wait" in normalized
            or "account_rate_limit_wait" in normalized
        )

    # 用途：
    # - 返回 tier:account:model 的唯一状态 key
    # 输入：
    # - backend/model_name/tier_name/account: backend 名、模型展示名、Tier 名和 account 名
    # 输出：
    # - `tier:account:model_name`
    def backend_key(self, backend: str, model_name: str, *, tier_name: str = "", account: str = "") -> str:
        tier = str(tier_name or "").strip()
        account_key = str(account or "").strip()
        return f"{tier}:{account_key}:{str(model_name or '').strip()}"

    # 用途：
    # - 查询 backend 是否处于人工启用状态
    # 输入：
    # - backend/model_name/tier_name: backend 名、模型展示名和 Tier 名
    # 输出：
    # - True 表示 enabled 或未显式设置
    def is_backend_enabled(self, backend: str, model_name: str, *, tier_name: str = "", account: str = "") -> bool:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            return bool(self._admin_state_by_backend.get(key, True))

    # 用途：
    # - 设置 backend 的人工启用状态
    # 输入：
    # - backend/model_name/tier_name/enabled: backend 名、模型名、Tier 名和新状态
    # 输出：
    # - 无；只更新 router 内存态
    def set_backend_enabled(self, backend: str, model_name: str, enabled: bool, *, tier_name: str = "", account: str = "") -> None:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            self._admin_state_by_backend[key] = bool(enabled)
            if enabled:
                self._failure_count_by_backend.pop(key, None)

    # 用途：
    # - 查询 backend 当前的 runtime status
    # 输入：
    # - backend/model_name/tier_name/account: backend 名、模型展示名、Tier 名和账号
    # 输出：
    # - status 字符串；quota 自动 reset 后同步清理 stale exhausted 状态
    def backend_runtime_status(self, backend: str, model_name: str, *, tier_name: str = "", account: str = "") -> str:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            status = str(self._runtime_status_by_backend.get(key) or "running")
        if status == "exhausted" and not self._quota.is_exhausted(backend, model_name):
            with self._state_lock:
                if str(self._runtime_status_by_backend.get(key) or "running") == "exhausted":
                    self._runtime_status_by_backend[key] = "running"
                status = str(self._runtime_status_by_backend.get(key) or "running")
        return status

    # 用途：
    # - 设置 backend 当前 runtime status
    # 输入：
    # - backend/model_name/tier_name/status: backend 名、模型名、Tier 名和状态
    # 输出：
    # - 无；只更新 router 内存态
    def set_backend_runtime_status(self, backend: str, model_name: str, status: str, *, tier_name: str = "", account: str = "") -> None:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            self._runtime_status_by_backend[key] = str(status or "running")

    # 用途：
    # - 清理 reset 覆盖范围内 backend 的 runtime failure/exhausted 状态
    # 输入：
    # - tier_name: 可选 Tier 名称；为空时清理全部配置 backend
    # 输出：
    # - 已恢复为 running 的 backend key 列表；人工 disabled 的 backend 不会被恢复
    def reset_runtime_statuses(self, tier_name: str = "") -> list[str]:
        if str(tier_name or "").strip():
            normalized_tier = str(tier_name or "").strip()
            models = [
                (normalized_tier, model)
                for model in self._config.get_tier_models(normalized_tier)
            ]
        else:
            models = [
                (str(configured_tier), model)
                for configured_tier in self._config._config.get("llm_tiers", {})
                for model in self._config.get_tier_models(str(configured_tier))
            ]

        reset_keys: list[str] = []
        with self._state_lock:
            for model_tier, model in models:
                key = self.backend_key(model.backend, model.model_name, tier_name=model_tier, account=model.account)
                if not self._admin_state_by_backend.get(key, True):
                    continue
                self._runtime_status_by_backend[key] = "running"
                self._runtime_error_by_backend.pop(key, None)
                self._failure_count_by_backend.pop(key, None)
                reset_keys.append(key)
        return reset_keys

    # 用途：
    # - 判断 backend 当前是否允许参与真实路由
    # 输入：
    # - backend/model_name: backend 名和模型展示名
    # 输出：
    # - True 表示 runtime 可路由
    def backend_routable(self, backend: str, model_name: str, *, tier_name: str = "", account: str = "") -> bool:
        status = self.backend_runtime_status(backend, model_name, tier_name=tier_name, account=account)
        return status == "running"

    # 用途：
    # - 返回 backend 最近一次错误和 breaker 元数据
    # 输入：
    # - backend/model_name: backend 名和模型展示名
    # 输出：
    # - 最近错误和连续失败次数
    def backend_runtime_meta(self, backend: str, model_name: str, *, tier_name: str = "", account: str = "") -> dict[str, Any]:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            return {
                "failure_count": int(self._failure_count_by_backend.get(key) or 0),
                **dict(self._runtime_error_by_backend.get(key) or {}),
            }

    # 用途：
    # - 手工或 probe 成功后清理 backend breaker 与错误状态
    # 输入：
    # - backend/model_name: backend 名和模型展示名
    # 输出：
    # - 无；重置 runtime failure 状态
    def _record_backend_success(self, backend: str, model_name: str, *, tier_name: str = "", account: str = "") -> None:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            self._failure_count_by_backend.pop(key, None)
            self._runtime_error_by_backend.pop(key, None)
            self._runtime_status_by_backend[key] = "running"

    # 用途：
    # - 记录 backend 最近一次错误摘要，但不修改 breaker 阈值
    # 输入：
    # - backend/model_name/error_message/failure_type: backend 标识、错误文本和错误类别
    # 输出：
    # - 无；更新最近错误元数据
    def _record_backend_error(
        self,
        backend: str,
        model_name: str,
        error_message: str,
        *,
        tier_name: str = "",
        account: str = "",
        failure_type: str,
    ) -> None:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        with self._state_lock:
            self._runtime_error_by_backend[key] = {
                "last_error": str(error_message or ""),
                "last_error_type": str(failure_type or ""),
                "last_error_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

    # 用途：
    # - 对 unhealthy 失败计数，并在达到阈值后标记 runtime unreachable
    # 输入：
    # - backend/model_name/error_message/source: backend 标识、错误文本和失败来源（call/probe）
    # 输出：
    # - 无；更新连续失败计数和 runtime status，不修改人工 admin state
    def _record_unhealthy_failure(
        self,
        backend: str,
        model_name: str,
        error_message: str,
        *,
        tier_name: str = "",
        account: str = "",
        source: str = "call",
    ) -> None:
        key = self.backend_key(backend, model_name, tier_name=tier_name, account=account)
        normalized_source = str(source or "call").strip().lower() or "call"
        with self._state_lock:
            failure_count = int(self._failure_count_by_backend.get(key) or 0) + 1
            self._failure_count_by_backend[key] = failure_count
            self._runtime_error_by_backend[key] = {
                "last_error": str(error_message or ""),
                "last_error_type": "unhealthy",
                "last_error_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            if failure_count >= self._failure_threshold:
                self._runtime_status_by_backend[key] = "unreachable"
            elif normalized_source == "probe":
                self._runtime_status_by_backend[key] = "unreachable"
            else:
                self._runtime_status_by_backend[key] = "running"

    # 用途：
    # - 在当前可用 backend 中按配置顺序展开 backend.weight，按 ring cursor 查找有空槽的 backend 并立即占用
    # 输入：
    # - tier_name/models/busy_backend_keys: Tier 名称、可用模型和请求内 busy 记录集合
    # 输出：
    # - 已占用 account 槽位的模型、backend key、account key 和下一次 busy retry 建议秒数
    def _select_and_acquire_weighted_backend(
        self,
        tier_name: str,
        models: list[TierModel],
        *,
        busy_backend_keys: set[str] | None = None,
    ) -> tuple[TierModel | None, str, str, float]:
        weighted_models: list[TierModel] = []
        for model in models:
            weighted_models.extend([model] * max(1, int(model.weight or 1)))
        if not weighted_models:
            return None, "", "", 0.5
        retry_after_candidates: list[float] = []
        with self._weight_state_lock:
            cursor = int(self._weighted_cursor_by_tier.get(tier_name) or 0)
            for offset in range(len(weighted_models)):
                index = (cursor + offset) % len(weighted_models)
                selected = weighted_models[index]
                backend_key = self.backend_key(selected.backend, selected.model_name, tier_name=tier_name, account=selected.account)
                account_key = str(selected.account or "").strip()
                acquired, busy_reason = self._concurrency.acquire(backend_key, account_key)
                if acquired:
                    self._weighted_cursor_by_tier[tier_name] = index + 1
                    return selected, backend_key, account_key, 0.5
                retry_after_candidates.append(
                    self._concurrency.retry_after_seconds(account_key, fallback_seconds=0.5)
                )
                if busy_backend_keys is not None:
                    busy_backend_keys.add(backend_key)
                self._trace(
                    "router",
                    "debug",
                    "router.backend.busy",
                    {
                        "tier": tier_name,
                        "backend_key": backend_key,
                        "account": account_key,
                        "reason": busy_reason,
                        "retry_after_seconds": round(retry_after_candidates[-1], 3),
                    },
                )
            self._weighted_cursor_by_tier[tier_name] = cursor + len(weighted_models)
        retry_after_seconds = min(
            (delay for delay in retry_after_candidates if delay >= 0),
            default=0.5,
        )
        return None, "", "", retry_after_seconds

    def _build_stats_event(
        self,
        tier_name: str,
        backend: str,
        account: str,
        backend_type: str,
        model: str,
        ok: bool,
        latency_ms: float,
        token_usage: dict[str, int],
        is_fallback: bool,
        fallback_count: int,
        selection_debug: str = "",
    ) -> dict[str, Any]:
        return {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tier": tier_name,
            "backend": backend,
            "account": account,
            "backend_type": backend_type,
            "model": model,
            "ok": ok,
            "latency_ms": token_usage.get("latency_ms", latency_ms),
            "call_count": token_usage.get("call_count", 1),
            "failed_call_count": token_usage.get("failed_call_count", 0),
            "prompt_tokens": token_usage.get("prompt_tokens", 0),
            "completion_tokens": token_usage.get("completion_tokens", 0),
            "total_tokens": token_usage.get("total_tokens", 0),
            "cached_tokens": token_usage.get("cached_tokens", 0),
            "prompt_chars": token_usage.get("prompt_chars", 0),
            "completion_chars": token_usage.get("completion_chars", 0),
            "provider_usage_available": token_usage.get("provider_usage_available", False),
            "usage_source": token_usage.get("usage_source", ""),
            "is_fallback": is_fallback,
            "fallback_count": fallback_count,
            "selection_debug": str(selection_debug or ""),
        }

    # 用途：
    # - 在当前 Tier 的 backend prompt 容量不足时，将本次请求提升到上一级 Tier
    # 输入：
    # - tier_name/prompt/trace_base: 原始 Tier、完整 prompt 和当前 trace 上下文
    # 输出：
    # - 实际用于后续选择 backend 的 Tier 名称
    def _resolve_upshift_tier(
        self,
        *,
        tier_name: str,
        prompt: str,
        trace_base: dict[str, Any],
    ) -> str:
        normalized_tier = str(tier_name or "").strip()
        estimated_prompt_tokens = self._estimate_prompt_tokens(prompt)
        current_tier = normalized_tier
        while current_tier in UPSHIFT_TARGET_BY_TIER:
            source_models = self._config.get_tier_models(current_tier)
            if not source_models:
                return current_tier
            capacity = self._tier_prompt_capacity_tokens(source_models)
            if capacity <= 0 or estimated_prompt_tokens <= capacity:
                return current_tier

            target_tier = UPSHIFT_TARGET_BY_TIER[current_tier]
            target_models = self._config.get_tier_models(target_tier)
            if not target_models:
                self._trace(
                    "router",
                    "warn",
                    "router.upshift.target_missing",
                    {
                        **trace_base,
                        "tier": current_tier,
                        "upshift_target_tier": target_tier,
                        "estimated_prompt_tokens": estimated_prompt_tokens,
                        "source_prompt_capacity_tokens": capacity,
                    },
                )
                return current_tier

            self._trace(
                "router",
                "info",
                "router.upshift",
                {
                    **trace_base,
                    "from_tier": current_tier,
                    "to_tier": target_tier,
                    "estimated_prompt_tokens": estimated_prompt_tokens,
                    "source_prompt_capacity_tokens": capacity,
                },
            )
            with self._state_lock:
                self._upshift_count += 1
            current_tier = target_tier
        return current_tier

    # 用途：
    # - 计算一组 backend 配置中可容纳的最大 prompt token 数
    # 输入：
    # - models: 当前 Tier 的 backend 配置列表
    # 输出：
    # - 最大 prompt token 容量；0 表示未配置上下文上限，不触发 Upshift
    def _tier_prompt_capacity_tokens(self, models: list[TierModel]) -> int:
        capacities: list[int] = []
        for model in models:
            max_context_tokens = int(model.max_context_tokens or 0)
            if max_context_tokens <= 0:
                return 0
            reserved_completion_tokens = int(
                model.max_output_tokens
                or model.reserved_completion_tokens
                or DEFAULT_MAX_OUTPUT_TOKENS
            )
            capacities.append(max(max_context_tokens - max(reserved_completion_tokens, 0), 0))
        if not capacities:
            return 0
        return max(capacities)

    # 用途：
    # - 返回当前 router 生命周期内实际执行的 Upshift 次数
    # 输入：
    # - 无；读取 router 运行态计数器
    # 输出：
    # - Upshift 总次数
    def upshift_count(self) -> int:
        with self._state_lock:
            return int(self._upshift_count)

    # 用途：
    # - 在发送 backend 请求前按配置检查 prompt 是否超过上下文窗口
    # 输入：
    # - model/prompt/credentials: 本次调用的模型、完整 prompt 与请求默认参数
    # 输出：
    # - 超限时返回错误上下文；未配置或未超限时返回 None
    def _context_limit_error(
        self,
        model: TierModel,
        prompt: str,
        credentials: dict[str, Any],
    ) -> dict[str, Any] | None:
        capabilities = self._config.get_backend_capabilities(
            model.backend,
            model_name=model.model_name,
            model_key=model.model_key,
            account=model.account,
        )
        max_context_tokens = int(capabilities.get("max_context_tokens") or 0)
        if max_context_tokens <= 0:
            return None
        estimated_prompt_tokens = self._estimate_prompt_tokens(prompt)
        reserved_completion_tokens = int(
            capabilities.get("reserved_completion_tokens")
            or capabilities.get("max_output_tokens")
            or credentials.get("max_tokens")
            or DEFAULT_MAX_OUTPUT_TOKENS
        )
        estimated_total_tokens = estimated_prompt_tokens + max(reserved_completion_tokens, 0)
        if estimated_total_tokens <= max_context_tokens:
            return None
        return {
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "estimated_total_tokens": estimated_total_tokens,
            "max_context_tokens": max_context_tokens,
            "message": (
                "context_length_exceeded: "
                f"estimated_total_tokens={estimated_total_tokens}, "
                f"estimated_prompt_tokens={estimated_prompt_tokens}, "
                f"reserved_completion_tokens={reserved_completion_tokens}, "
                f"max_context_tokens={max_context_tokens}, backend={model.backend}"
            ),
        }

    # 用途：
    # - 将 prompt 长度估算结果转换为失败响应可记录的 token usage
    # 输入：
    # - prompt: 完整 LLM prompt 文本
    # 输出：
    # - 只包含输入 token 估算值的 usage 字典
    def _estimated_prompt_token_usage(self, prompt: str) -> dict[str, int]:
        prompt_tokens = self._estimate_prompt_tokens(prompt)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 0,
            "total_tokens": prompt_tokens,
        }

    # 用途：
    # - 判断 backend 错误是否来自当前请求本身，而不是 backend 健康问题
    # 输入：
    # - error_message: backend 抛出的标准化错误文本
    # 输出：
    # - client request 错误消息；非请求错误时返回空字符串
    def _client_request_error_message(self, error_message: str) -> str:
        normalized = str(error_message or "").strip()
        lower = normalized.lower()
        if not normalized:
            return ""
        client_error_markers = (
            "http 400",
            "http 413",
            "http 422",
            "context_length_exceeded",
            "context length",
            "maximum context",
            "max context",
            "token limit",
            "too many tokens",
            "input too large",
            "prompt too large",
            "prompt is too long",
            "request too large",
            "invalid_request",
            "mlexp job ended with protocol status",
        )
        if any(marker in lower for marker in client_error_markers):
            return f"client_request_error: {normalized}"
        return ""

    # 用途：
    # - 解析当前 backend/model 本次调用应该使用的最大输出 token 数
    # 输入：
    # - model/credentials: 当前路由选中的模型和 backend 凭证配置
    # 输出：
    # - 传给 backend client 的 max_tokens
    def _max_tokens_for_model(self, model: TierModel, credentials: dict[str, Any]) -> int:
        capabilities = self._config.get_backend_capabilities(
            model.backend,
            model_name=model.model_name,
            model_key=model.model_key,
            account=model.account,
        )
        for key in ("max_output_tokens", "reserved_completion_tokens"):
            value = capabilities.get(key)
            if value:
                return int(value)
        return int(credentials.get("max_tokens") or DEFAULT_MAX_OUTPUT_TOKENS)

    # 用途：
    # - 对 prompt 做轻量 token 估算，供 context 预检使用
    # 输入：
    # - prompt: 完整 LLM prompt 文本
    # 输出：
    # - 保守估算的 prompt token 数
    def _estimate_prompt_tokens(self, prompt: str) -> int:
        text = str(prompt or "")
        if not text:
            return 0
        return max(1, (len(text) + 2) // 3)

    def _get_backend_credentials(
        self,
        backend_name: str,
        provider: str = "",
        model_name: str = "",
        model_key: str = "",
        account: str = "",
    ) -> dict[str, Any]:
        credentials = self._config.get_backend_credentials(
            backend_name,
            provider=provider,
            model_name=model_name,
            model_key=model_key,
            account=account,
        )
        expires_at = str(credentials.get("expires_at") or "").strip()
        if expires_at:
            try:
                expires_at_value = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expires_at_value.tzinfo is None:
                    expires_at_value = expires_at_value.replace(tzinfo=timezone.utc)
            except ValueError as exc:
                raise BackendCallError(backend_name, "credential expiry is invalid") from exc
            if expires_at_value <= datetime.now(timezone.utc):
                raise BackendCallError(backend_name, "credential expired")
        return credentials
