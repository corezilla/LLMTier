from __future__ import annotations

import ipaddress
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from llm_tier.execution_identity import resolve_execution_identity_for_role
from llm_tier.redaction import redact_sensitive_value
from llm_tier.tier_model import TierCallRequest, TierCallResult
from utils.response_parser import ParseError, ResponseParser

DEFAULT_SERVER_URL = "http://127.0.0.1:8765"
POLL_INTERVAL_SECONDS = 1.0
POLL_TIMEOUT_SECONDS = 900.0
POLL_TIMEOUT_BUFFER_SECONDS = 180.0
DEFAULT_BACKEND_TIMEOUT_SECONDS = 600.0
CONNECT_TIMEOUT_SECONDS = 2.0
BUSY_RETRY_INTERVAL_SECONDS = 0.5
BUSY_MAX_RETRY_INTERVAL_SECONDS = 600.0
TRACE_LEVELS = {
    "trace": 5,
    "debug": 10,
    "info": 20,
    "warn": 30,
    "warning": 30,
    "error": 40,
}
DEFAULT_TRACE_STATE_PATH = "workspaces/tier_state/tier_debug.json"
DEFAULT_TRACE_PATH = "workspaces/tier_state/tier_trace.jsonl"
REPLAY_RESPONSE_PATH_ENV = "SLINKY_TIER_CLIENT_REPLAY_RESPONSE_PATH"
REPLAY_MAP_PATH_ENV = "SLINKY_TIER_CLIENT_REPLAY_MAP_PATH"
REPLAY_ROLE_ENV = "SLINKY_TIER_CLIENT_REPLAY_ROLE"
REPLAY_PROMPT_NAME_ENV = "SLINKY_TIER_CLIENT_REPLAY_PROMPT_NAME"
REPLAY_TASK_ID_ENV = "SLINKY_TIER_CLIENT_REPLAY_TASK_ID"
_RESPONSE_PARSER = ResponseParser()
_PRIVATE_TIER_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
)


# Purpose: Decide whether one Tier hostname is safe for the existing trusted-network HTTP transport.
# Inputs: Parsed URL hostname or server bind host.
# Outputs: True only for localhost, loopback, RFC1918, or IPv6 ULA addresses.
def is_trusted_tier_host(hostname: str) -> bool:
    normalized_hostname = str(hostname or "").strip().lower()
    if normalized_hostname == "localhost":
        return True
    try:
        address = ipaddress.ip_address(normalized_hostname)
    except ValueError:
        return False
    return address.is_loopback or any(address in network for network in _PRIVATE_TIER_NETWORKS)


# 用途：
# - 提供 llm_tier HTTP client，是 roles/escalation 等外部模块调用 LLM 的统一入口
# 输入：
# - server_url: 可选 tier server 地址
# 输出：
# - call/get_stats/reset 等远程操作接口
class TierClient:
    # 用途：
    # - 初始化 tier server 地址
    # 输入：
    # - server_url: 显式传入或从环境变量读取的 server 地址
    # 输出：
    # - 可复用的 TierClient 实例
    def __init__(self, server_url: str = "") -> None:
        resolved_server_url = (server_url or
                               os.environ.get("TIER_SERVER_URL") or
                               DEFAULT_SERVER_URL).rstrip("/")
        parsed_server_url = urllib.parse.urlsplit(resolved_server_url)
        if (
            parsed_server_url.scheme not in {"http", "https"}
            or not is_trusted_tier_host(parsed_server_url.hostname or "")
            or parsed_server_url.username is not None
            or parsed_server_url.password is not None
            or parsed_server_url.path not in {"", "/"}
            or parsed_server_url.query
            or parsed_server_url.fragment
        ):
            raise ValueError("Tier server URL must be a credential-free trusted HTTP origin")
        self._server_url = resolved_server_url
        self._busy_retry_interval_seconds = _env_float(
            "TIER_BUSY_RETRY_INTERVAL_SECONDS",
            BUSY_RETRY_INTERVAL_SECONDS,
        )
        self._trace_state_path = os.environ.get("TIER_TRACE_STATE_PATH", DEFAULT_TRACE_STATE_PATH).strip()

    # =========================================================================
    # Role 调用 — 外部唯一需要的接口
    # =========================================================================

    # 用途：
    # - 通过 role 名称执行一次 LLM 调用
    # 输入：
    # - payload: role_name、prompt、project/stage/phase/task 上下文、metadata 和可选 response_type
    # 输出：
    # - 包含 ok/content/model/error/usage 的调用结果字典；response_type=json 时包含 parsed_json/parse_error
    def invoke_role(self, payload: dict[str, Any]) -> dict[str, Any]:
        role_name = str(payload.get("role_name") or "").strip()
        prompt = str(payload.get("prompt") or payload.get("user_prompt") or "").strip()
        prompt_path = str(payload.get("prompt_path") or "").strip()
        if not role_name or (not prompt and not prompt_path):
            return {"ok": False, "content": "", "error": "invoke_role requires role_name and prompt or prompt_path", "model_name": ""}

        metadata = dict(payload.get("metadata") or {})
        execution_identity = resolve_execution_identity_for_role(role_name)
        if not str(metadata.get("execution_level") or "").strip():
            metadata["execution_level"] = execution_identity.execution_level
        if not str(metadata.get("role_profile") or "").strip():
            metadata["role_profile"] = execution_identity.role_profile
        replay_payload = self._maybe_replay_role_response(
            payload=payload,
            metadata=metadata,
            role_name=role_name,
        )
        if replay_payload is not None:
            response_type = str(payload.get("response_type") or metadata.get("response_type") or "").strip().lower()
            if response_type == "json":
                _attach_parsed_json_response(replay_payload)
            return replay_payload

        req = TierCallRequest(
            role_name=role_name,
            prompt=prompt,
            project_name=str(metadata.get("project_name") or payload.get("project_name") or ""),
            stage_name=str(metadata.get("stage_name") or payload.get("stage_name") or ""),
            phase_name=str(metadata.get("phase_name") or payload.get("phase_name") or ""),
            task_id=str(metadata.get("task_id") or payload.get("task_id") or ""),
            task_key=str(metadata.get("task_key") or payload.get("task_key") or ""),
            temperature=float(payload.get("temperature") or 0.0),
            timeout_seconds=int(payload.get("timeout_seconds") or metadata.get("timeout_seconds") or 0) or None,
            metadata=metadata,
            prompt_path=prompt_path,
            response_path=str(payload.get("response_path") or "").strip(),
            raw_response_path=str(payload.get("raw_response_path") or "").strip(),
            error_response_path=_resolve_error_response_path(
                response_path=str(payload.get("response_path") or "").strip(),
                requested_path=str(payload.get("error_response_path") or "").strip(),
            ),
        )
        result = self.call(req)
        response_payload = {
            "ok": result.ok,
            "content": result.content,
            "model_name": result.model_name,
            "error": result.error_message if not result.ok else "",
            "tier": result.tier,
            "backend": result.backend,
            "account": result.account,
            "execution_level": str(metadata.get("execution_level") or "").strip(),
            "role_profile": str(metadata.get("role_profile") or "").strip(),
            "latency_ms": result.latency_ms,
            "token_usage": result.token_usage,
            "usage": result.token_usage,
            "raw_response": result.raw_response,
            "artifact_paths": result.artifact_paths,
            "error_code": result.error_code,
        }
        response_type = str(payload.get("response_type") or metadata.get("response_type") or "").strip().lower()
        if response_type == "json":
            _attach_parsed_json_response(response_payload)
        return response_payload

    # 用途：
    # - 在调试模式下跳过 Tier HTTP 调用，直接把本地 fixture response 写入当前调用的 response_path
    # 输入：
    # - payload/metadata/role_name: 本次 Role 调用请求和运行上下文
    # 输出：
    # - 命中 replay 配置时返回模拟成功 payload；未启用或过滤不匹配时返回 None
    def _maybe_replay_role_response(
        self,
        *,
        payload: dict[str, Any],
        metadata: dict[str, Any],
        role_name: str,
    ) -> dict[str, Any] | None:
        replay_source = _resolve_replay_source_path(payload=payload, metadata=metadata, role_name=role_name)
        if replay_source is None:
            return None
        content = replay_source.read_text(encoding="utf-8")
        response_path = _write_replay_response_file(
            requested_path=str(payload.get("response_path") or "").strip(),
            content=content,
            metadata=metadata,
        )
        raw_response_path = _write_replay_raw_response_file(
            requested_path=str(payload.get("raw_response_path") or "").strip(),
            replay_source=replay_source,
            content=content,
            metadata=metadata,
            role_name=role_name,
            prompt_name=str(metadata.get("prompt_name") or payload.get("prompt_name") or "").strip(),
        )
        artifact_paths: dict[str, str] = {}
        if response_path:
            artifact_paths["response_path"] = response_path
        if raw_response_path:
            artifact_paths["raw_response_path"] = raw_response_path
        return {
            "ok": True,
            "content": "" if response_path else content,
            "model_name": "debug-replay",
            "error": "",
            "tier": "debug",
            "backend": "debug_replay",
            "execution_level": str(metadata.get("execution_level") or "").strip(),
            "role_profile": str(metadata.get("role_profile") or "").strip(),
            "latency_ms": 0.0,
            "token_usage": {},
            "usage": {},
            "raw_response": {
                "debug_replay": True,
                "source_response_path": str(replay_source),
                "content_chars": len(content),
                "execution_level": str(metadata.get("execution_level") or "").strip(),
                "role_profile": str(metadata.get("role_profile") or "").strip(),
            },
            "artifact_paths": artifact_paths,
            "error_code": 0,
        }

    # =========================================================================
    # 健康检查
    # =========================================================================

    # Purpose: Check whether the configured Tier HTTP listener answers health requests.
    # Inputs: Positive request timeout in seconds.
    # Outputs: True only for a successful health response; transport failures return False.
    def is_reachable(self, timeout: float = CONNECT_TIMEOUT_SECONDS) -> bool:
        try:
            self._http_get("/health", timeout=timeout)
            return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            return False

    # 用途：
    # - 查询 server 健康状态
    # 输入：
    # - 无
    # 输出：
    # - server 返回的 health payload
    def get_health(self) -> dict[str, Any]:
        return self._http_get("/health")

    # =========================================================================
    # 普通调用 — role → tier → backend（走 role_tier_map）
    # =========================================================================

    # 用途：
    # - 同步执行 role LLM 调用
    # 输入：
    # - req: TierCallRequest
    # 输出：
    # - TierCallResult
    def call(self, req: TierCallRequest) -> TierCallResult:
        return self._call_with_busy_retry(
            submit_path="/call",
            request_data=_request_dict(req),
        )

    # 用途：
    # - 异步提交 role LLM 调用
    # 输入：
    # - req: TierCallRequest
    # 输出：
    # - job_id；调用方后续通过 get_result 轮询
    def call_async(self, req: TierCallRequest) -> str:
        data = _request_dict(req)
        resp = self._http_post("/call", data)
        return str(resp.get("job_id", ""))

    # 用途：
    # - 查询异步 job 结果
    # 输入：
    # - job_id: /call 或 /escalate 返回的 job id
    # 输出：
    # - 完成时返回 TierCallResult，未完成或查询失败时返回 None
    def get_result(self, job_id: str) -> TierCallResult | None:
        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            raise ValueError("job_id must be non-empty")
        resp = self._http_get(f"/result/{urllib.parse.quote(normalized_job_id, safe='')}")
        status = resp.get("status", "")
        if status != "done":
            return None
        return _result_from_dict(resp.get("result", {}))

    # Purpose: Forward one whitelisted Dashboard request through the configured Tier HTTP transport.
    # Inputs: GET/POST method, absolute Tier path, optional JSON object, and positive timeout.
    # Outputs: Upstream HTTP status and decoded JSON object without applying business fallback.
    def proxy_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = CONNECT_TIMEOUT_SECONDS,
    ) -> tuple[int, dict[str, Any]]:
        normalized_method = str(method or "").strip().upper()
        normalized_path = str(path or "").strip()
        if normalized_method not in {"GET", "POST"}:
            raise ValueError(f"unsupported Tier HTTP method: {normalized_method}")
        if not normalized_path.startswith("/") or normalized_path.startswith("//"):
            raise ValueError("Tier HTTP path must be origin-relative")
        if float(timeout) <= 0:
            raise ValueError("Tier HTTP timeout must be positive")
        return self._http_request(
            normalized_method,
            normalized_path,
            payload,
            timeout=float(timeout),
        )

    # =========================================================================
    # Escalation 调用 — 按 tier 优先级扫荡（不走 role_tier_map）
    # =========================================================================

    # 用途：
    # - 同步执行跨 Tier fallback 调用
    # 输入：
    # - req: TierEscalationRequest
    # 输出：
    # - TierCallResult
    def escalate(self, req: TierEscalationRequest) -> TierCallResult:
        return self._call_with_busy_retry(
            submit_path="/escalate",
            request_data=_escalation_request_dict(req),
        )

    # 用途：
    # - 异步提交跨 Tier fallback 调用
    # 输入：
    # - req: TierEscalationRequest
    # 输出：
    # - job_id；调用方后续通过 get_result 轮询
    def escalate_async(self, req: TierEscalationRequest) -> str:
        data = _escalation_request_dict(req)
        resp = self._http_post("/escalate", data)
        return str(resp.get("job_id", ""))

    # =========================================================================
    # 管理接口
    # =========================================================================

    # 用途：
    # - 查询 llm_tier runtime 统计，支持按 project/stage/phase/task 过滤
    # 输入：
    # - project/stage/phase/task_id/task_key/tier/backend/role: 可选过滤条件
    # 输出：
    # - Tier Server /stats 返回的统计 payload
    def get_stats(
        self,
        project: str = "",
        *,
        stage: str = "",
        phase: str = "",
        task_id: str = "",
        task_key: str = "",
        tier: str = "",
        backend: str = "",
        role: str = "",
    ) -> dict[str, Any]:
        params = {
            "project": project,
            "stage": stage,
            "phase": phase,
            "task_id": task_id,
            "task_key": task_key,
            "tier": tier,
            "backend": backend,
            "role": role,
        }
        query = urllib.parse.urlencode({key: value for key, value in params.items() if value})
        path = f"/stats?{query}" if query else "/stats"
        return self._http_get(path)

    def reset_exhausted(self, tier_name: str = "") -> dict[str, Any]:
        return self._http_post("/reset", {"tier_name": tier_name})

    def reload_config(self) -> dict[str, Any]:
        return self._http_post("/reload", {})

    # 用途：
    # - 查询 tier server 当前 runtime 快照，供 dashboard、environment phase 和调试工具读取 backend 状态
    # 输入：
    # - 无
    # 输出：
    # - `/runtime` 返回的 runtime payload
    def get_runtime(self) -> dict[str, Any]:
        return self._http_get("/runtime", timeout=POLL_TIMEOUT_SECONDS)

    # 用途：
    # - 对指定 Tier backend 触发一次后台 probe
    # 输入：
    # - tier_name/account/backend/model_name: Tier 内 Backend identity
    # 输出：
    # - `/backend/probe` 返回的 probe 启动结果
    def probe_backend(self, *, tier_name: str, account: str, backend: str, model_name: str) -> dict[str, Any]:
        return self._http_post(
            "/backend/probe",
            {
                "tier_name": str(tier_name or "").strip(),
                "account": str(account or "").strip(),
                "backend": str(backend or "").strip(),
                "model_name": str(model_name or "").strip(),
            },
        )

    # 用途：
    # - 从 runtime 快照中定位单个 backend 的状态
    # 输入：
    # - tier_name/account/backend/model_name: Tier 内 Backend identity
    # 输出：
    # - 匹配到的 backend runtime 行；找不到时返回空字典
    def get_backend_status(self, *, tier_name: str, account: str, backend: str, model_name: str) -> dict[str, Any]:
        runtime = self.get_runtime()
        tiers = runtime.get("tiers") if isinstance(runtime.get("tiers"), dict) else {}
        rows = tiers.get(str(tier_name or "").strip()) if isinstance(tiers, dict) else []
        for row in list(rows or []):
            if not isinstance(row, dict):
                continue
            if str(row.get("account") or "").strip() != str(account or "").strip():
                continue
            if str(row.get("backend") or "").strip() != str(backend or "").strip():
                continue
            if str(row.get("model_name") or "").strip() != str(model_name or "").strip():
                continue
            return dict(row)
        return {}

    # 用途：
    # - 等待指定 backend 的 probe_status 达到目标状态
    # 输入：
    # - tier_name/account/backend/model_name: Tier 内 Backend identity
    # - expected_status/timeout_seconds/poll_interval_seconds: 目标状态、最大等待时间和轮询间隔
    # 输出：
    # - 最终 backend status 行；超时或失败状态会抛出 RuntimeError
    def wait_backend_probe_status(
        self,
        *,
        tier_name: str,
        account: str,
        backend: str,
        model_name: str,
        expected_status: str = "running",
        timeout_seconds: int = 600,
        poll_interval_seconds: float = 2.0,
    ) -> dict[str, Any]:
        started_at = time.time()
        terminal_failures = {"unreachable", "exhausted", "disabled"}
        while True:
            status_row = self.get_backend_status(
                tier_name=tier_name,
                account=account,
                backend=backend,
                model_name=model_name,
            )
            probe_status = str(status_row.get("probe_status") or "").strip().lower()
            if probe_status == str(expected_status or "running").strip().lower():
                return status_row
            if probe_status in terminal_failures:
                raise RuntimeError(f"backend probe ended with {probe_status}: {backend}:{model_name}")
            if time.time() - started_at >= int(timeout_seconds or 600):
                raise RuntimeError(f"backend probe timed out after {timeout_seconds}s: {backend}:{model_name}")
            time.sleep(float(poll_interval_seconds or 2.0))

    # =========================================================================
    # 内部
    # =========================================================================

    # 用途：
    # - 对同步 Tier 调用统一处理 server 返回的 all_backends_busy，按 server 建议退避重提请求直到成功
    # 输入：
    # - submit_path: `/call` 或 `/escalate`
    # - request_data: 要提交给 server 的请求 JSON
    # 输出：
    # - TierCallResult；busy 不向业务层返回，会持续等待并重试
    def _call_with_busy_retry(
        self,
        *,
        submit_path: str,
        request_data: dict[str, Any],
    ) -> TierCallResult:
        started_at = time.time()
        busy_retry_count = 0
        total_timeout_seconds = _poll_timeout_for_request(request_data)

        while True:
            if time.time() - started_at >= total_timeout_seconds:
                raise TimeoutError(f"Tier busy retry timed out after {total_timeout_seconds:.1f}s")
            result = self._submit_and_wait(
                submit_path=submit_path,
                request_data=request_data,
            )
            if not self._is_busy_result(result):
                return result
            busy_retry_count += 1
            elapsed_seconds = time.time() - started_at
            time.sleep(self._busy_retry_delay_seconds(
                result,
                elapsed_seconds=elapsed_seconds,
                retry_count=busy_retry_count,
            ))

    # 用途：
    # - 提交一次 server job 并等待 job 完成
    # 输入：
    # - submit_path: `/call` 或 `/escalate`
    # - request_data: 要提交给 server 的请求 JSON；可包含 backend timeout
    # 输出：
    # - TierCallResult；当 server 未返回 job_id 时返回失败结果
    def _submit_and_wait(
        self,
        *,
        submit_path: str,
        request_data: dict[str, Any],
    ) -> TierCallResult:
        request_data = dict(request_data or {})
        metadata = dict(request_data.get("metadata") or {}) if isinstance(request_data.get("metadata"), dict) else {}
        client_request_id = str(metadata.get("client_request_id") or uuid.uuid4())[:12]
        metadata["client_request_id"] = client_request_id
        request_data["metadata"] = metadata
        submit_started_at = time.time()
        self._trace(
            "client",
            "info",
            "client.submit.start",
            {
                **_request_trace_fields(request_data),
                "submit_path": submit_path,
                "request_bytes": len(json.dumps(request_data, ensure_ascii=False).encode("utf-8")),
            },
        )
        resp = self._http_post(submit_path, request_data)
        job_id = str(resp.get("job_id", "")).strip()
        self._trace(
            "client",
            "info",
            "client.submit.finish",
            {
                **_request_trace_fields(request_data),
                "submit_path": submit_path,
                "job_id": job_id,
                "elapsed_ms": (time.time() - submit_started_at) * 1000,
                "ok": bool(resp.get("ok")),
            },
        )
        if not job_id:
            return TierCallResult(
                ok=False, content="", backend="", model_name="",
                backend_type="", tier="", tier_priority=0,
                latency_ms=0, token_usage={},
                error_code=1998, error_message="server did not return job_id",
            )
        return self._poll_result(
            job_id,
            timeout_seconds=_poll_timeout_for_request(request_data),
            request_data=request_data,
        )

    # 用途：
    # - 判断一次 Tier 调用结果是否属于可由 client 继续等待并重提的 busy 错误
    # 输入：
    # - result: 本次 server job 的最终 TierCallResult
    # 输出：
    # - True 表示命中 all_backends_busy，需要 client 继续等待；否则返回 False
    def _is_busy_result(self, result: TierCallResult) -> bool:
        if result.ok:
            return False
        error_text = str(result.error_message or "").strip().lower()
        return error_text == "all_backends_busy" or error_text.startswith("all_backends_busy:")

    # 用途：
    # - 从 server busy 结果中读取下一次重试建议，并按已等待时长逐步扩大重试间隔
    # 输入：
    # - result: 当前 busy 的 TierCallResult
    # 输出：
    # - 本次应等待的秒数，最大不超过 10 分钟
    def _busy_retry_delay_seconds(
        self,
        result: TierCallResult,
        *,
        elapsed_seconds: float = 0.0,
        retry_count: int = 0,
    ) -> float:
        scheduled_delay = _busy_retry_schedule_seconds(
            elapsed_seconds=elapsed_seconds,
            retry_count=retry_count,
            initial_seconds=self._busy_retry_interval_seconds,
        )
        if isinstance(result.raw_response, dict):
            try:
                retry_after = float(result.raw_response.get("retry_after_seconds") or 0.0)
            except (TypeError, ValueError):
                retry_after = 0.0
            if retry_after > 0:
                return min(BUSY_MAX_RETRY_INTERVAL_SECONDS, max(scheduled_delay, retry_after))
        return scheduled_delay

    # 用途：
    # - 轮询Tier Server job直到完成，并在总等待预算到期时明确终止
    # 输入：
    # - job_id/timeout_seconds: server 返回的 job id 和预期完成等待秒数
    # 输出：
    # - TierCallResult；超时抛出TimeoutError，transport异常在预算内重试
    def _poll_result(
        self,
        job_id: str,
        *,
        timeout_seconds: float,
        request_data: dict[str, Any] | None = None,
    ) -> TierCallResult:
        started_at = time.time()
        poll_count = 0
        trace_fields = _request_trace_fields(request_data or {})
        while True:
            elapsed = time.time() - started_at
            if elapsed >= timeout_seconds:
                self._trace(
                    "client",
                    "error",
                    "client.poll.timeout",
                    {
                        **trace_fields,
                        "job_id": job_id,
                        "elapsed_ms": elapsed * 1000,
                        "poll_count": poll_count,
                        "timeout_seconds": timeout_seconds,
                    },
                )
                raise TimeoutError(f"Tier job poll timed out after {timeout_seconds:.1f}s: {job_id}")
            try:
                poll_count += 1
                resp = self._http_get(f"/result/{job_id}")
            except Exception as exc:
                self._trace(
                    "client",
                    "warn",
                    "client.poll.error",
                    {
                        **trace_fields,
                        "job_id": job_id,
                        "elapsed_ms": (time.time() - started_at) * 1000,
                        "poll_count": poll_count,
                        "error_message": str(exc),
                    },
                )
                time.sleep(_busy_retry_schedule_seconds(
                    elapsed_seconds=time.time() - started_at,
                    retry_count=poll_count,
                    initial_seconds=POLL_INTERVAL_SECONDS,
                ))
                continue
            status = resp.get("status", "")
            if status == "done":
                result = _result_from_dict(resp.get("result", {}))
                self._trace(
                    "client",
                    "info",
                    "client.poll.done",
                    {
                        **trace_fields,
                        "job_id": job_id,
                        "elapsed_ms": (time.time() - started_at) * 1000,
                        "poll_count": poll_count,
                        "ok": result.ok,
                        "backend": result.backend,
                        "account": result.account,
                        "model_name": result.model_name,
                        "tier": result.tier,
                        "error_code": result.error_code,
                        "error_message": result.error_message,
                    },
                )
                return result
            time.sleep(_busy_retry_schedule_seconds(
                elapsed_seconds=elapsed,
                retry_count=poll_count,
                initial_seconds=POLL_INTERVAL_SECONDS,
            ))

    # 用途：
    # - 读取 server 写出的 debug state，判断 client 侧是否需要写 trace
    # 输入：
    # - 无；读取 TIER_TRACE_STATE_PATH 或默认 workspaces/tier_state/tier_debug.json
    # 输出：
    # - debug state 字典；未开启或文件不存在时返回 disabled state
    def _client_trace_state(self) -> dict[str, Any]:
        state_path = Path(self._trace_state_path or DEFAULT_TRACE_STATE_PATH)
        if not state_path.exists():
            return {"enabled": False, "level": "info", "types": [], "path": DEFAULT_TRACE_PATH}
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"enabled": False, "level": "info", "types": [], "path": DEFAULT_TRACE_PATH}
        return dict(data or {}) if isinstance(data, dict) else {"enabled": False, "level": "info", "types": [], "path": DEFAULT_TRACE_PATH}

    # 用途：
    # - 将 client 侧提交和 poll 事件写入与 server 共用的 tier_trace.jsonl
    # 输入：
    # - event_type/level/event/fields: 类型、级别、事件名和诊断字段
    # 输出：
    # - 无；失败时静默跳过，避免影响 LLM 调用
    def _trace(
        self,
        event_type: str,
        level: str,
        event: str,
        fields: dict[str, Any] | None = None,
    ) -> None:
        state = self._client_trace_state()
        if not bool(state.get("enabled")):
            return
        normalized_type = str(event_type or "client").strip().lower()
        normalized_level = str(level or "info").strip().lower()
        if normalized_level == "warning":
            normalized_level = "warn"
        configured_level = str(state.get("level") or "info").strip().lower()
        if TRACE_LEVELS.get(normalized_level, 20) < TRACE_LEVELS.get(configured_level, 20):
            return
        configured_types = _normalize_trace_types(state.get("types"))
        if "all" not in configured_types and normalized_type not in configured_types and normalized_level != "error":
            return
        record = {
            "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": normalized_level,
            "type": normalized_type,
            "event": str(event or ""),
            **redact_sensitive_value(dict(fields or {})),
        }
        try:
            trace_path = Path(str(state.get("path") or DEFAULT_TRACE_PATH))
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError:
            return

    # Purpose: Execute one raw Tier HTTP request and preserve upstream status for Dashboard proxying.
    # Inputs: Method, origin-relative path, optional JSON object, and positive timeout.
    # Outputs: HTTP status and decoded JSON object, including typed upstream error bodies.
    def _http_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None,
        *,
        timeout: float,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self._server_url}{path}"
        body = None if method == "GET" else json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                raw_body = response.read()
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            raw_body = exc.read()
        decoded = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        if not isinstance(decoded, dict):
            raise ValueError(f"Tier HTTP response must be a JSON object: {method} {path}")
        return status, decoded

    # Purpose: Execute one Tier GET and reject non-success HTTP status.
    # Inputs: Origin-relative path and positive timeout.
    # Outputs: Decoded JSON object.
    def _http_get(self, path: str, timeout: float = CONNECT_TIMEOUT_SECONDS) -> dict[str, Any]:
        status, payload = self.proxy_request("GET", path, timeout=timeout)
        if status >= 400:
            raise RuntimeError(f"Tier HTTP GET failed with status {status}: {path}")
        return payload

    # Purpose: Execute one Tier POST and reject non-success HTTP status.
    # Inputs: Origin-relative path, JSON object, and positive timeout.
    # Outputs: Decoded JSON object.
    def _http_post(
        self,
        path: str,
        data: dict[str, Any],
        timeout: float = POLL_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        status, payload = self.proxy_request("POST", path, data, timeout=timeout)
        if status >= 400:
            raise RuntimeError(f"Tier HTTP POST failed with status {status}: {path}")
        return payload


# =============================================================================
# 数据模型
# =============================================================================

# 用途：
# - 描述不走 role_tier_map 的跨 Tier fallback 调用请求
# 输入：
# - prompt/project/tier_priority/stage/phase/task/temperature
# 输出：
# - 可序列化给 /escalate 的请求对象
class TierEscalationRequest:
    def __init__(
        self,
        prompt: str,
        project_name: str,
        tier_priority: list[str] | None = None,
        stage_name: str = "",
        phase_name: str = "",
        task_id: str = "",
        task_key: str = "",
        temperature: float = 0.1,
    ) -> None:
        self.prompt = prompt
        self.project_name = project_name
        self.tier_priority = tier_priority or ["Senior", "Junior", "Worker", "Associate", "Engineer", "Executor"]
        self.stage_name = stage_name
        self.phase_name = phase_name
        self.task_id = task_id
        self.task_key = task_key
        self.temperature = temperature


# =============================================================================
# 序列化辅助
# =============================================================================

def _request_dict(req: TierCallRequest) -> dict[str, Any]:
    payload = {
        "role_name": req.role_name,
        "prompt": req.prompt,
        "project_name": req.project_name,
        "stage_name": req.stage_name,
        "phase_name": req.phase_name,
        "task_id": req.task_id,
        "task_key": req.task_key,
        "temperature": req.temperature,
        "timeout_seconds": req.timeout_seconds,
        "metadata": dict(req.metadata or {}),
    }
    if str(req.prompt_path or "").strip():
        payload["prompt_path"] = str(req.prompt_path or "").strip()
        payload["prompt"] = ""
    if str(req.response_path or "").strip():
        payload["response_path"] = str(req.response_path or "").strip()
    if str(req.raw_response_path or "").strip():
        payload["raw_response_path"] = str(req.raw_response_path or "").strip()
    error_response_path = _resolve_error_response_path(
        response_path=str(req.response_path or "").strip(),
        requested_path=str(req.error_response_path or "").strip(),
    )
    if error_response_path:
        payload["error_response_path"] = error_response_path
    return payload


# 用途：
# - 为 file mode 调用确定错误 sidecar 路径，避免正常 response 文件承载 transport/backend 错误
# 输入：
# - response_path: 正常业务 response 文件路径
# - requested_path: 调用方显式传入的错误 sidecar 路径
# 输出：
# - 可传给 tier server 的 error_response_path；无法确定时为空字符串
def _resolve_error_response_path(*, response_path: str, requested_path: str = "") -> str:
    explicit_path = str(requested_path or "").strip()
    if explicit_path:
        return explicit_path
    normalized_response_path = str(response_path or "").strip()
    if not normalized_response_path:
        return ""
    path = Path(normalized_response_path)
    if path.suffix:
        return str(path.with_suffix(".error.json"))
    return f"{normalized_response_path}.error.json"


# 用途：
# - 根据环境变量和可选 replay map 为当前 Role 调用选择 fixture response 文件
# 输入：
# - payload/metadata/role_name: 当前调用请求和上下文
# 输出：
# - 命中的本地 response Path；未启用或过滤不匹配时返回 None
def _resolve_replay_source_path(
    *,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    role_name: str,
) -> Path | None:
    replay_entry = _matching_replay_map_entry(payload=payload, metadata=metadata, role_name=role_name)
    if replay_entry:
        return _resolve_existing_replay_path(str(replay_entry), metadata)
    replay_path = str(os.environ.get(REPLAY_RESPONSE_PATH_ENV) or "").strip()
    if not replay_path:
        return None
    if not _replay_env_filters_match(payload=payload, metadata=metadata, role_name=role_name):
        return None
    return _resolve_existing_replay_path(replay_path, metadata)


# 用途：
# - 从 replay map 中查找当前调用对应的 response fixture
# 输入：
# - payload/metadata/role_name: 当前调用请求和上下文
# 输出：
# - 命中的 response path 字符串；没有命中时返回空字符串
def _matching_replay_map_entry(
    *,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    role_name: str,
) -> str:
    map_path = str(os.environ.get(REPLAY_MAP_PATH_ENV) or "").strip()
    if not map_path:
        return ""
    resolved_map_path = _resolve_existing_replay_path(map_path, metadata)
    if resolved_map_path is None:
        return ""
    try:
        raw_map = json.loads(resolved_map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    default_response_path = ""
    entries = raw_map.get("responses") if isinstance(raw_map, dict) else raw_map
    if isinstance(entries, dict):
        default_response_path = str(entries.get("default") or "").strip()
        entries = [
            {**({"match_key": key} if key != "default" else {}), "response_path": value}
            for key, value in entries.items()
            if key != "default"
        ]
    if not isinstance(entries, list):
        return ""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if not _replay_entry_matches(entry=entry, payload=payload, metadata=metadata, role_name=role_name):
            continue
        response_path = str(entry.get("response_path") or entry.get("content_file") or entry.get("path") or "").strip()
        if response_path:
            return response_path
    if default_response_path:
        return default_response_path
    if isinstance(raw_map, dict):
        return str(raw_map.get("default") or "").strip()
    return ""


# 用途：
# - 判断 replay map 的单条 entry 是否匹配当前调用
# 输入：
# - entry/payload/metadata/role_name: map entry 与当前调用上下文
# 输出：
# - True 表示该 entry 可用于当前调用
def _replay_entry_matches(
    *,
    entry: dict[str, Any],
    payload: dict[str, Any],
    metadata: dict[str, Any],
    role_name: str,
) -> bool:
    match_key = str(entry.get("match_key") or "").strip()
    prompt_name = str(metadata.get("prompt_name") or payload.get("prompt_name") or "").strip()
    task_id = str(metadata.get("task_id") or payload.get("task_id") or "").strip()
    if match_key and match_key not in {
        role_name,
        prompt_name,
        task_id,
        f"{task_id}|{prompt_name}",
        f"{task_id}|{role_name}",
        f"{role_name}|{prompt_name}",
        f"{task_id}|{prompt_name}|{role_name}",
    }:
        return False
    checks = {
        "role_name": role_name,
        "prompt_name": prompt_name,
        "task_id": task_id,
        "task_key": str(metadata.get("task_key") or payload.get("task_key") or "").strip(),
        "stage_name": str(metadata.get("stage_name") or payload.get("stage_name") or "").strip(),
        "phase_name": str(metadata.get("phase_name") or payload.get("phase_name") or "").strip(),
    }
    for key, current_value in checks.items():
        expected_value = str(entry.get(key) or "").strip()
        if expected_value and expected_value != current_value:
            return False
    return True


# 用途：
# - 判断全局 replay 环境变量 filter 是否允许当前调用使用单个 response fixture
# 输入：
# - payload/metadata/role_name: 当前调用请求和上下文
# 输出：
# - True 表示 filter 为空或全部命中
def _replay_env_filters_match(
    *,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    role_name: str,
) -> bool:
    filters = {
        REPLAY_ROLE_ENV: role_name,
        REPLAY_PROMPT_NAME_ENV: str(metadata.get("prompt_name") or payload.get("prompt_name") or "").strip(),
        REPLAY_TASK_ID_ENV: str(metadata.get("task_id") or payload.get("task_id") or "").strip(),
    }
    for env_name, current_value in filters.items():
        expected_value = str(os.environ.get(env_name) or "").strip()
        if expected_value and expected_value != current_value:
            return False
    return True


# 用途：
# - 将 replay 配置中的路径解析为存在的本地文件路径
# 输入：
# - raw_path: 环境变量或 map 中配置的 response 文件路径
# - metadata: 当前调用 metadata，用于解析 workspace-relative path
# 输出：
# - 存在的 Path；路径为空或不存在时返回 None
def _resolve_existing_replay_path(raw_path: str, metadata: dict[str, Any]) -> Path | None:
    normalized_path = str(raw_path or "").strip()
    if not normalized_path:
        return None
    candidate = Path(normalized_path).expanduser()
    if not candidate.is_absolute():
        workspace_root_text = str(metadata.get("workspace_root") or "").strip()
        workspace_root = Path(workspace_root_text).expanduser() if workspace_root_text else Path.cwd()
        candidate = workspace_root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate
    if not resolved.exists() or not resolved.is_file():
        return None
    return resolved


# 用途：
# - 把 replay fixture 正文写入调用方声明的 response_path，模拟 tier file mode 回写
# 输入：
# - requested_path/content/metadata: 调用方期望路径、fixture 正文和 workspace 上下文
# 输出：
# - 已写入的 response path 字符串；未声明 response_path 时返回空字符串
def _write_replay_response_file(
    *,
    requested_path: str,
    content: str,
    metadata: dict[str, Any],
) -> str:
    target = _resolve_output_path(requested_path, metadata)
    if target is None:
        return ""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="")
    return str(target)


# 用途：
# - 写入 replay 模式的 raw_response_path 审计文件，便于确认本次调用没有走真实 Tier
# 输入：
# - requested_path/replay_source/content/metadata/role_name/prompt_name: 输出路径和 replay 上下文
# 输出：
# - 已写入的 raw response path 字符串；未声明 raw_response_path 时返回空字符串
def _write_replay_raw_response_file(
    *,
    requested_path: str,
    replay_source: Path,
    content: str,
    metadata: dict[str, Any],
    role_name: str,
    prompt_name: str,
) -> str:
    target = _resolve_output_path(requested_path, metadata)
    if target is None:
        return ""
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "debug_replay": True,
        "source_response_path": str(replay_source),
        "role_name": str(role_name or "").strip(),
        "prompt_name": str(prompt_name or "").strip(),
        "execution_level": str(metadata.get("execution_level") or "").strip(),
        "role_profile": str(metadata.get("role_profile") or "").strip(),
        "task_id": str(metadata.get("task_id") or "").strip(),
        "content_chars": len(content),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(target)


# 用途：
# - 将调用方声明的输出路径解析为本地可写 Path
# 输入：
# - requested_path/metadata: response_path 或 raw_response_path 与 workspace 上下文
# 输出：
# - 可写 Path；路径为空时返回 None
def _resolve_output_path(requested_path: str, metadata: dict[str, Any]) -> Path | None:
    normalized_path = str(requested_path or "").strip()
    if not normalized_path:
        return None
    target = Path(normalized_path).expanduser()
    if target.is_absolute():
        return target
    workspace_root_text = str(metadata.get("workspace_root") or "").strip()
    workspace_root = Path(workspace_root_text).expanduser() if workspace_root_text else Path.cwd()
    return workspace_root / target


# 用途：
# - 规范化 trace 类型过滤条件
# 输入：
# - raw_types: 字符串、列表或集合形式的类型配置
# 输出：
# - 小写类型集合；空输入时返回空集合
def _normalize_trace_types(raw_types: Any) -> set[str]:
    if isinstance(raw_types, str):
        parts = raw_types.split(",")
    elif isinstance(raw_types, (list, tuple, set)):
        parts = list(raw_types)
    else:
        parts = []
    return {str(item or "").strip().lower() for item in parts if str(item or "").strip()}


# 用途：
# - 从 client 请求 payload 中抽取可记录的诊断字段，避免写入 prompt 正文
# 输入：
# - request_data: 即将提交给 tier server 的请求 JSON
# 输出：
# - role/project/stage/phase/task/prompt 长度等 trace 元数据
def _request_trace_fields(request_data: dict[str, Any]) -> dict[str, Any]:
    metadata = request_data.get("metadata") if isinstance(request_data.get("metadata"), dict) else {}
    prompt = str(request_data.get("prompt") or "")
    return {
        "client_request_id": str(metadata.get("client_request_id") or ""),
        "role_name": str(request_data.get("role_name") or ""),
        "project_name": str(request_data.get("project_name") or metadata.get("project_name") or ""),
        "stage_name": str(request_data.get("stage_name") or metadata.get("stage_name") or ""),
        "phase_name": str(request_data.get("phase_name") or metadata.get("phase_name") or ""),
        "task_id": str(request_data.get("task_id") or metadata.get("task_id") or ""),
        "task_key": str(request_data.get("task_key") or metadata.get("task_key") or ""),
        "prompt_chars": len(prompt),
        "prompt_path": str(request_data.get("prompt_path") or ""),
        "response_path": str(request_data.get("response_path") or ""),
        "raw_response_path": str(request_data.get("raw_response_path") or ""),
        "error_response_path": str(request_data.get("error_response_path") or ""),
    }


# 用途：
# - 计算 client 等待 server job 完成的 deadline，避免与 backend 执行 timeout 同秒竞争
# 输入：
# - request_data: 即将提交给 tier server 的调用请求 JSON
# 输出：
# - 本次 polling 最大等待秒数
def _poll_timeout_for_request(request_data: dict[str, Any]) -> float:
    metadata = request_data.get("metadata") if isinstance(request_data.get("metadata"), dict) else {}
    raw_timeout = request_data.get("timeout_seconds") or metadata.get("timeout_seconds")
    try:
        backend_timeout = float(raw_timeout or DEFAULT_BACKEND_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        backend_timeout = DEFAULT_BACKEND_TIMEOUT_SECONDS
    return max(POLL_TIMEOUT_SECONDS, backend_timeout + POLL_TIMEOUT_BUFFER_SECONDS)


# 用途：
# - 根据 busy 已等待时长计算退避间隔，避免长期 busy 时高频重提请求
# 输入：
# - elapsed_seconds/retry_count/initial_seconds: 已等待秒数、重试次数和初始退避秒数
# 输出：
# - 当前 busy retry 应等待的秒数，最大 600 秒
def _busy_retry_schedule_seconds(*, elapsed_seconds: float, retry_count: int, initial_seconds: float) -> float:
    try:
        initial = max(0.0, float(initial_seconds))
    except (TypeError, ValueError):
        initial = BUSY_RETRY_INTERVAL_SECONDS
    try:
        elapsed = max(0.0, float(elapsed_seconds))
    except (TypeError, ValueError):
        elapsed = 0.0
    _ = int(retry_count or 0)
    if elapsed < 60.0:
        delay = max(initial, 1.0)
    elif elapsed < 600.0:
        delay = 5.0
    elif elapsed < 1800.0:
        delay = 30.0
    elif elapsed < 7200.0:
        delay = 120.0
    else:
        delay = BUSY_MAX_RETRY_INTERVAL_SECONDS
    return min(BUSY_MAX_RETRY_INTERVAL_SECONDS, delay)


def _escalation_request_dict(req: TierEscalationRequest) -> dict[str, Any]:
    return {
        "prompt": req.prompt,
        "project_name": req.project_name,
        "tier_priority": req.tier_priority,
        "stage_name": req.stage_name,
        "phase_name": req.phase_name,
        "task_id": req.task_id,
        "task_key": req.task_key,
        "temperature": req.temperature,
    }


def _result_from_dict(r: dict[str, Any]) -> TierCallResult:
    return TierCallResult(
        ok=bool(r.get("ok", False)),
        content=str(r.get("content", "")),
        backend=str(r.get("backend", "")),
        account=str(r.get("account", "")),
        model_name=str(r.get("model_name", "")),
        backend_type=str(r.get("backend_type", "")),
        tier=str(r.get("tier", "")),
        tier_priority=int(r.get("tier_priority", 0)),
        latency_ms=float(r.get("latency_ms", 0)),
        token_usage=dict(r.get("token_usage", {})),
        is_fallback=bool(r.get("is_fallback", False)),
        fallback_count=int(r.get("fallback_count", 0)),
        raw_response=dict(r.get("raw_response", {})) if isinstance(r.get("raw_response"), dict) else {},
        artifact_paths=dict(r.get("artifact_paths", {})) if isinstance(r.get("artifact_paths"), dict) else {},
        error_code=int(r.get("error_code", 0)),
        error_message=str(r.get("error_message", "")),
    )


# 用途：
# - 当调用方声明 response_type=json 时，在 TierClient 层统一解析模型 JSON 返回
# 输入：
# - response_payload: invoke_role 即将返回给业务层的结果字典
# 输出：
# - 原地补充 parsed_json/parse_error；解析失败时将 ok 标记为 False
def _attach_parsed_json_response(response_payload: dict[str, Any]) -> None:
    response_payload["parsed_json"] = {}
    response_payload["parsed_json_result"] = {}
    response_payload["parse_error"] = ""
    if not bool(response_payload.get("ok")):
        return
    response_text = _tier_response_text(response_payload)
    try:
        parsed = _RESPONSE_PARSER.parse_json(response_text)
    except ParseError as exc:
        error_message = f"json response parse failed: {exc}"
        response_payload["ok"] = False
        response_payload["error"] = error_message
        response_payload["parse_error"] = error_message
        return
    response_payload["parsed_json"] = parsed
    nested_result = parsed.get("result") if isinstance(parsed, dict) else None
    if isinstance(nested_result, str) and nested_result.strip().startswith("{"):
        try:
            response_payload["parsed_json_result"] = _RESPONSE_PARSER.parse_json(nested_result)
        except ParseError:
            response_payload["parsed_json_result"] = {}


# 用途：
# - 为统一 JSON parser 读取 Tier 调用正文，兼容 content mode 和 file mode response_path
# 输入：
# - response_payload: invoke_role 返回结构
# 输出：
# - 模型响应正文；读取失败时返回空字符串让 parser 给出统一错误
def _tier_response_text(response_payload: dict[str, Any]) -> str:
    content = str(response_payload.get("content") or "")
    if content:
        return content
    artifact_paths = response_payload.get("artifact_paths")
    if not isinstance(artifact_paths, dict):
        return ""
    response_path = str(artifact_paths.get("response_path") or "").strip()
    if not response_path:
        return ""
    try:
        return Path(response_path).read_text(encoding="utf-8")
    except OSError:
        return ""


# 用途：
# - 读取环境变量中的秒数配置，缺失或非法时回退到默认值
# 输入：
# - env_name: 环境变量名
# - default: 默认秒数
# 输出：
# - 非负浮点秒数
def _env_float(env_name: str, default: float) -> float:
    raw_value = str(os.environ.get(env_name) or "").strip()
    if not raw_value:
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default
