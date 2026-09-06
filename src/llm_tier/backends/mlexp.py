from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_tier.backends import register_backend
from llm_tier.backends.base import BaseBackendClient
from llm_tier.exceptions import BackendCallError


DEFAULT_MLEXP_BASE_URL = "http://192.168.1.10:8001"
DEFAULT_MLEXP_HTTP_PORT = 8001
DEFAULT_MLEXP_TIMEOUT_SECONDS = 60
DEFAULT_MLEXP_AI_BACKEND = "ollama"
DEFAULT_MLEXP_AI_MODEL_NAME = "gemma4:latest"
DEFAULT_MLEXP_MODEL_NAME = "ollama/gemma4"
DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT = ""


# 用途：
# - 表达 MLEXP backend HTTP 调用失败
# 输入：
# - message: 可展示的失败原因
# 输出：
# - 可由 tier probe 或 system_testing execution 捕获并写入报告的异常
class MlexpBackendError(RuntimeError):
    """Raised when an MLEXP job cannot satisfy the Tier backend contract."""


# 用途：
# - 表达 MLEXP system-test job 的提交结果
# 输入：
# - job_id/external_id/status/status_url/artifacts_url/raw_response: MLEXP 返回的 job 元数据
# 输出：
# - Slinky 可保存和轮询的 job 句柄
@dataclass(frozen=True)
class MlexpSystemTestJob:
    job_id: str
    external_id: str
    status: str
    status_url: str = ""
    artifacts_url: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


# 用途：
# - 表达 Slinky project case report 在本地 workspace 中的固定位置
# 输入：
# - project_name/case_id/root/subdir: 项目名、case 稳定身份、system test 根目录和 report 子目录
# 输出：
# - 可解析 report.json 的位置对象
@dataclass(frozen=True)
class MlexpProjectCaseReportLocation:
    project_name: str
    case_id: str
    root: str = "test/system"
    subdir: str = "mlexp"

    # 用途：
    # - 计算本地 report.json 路径
    # 输入：
    # - workspace_root: Slinky 本地 workspaces 根目录
    # 输出：
    # - report.json 的绝对或相对 Path
    def report_path(self, *, workspace_root: str | Path) -> Path:
        return (
            Path(workspace_root)
            / self.project_name
            / self.root
            / self.case_id
            / self.subdir
            / "report.json"
        )


# 用途：
# - 从 backend 的 SSH 配置推导同一台机器上的 MLEXP HTTP 服务地址
# 输入：
# - ssh: backend 配置中的 SSH 字典；ssh.port 是登录端口，不是 MLEXP HTTP 端口
# 输出：
# - `http://host:8001` 形式的 base_url；缺少 host 时返回空字符串
def _mlexp_base_url_from_ssh(ssh: Any) -> str:
    if not isinstance(ssh, dict):
        return ""
    host = str(ssh.get("host") or "").strip()
    if not host:
        return ""
    return f"http://{host}:{DEFAULT_MLEXP_HTTP_PORT}"


# 用途：
# - 作为 MLEXP system testing backend 在 llm_tier 中的统一 backend client
# 输入：
# - base_url/timeout_seconds: MLEXP HTTP 服务地址和请求超时
# 输出：
# - 可被 llm_tier probe/dashboard 和 system_testing execution 复用的 backend client
class MlexpClient(BaseBackendClient):
    # 用途：
    # - 初始化 MLEXP backend client
    # 输入：
    # - base_url: MLEXP HTTP 服务根地址
    # - timeout_seconds: 默认 HTTP 请求超时秒数
    # 输出：
    # - 已归一化 base_url 的 MlexpClient
    def __init__(
        self,
        base_url: str = "",
        timeout_seconds: int = DEFAULT_MLEXP_TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> None:
        resolved_base_url = str(base_url or "").strip() or _mlexp_base_url_from_ssh(kwargs.get("ssh"))
        self._base_url = str(resolved_base_url or DEFAULT_MLEXP_BASE_URL).rstrip("/")
        self._timeout_seconds = int(timeout_seconds or DEFAULT_MLEXP_TIMEOUT_SECONDS)
        self._remote_workspace_root = str(kwargs.get("remote_workspace_root") or "").rstrip("/")
        self._poll_interval_seconds = float(kwargs.get("poll_interval_seconds") or 5.0)

    # 用途：
    # - 返回注册表中的 backend 名称
    # 输入：
    # - 无
    # 输出：
    # - backend 标识字符串
    @property
    def backend(self) -> str:
        return "mlexp"

    # 用途：
    # - 返回 backend 类型，供 dashboard 和统计展示
    # 输入：
    # - 无
    # 输出：
    # - 固定类型 `MLP`
    @property
    def backend_type(self) -> str:
        return "MLP"

    # 用途：
    # - 返回 MLEXP backend 的展示模型名集合
    # 输入：
    # - 无
    # 输出：
    # - 供配置和 dashboard 展示的模型名列表
    def supported_models(self) -> list[str]:
        return [DEFAULT_MLEXP_MODEL_NAME]

    # 用途：
    # - 执行一次 MLEXP backend 健康探测；llm_tier probe 会调用该方法
    # 输入：
    # - model_name/prompt/system_prompt/temperature/timeout_seconds/metadata: BaseBackendClient 统一调用参数
    # 输出：
    # - 与 LLM backend call 兼容的结果字典；content 为 "OK" 或健康摘要
    def call(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = DEFAULT_MLEXP_TIMEOUT_SECONDS,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = (system_prompt, temperature, kwargs)
        metadata = metadata or {}
        normalized_prompt = str(prompt or "").strip()
        role_name = str(metadata.get("role") or metadata.get("role_name") or "").strip()
        is_probe = normalized_prompt == "Reply with OK." or role_name == "probe"
        started_at = time.time()
        if not is_probe:
            return self._call_system_test_job(
                model_name=model_name,
                prompt=prompt,
                role_name=role_name,
                timeout_seconds=timeout_seconds or self._timeout_seconds,
                metadata=metadata,
                started_at=started_at,
            )
        health = self.health(timeout_seconds=timeout_seconds or self._timeout_seconds)
        runtime = self.runtime(timeout_seconds=timeout_seconds or self._timeout_seconds)
        latency_ms = (time.time() - started_at) * 1000
        ok = bool(health.get("ok", False))
        if not ok:
            raise BackendCallError(self.backend, f"MLEXP health check failed: {health}")
        ai_backend, _ai_model_name = _parse_mlexp_model_selector(model_name)
        readiness_backend = _normalize_mlexp_ai_backend(ai_backend)
        readiness_by_backend = health.get("llm_backends")
        if not isinstance(readiness_by_backend, dict):
            raise BackendCallError(self.backend, "MLEXP health response missing internal LLM readiness")
        readiness = readiness_by_backend.get(readiness_backend)
        if not isinstance(readiness, dict):
            raise BackendCallError(
                self.backend,
                f"MLEXP health response missing readiness for internal LLM Backend: {readiness_backend}",
            )
        if not bool(readiness.get("ready", False)):
            reason = str(readiness.get("reason") or "unavailable")
            raise BackendCallError(
                self.backend,
                f"MLEXP internal LLM Backend unavailable: {readiness_backend}: {reason}",
            )
        content = "OK"
        if isinstance(runtime, dict):
            running = runtime.get("running", 0)
            queued = runtime.get("queued", 0)
            capacity = runtime.get("capacity", 0)
            content = f"OK running={running} queued={queued} capacity={capacity}"
        return {
            "ok": True,
            "content": content,
            "model_name": DEFAULT_MLEXP_MODEL_NAME,
            "latency_ms": latency_ms,
            "token_usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "raw_response": {
                "health": health,
                "runtime": runtime,
            },
            "error_code": 0,
            "error_message": "",
        }

    # 用途：
    # - 将普通 Tier call 封装为 MLEXP `/api/system-test/run` 调用
    # 输入：
    # - model_name/prompt/role_name/timeout_seconds/metadata/started_at: Tier 调用上下文
    # 输出：
    # - 与 LLM backend call 兼容的结果字典；content 为 MLEXP job 终态摘要 JSON
    def _call_system_test_job(
        self,
        *,
        model_name: str,
        prompt: str,
        role_name: str,
        timeout_seconds: int,
        metadata: dict[str, str],
        started_at: float,
    ) -> dict[str, Any]:
        ai_backend, ai_model_name = _parse_mlexp_model_selector(model_name)
        project_name = str(metadata.get("project_name") or metadata.get("workspace_name") or "default").strip()
        stage_name = str(metadata.get("stage_name") or "system_testing").strip()
        phase_name = str(metadata.get("phase_name") or "execution").strip()
        task_id = str(metadata.get("task_id") or "").strip()
        task_key = str(metadata.get("task_key") or "").strip()
        case_id = _resolve_mlexp_case_id(task_id=task_id, task_key=task_key, prompt=prompt)
        report_subdir = "report/preflight" if _is_preflight_call(role_name, phase_name) else "mlexp"
        remote_workspace_root = str(metadata.get("remote_workspace_root") or metadata.get("REMOTE_WORKSPACE_ROOT") or self._remote_workspace_root).rstrip("/")
        agent_kind = "environment_report" if phase_name == "environment" else ""
        try:
            case_payload = metadata.get("mlexp_case_payload")
            mlexp_options = metadata.get("mlexp_options")
            if isinstance(case_payload, dict):
                options = dict(mlexp_options or {}) if isinstance(mlexp_options, dict) else {}
                app_files = metadata.get("mlexp_app_files")
                job = self.submit_case_payload(
                    project_name=project_name,
                    case_payload=case_payload,
                    case_id=case_id,
                    remote_workspace_root=str(options.get("remote_workspace_root") or remote_workspace_root),
                    report_root=str(options.get("report_root") or "test/system/case"),
                    report_subdir=str(options.get("report_subdir") or report_subdir),
                    details_dir=str(options.get("details_dir") or "details"),
                    ai_backend=str(options.get("ai_backend") or ai_backend),
                    model_name=str(options.get("model_name") or ai_model_name),
                    ai_mode=str(options.get("ai_mode") or "full"),
                    app_files=dict(app_files) if isinstance(app_files, dict) else None,
                    environment_setup=(
                        dict(options.get("environment_setup"))
                        if isinstance(options.get("environment_setup"), dict)
                        else None
                    ),
                    phase_name=phase_name,
                    task_id=task_id,
                    task_key=task_key,
                    external_id=str(options.get("external_id") or ""),
                    timeout_seconds=timeout_seconds,
                )
            else:
                payload = build_description_only_system_test_payload(
                    project_name=project_name,
                    case_id=case_id,
                    name=f"{role_name or 'engineer'} {case_id}",
                    description=prompt,
                    expected="MLEXP should complete the requested system-testing engineer task and return an auditable report.",
                    remote_workspace_root=remote_workspace_root,
                    report_subdir=report_subdir,
                    ai_backend=ai_backend,
                    model_name=ai_model_name,
                    stage_name=stage_name,
                    phase_name=phase_name,
                    task_id=task_id,
                    task_key=task_key,
                    agent_kind=agent_kind,
                )
                if report_subdir == "report/preflight":
                    payload["options"]["preflight"] = True
                job = self.submit_system_test(payload, timeout_seconds=timeout_seconds)
            terminal = self.wait_for_job(
                job.job_id,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=self._poll_interval_seconds,
            )
        except TimeoutError as exc:
            cancel_error = ""
            if "job" in locals():
                try:
                    self.cancel_job(job.job_id, timeout_seconds=timeout_seconds)
                except Exception as cancel_exc:
                    cancel_error = f"; cancellation failed: {cancel_exc}"
            raise BackendCallError(self.backend, f"MLEXP job timeout: {exc}{cancel_error}") from exc
        except MlexpBackendError as exc:
            raise BackendCallError(self.backend, str(exc)) from exc

        status = str(terminal.get("status") or "").strip().lower()
        if status != "passed":
            raise BackendCallError(self.backend, f"MLEXP job ended with protocol status {status}: {terminal}")
        latency_ms = (time.time() - started_at) * 1000
        usage = _usage_from_mlexp_terminal(terminal)
        content_payload: dict[str, Any] = {
            "ok": True,
            "backend": "mlexp",
            "model": str(model_name or "").strip() or f"{ai_backend}/{ai_model_name}",
            "job_id": job.job_id,
            "job_status": terminal.get("status"),
            "submit": job.raw_response,
            "terminal": terminal,
        }
        report_payload = self._read_job_output_json(job.job_id, "output/summary.json")
        if not report_payload:
            raise BackendCallError(self.backend, "MLEXP job passed without a committed Artifact report")
        content_payload["report"] = report_payload
        content = json.dumps(report_payload, ensure_ascii=False, indent=2)
        return {
            "ok": True,
            "content": content,
            "model_name": str(model_name or "").strip() or f"{ai_backend}/{ai_model_name}",
            "latency_ms": latency_ms,
            "token_usage": usage,
            "raw_response": content_payload,
            "error_code": 0,
            "error_message": "",
        }

    # 用途：
    # - 检查 MLEXP backend 健康状态
    # 输入：
    # - timeout_seconds: 可选请求超时秒数
    # 输出：
    # - `/health` 响应 JSON
    def health(self, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        return self._request_json("GET", "/health", timeout_seconds=timeout_seconds)

    # 用途：
    # - 查询 MLEXP backend 当前运行容量
    # 输入：
    # - timeout_seconds: 可选请求超时秒数
    # 输出：
    # - `/api/runtime` 响应 JSON
    def runtime(self, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        return self._request_json("GET", "/api/runtime", timeout_seconds=timeout_seconds)

    # 用途：
    # - 提交 description-only Slinky v1 AI system-test case
    # 输入：
    # - project_name/case_id/name/description/expected: Slinky case 基本信息
    # - remote_workspace_root/ai_backend/model_name: MLEXP 侧 project workspace root 和 AI 后端选择
    # 输出：
    # - MlexpSystemTestJob 句柄
    def submit_description_only_case(
        self,
        *,
        project_name: str,
        case_id: str,
        name: str,
        description: str,
        expected: str,
        remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT,
        ai_backend: str = DEFAULT_MLEXP_AI_BACKEND,
        model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME,
        phase_name: str = "manual",
        task_id: str = "",
        timeout_seconds: int | None = None,
    ) -> MlexpSystemTestJob:
        payload = build_description_only_system_test_payload(
            project_name=project_name,
            case_id=case_id,
            name=name,
            description=description,
            expected=expected,
            remote_workspace_root=remote_workspace_root,
            ai_backend=ai_backend,
            model_name=model_name,
            phase_name=phase_name,
            task_id=task_id,
        )
        response = self._request_json(
            "POST",
            "/api/system-test/run",
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
        return self._parse_submit_response(response)

    # 用途：
    # - 提交已经构造好的 Slinky v1 case，并保持 MLEXP report 落盘约定
    # 输入：
    # - project_name/case_payload/case_id/external_id: 项目名、case JSON、case 稳定身份和本次执行幂等身份
    # - remote_workspace_root/ai_backend/model_name/ai_mode: MLEXP 执行环境与 AI 选项
    # 输出：
    # - MlexpSystemTestJob 句柄
    def submit_case_payload(
        self,
        *,
        project_name: str,
        case_payload: dict[str, Any],
        case_id: str = "",
        remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT,
        report_root: str = "test/system",
        report_subdir: str = "mlexp",
        details_dir: str = "details",
        ai_backend: str = DEFAULT_MLEXP_AI_BACKEND,
        model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME,
        ai_mode: str = "full",
        app_files: dict[str, str] | None = None,
        environment_setup: dict[str, Any] | None = None,
        phase_name: str = "execution",
        task_id: str = "",
        task_key: str = "",
        external_id: str = "",
        timeout_seconds: int | None = None,
    ) -> MlexpSystemTestJob:
        payload = build_system_test_payload_from_case(
            project_name=project_name,
            case_payload=case_payload,
            case_id=case_id,
            remote_workspace_root=remote_workspace_root,
            report_root=report_root,
            report_subdir=report_subdir,
            details_dir=details_dir,
            ai_backend=ai_backend,
            model_name=model_name,
            ai_mode=ai_mode,
            app_files=app_files,
            environment_setup=environment_setup,
            phase_name=phase_name,
            task_id=task_id,
            task_key=task_key,
            external_id=external_id,
        )
        response = self._request_json(
            "POST",
            "/api/system-test/run",
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
        return self._parse_submit_response(response)

    # 用途：
    # - 提交 Slinky v1 system-test job
    # 输入：
    # - payload/timeout_seconds: 符合 MLEXP `/api/system-test/run` 的请求体和提交超时
    # 输出：
    # - MlexpSystemTestJob 句柄
    def submit_system_test(
        self,
        payload: dict[str, Any],
        *,
        timeout_seconds: int | None = None,
    ) -> MlexpSystemTestJob:
        response = self._request_json(
            "POST",
            "/api/system-test/run",
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
        return self._parse_submit_response(response)

    # 用途：
    # - 查询 MLEXP job 当前状态
    # 输入：
    # - job_id/timeout_seconds: MLEXP job id 和本次 HTTP 请求超时
    # 输出：
    # - job 状态响应 JSON
    def get_job(self, job_id: str, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        normalized_job_id = self._require_job_id(job_id)
        return self._request_json("GET", f"/api/jobs/{normalized_job_id}", timeout_seconds=timeout_seconds)

    # 用途：
    # - 取消 queued/running MLEXP job
    # 输入：
    # - job_id/timeout_seconds: MLEXP job id 和本次 HTTP 请求超时
    # 输出：
    # - cancel 响应 JSON
    def cancel_job(self, job_id: str, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        normalized_job_id = self._require_job_id(job_id)
        return self._request_json(
            "POST",
            f"/api/jobs/{normalized_job_id}/cancel",
            payload={},
            timeout_seconds=timeout_seconds,
        )

    # 用途：
    # - 查询 MLEXP job 的 artifact manifest
    # 输入：
    # - job_id/timeout_seconds: MLEXP job id 和本次 HTTP 请求超时
    # 输出：
    # - artifacts manifest 响应 JSON
    def get_artifacts(self, job_id: str, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        normalized_job_id = self._require_job_id(job_id)
        return self._request_json(
            "GET",
            f"/api/jobs/{normalized_job_id}/artifacts",
            timeout_seconds=timeout_seconds,
        )

    # 用途：
    # - 读取 MLEXP job 内部 workspace 的文本 artifact
    # 输入：
    # - job_id/path/timeout_seconds: MLEXP job id、workspace 内相对路径和本次 HTTP 请求超时
    # 输出：
    # - `/api/workspace/{job_id}/file` 响应 JSON
    def get_workspace_file(self, job_id: str, path: str, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        normalized_job_id = self._require_job_id(job_id)
        encoded_path = urllib.parse.quote(str(path or "").strip(), safe="/")
        return self._request_json(
            "GET",
            f"/api/workspace/{normalized_job_id}/file?path={encoded_path}",
            timeout_seconds=timeout_seconds,
        )

    # 用途：
    # - 尝试读取 MLEXP job 输出的 JSON artifact
    # 输入：
    # - job_id/path/timeout_seconds: MLEXP job id、JSON artifact 相对路径和本次 HTTP 请求超时
    # 输出：
    # - 解析后的 JSON object；不存在或格式不匹配时返回空 dict
    def _read_job_output_json(self, job_id: str, path: str, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        try:
            payload = self.get_workspace_file(job_id, path, timeout_seconds=timeout_seconds)
        except MlexpBackendError:
            return {}
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            return {}
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    # 用途：
    # - 轮询 MLEXP job 直到终态或超时
    # 输入：
    # - job_id: MLEXP job id
    # - timeout_seconds: 最大等待秒数
    # - poll_interval_seconds: 轮询间隔秒数
    # 输出：
    # - 终态 job 响应 JSON
    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout_seconds: int = 600,
        poll_interval_seconds: float = 5.0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(1, int(timeout_seconds or 600))
        terminal_statuses = {"passed", "failed", "blocked", "error", "cancelled", "interrupted"}
        last_response: dict[str, Any] = {}
        while time.monotonic() < deadline:
            remaining_seconds = max(1, int(deadline - time.monotonic()))
            request_timeout_seconds = max(
                1,
                min(int(self._timeout_seconds or DEFAULT_MLEXP_TIMEOUT_SECONDS), remaining_seconds),
            )
            last_response = self.get_job(job_id, timeout_seconds=request_timeout_seconds)
            status = str(last_response.get("status") or "").strip().lower()
            if status in terminal_statuses:
                return last_response
            time.sleep(max(0.1, float(poll_interval_seconds)))
        raise MlexpBackendError(f"MLEXP job timed out after {timeout_seconds}s: {last_response}")

    # 用途：
    # - 将 MLEXP submit 响应解析成稳定 job 句柄
    # 输入：
    # - response: `/api/system-test/run` 响应 JSON
    # 输出：
    # - MlexpSystemTestJob
    def _parse_submit_response(self, response: dict[str, Any]) -> MlexpSystemTestJob:
        if not bool(response.get("ok", False)):
            raise MlexpBackendError(f"MLEXP system-test submit failed: {response}")
        job_id = str(response.get("job_id") or "").strip()
        if not job_id:
            raise MlexpBackendError(f"MLEXP system-test submit returned no job_id: {response}")
        return MlexpSystemTestJob(
            job_id=job_id,
            external_id=str(response.get("external_id") or ""),
            status=str(response.get("status") or ""),
            status_url=str(response.get("status_url") or ""),
            artifacts_url=str(response.get("artifacts_url") or ""),
            raw_response=response,
        )

    # 用途：
    # - 校验 job id 非空并做 URL path 安全归一
    # 输入：
    # - job_id: 原始 job id
    # 输出：
    # - 可拼入 URL path 的 job id
    def _require_job_id(self, job_id: str) -> str:
        normalized = str(job_id or "").strip()
        if not normalized:
            raise MlexpBackendError("missing MLEXP job_id")
        return urllib.parse.quote(normalized, safe="")

    # 用途：
    # - 发起 MLEXP HTTP JSON 请求并解析响应
    # 输入：
    # - method/path/payload/timeout_seconds: HTTP 方法、路径、请求 JSON 和超时
    # 输出：
    # - 响应 JSON object
    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds or self._timeout_seconds) as response:
                text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            raise MlexpBackendError(f"MLEXP HTTP error {exc.code}: {error_text}") from exc
        except urllib.error.URLError as exc:
            raise MlexpBackendError(f"MLEXP connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise MlexpBackendError(f"MLEXP request timed out after {timeout_seconds or self._timeout_seconds}s") from exc
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise MlexpBackendError(f"MLEXP returned invalid JSON: {text[:500]}") from exc
        if not isinstance(parsed, dict):
            raise MlexpBackendError(f"MLEXP returned non-object JSON: {text[:500]}")
        return parsed


# 用途：
# - 构造 MLEXP `/api/system-test/run` 的 description-only Slinky v1 payload
# 输入：
# - project_name/case_id/name/description/expected: Slinky system test case 信息
# - remote_workspace_root/app_workdir/report_root/report_subdir/details_dir: MLEXP 侧 project workspace 路径和 report 落盘配置
# - ai_backend/model_name: MLEXP 内部 LLM 后端与模型名
# 输出：
# - 可直接提交给 MLEXP 的 JSON payload
def build_description_only_system_test_payload(
    *,
    project_name: str,
    case_id: str,
    name: str,
    description: str,
    expected: str,
    remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT,
    app_workdir: str = ".",
    report_root: str = "test/system",
    report_subdir: str = "mlexp",
    details_dir: str = "details",
    ai_backend: str = DEFAULT_MLEXP_AI_BACKEND,
    model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME,
    stage_name: str = "system_testing",
    phase_name: str = "manual",
    task_id: str = "",
    task_key: str = "",
    external_id: str = "",
    agent_kind: str = "",
) -> dict[str, Any]:
    normalized_project = _require_text(project_name, "project_name")
    normalized_case = _require_text(case_id, "case_id")
    normalized_task_id = task_id or f"{stage_name}::{phase_name}::{normalized_case}"
    normalized_task_key = task_key or normalized_case
    normalized_external_id = (
        external_id
        or f"slinky:{normalized_project}:{stage_name}:{phase_name}:{normalized_case}"
    )
    payload = {
        "mode": "pythontest",
        "external_id": normalized_external_id,
        "project_name": normalized_project,
        "stage_name": stage_name,
        "phase_name": phase_name,
        "task_id": normalized_task_id,
        "task_key": normalized_task_key,
        "options": {
            "ai_mode": "full",
            "backend": ai_backend,
            "model_name": model_name,
        },
        "test_case": {
            "version": "v1",
            "case_id": normalized_case,
            "name": name or normalized_case,
            "mode": "pythontest",
            "description": _require_text(description, "description"),
            "expected": _require_text(expected, "expected"),
        },
    }
    normalized_agent_kind = str(agent_kind or "").strip()
    if normalized_agent_kind:
        payload["options"]["agent_kind"] = normalized_agent_kind
        payload["options"]["agent_prompt"] = _require_text(description, "description")
        payload["app_deploy"] = {"method": "none", "workdir": app_workdir}
        return payload
    normalized_remote_root = str(remote_workspace_root or "").strip().rstrip("/")
    if normalized_remote_root:
        payload["app_deploy"] = {
            "method": "mlexp_workspace",
            "path": f"{normalized_remote_root}/{normalized_project}",
            "workdir": app_workdir,
        }
        payload["report_output"] = {
            "mode": "project_case_dir",
            "root": report_root,
            "case": normalized_case,
            "subdir": report_subdir,
            "details_dir": details_dir,
        }
    else:
        payload["app_deploy"] = {"method": "none", "workdir": app_workdir}
    return payload


# 用途：
# - 从 Slinky v1 case JSON 构造 MLEXP `/api/system-test/run` payload
# 输入：
# - project_name/case_payload/case_id: 项目名、case JSON 和可选 case id
# - remote_workspace_root/app_workdir/report_root/report_subdir/details_dir: MLEXP 侧 project workspace 路径和 report 落盘配置
# - ai_backend/model_name/ai_mode: MLEXP 内部 LLM 后端、模型名和 AI 模式
# 输出：
# - 可直接提交给 MLEXP 的 JSON payload
def build_system_test_payload_from_case(
    *,
    project_name: str,
    case_payload: dict[str, Any],
    case_id: str = "",
    remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT,
    app_workdir: str = ".",
    report_root: str = "test/system",
    report_subdir: str = "mlexp",
    details_dir: str = "details",
    ai_backend: str = DEFAULT_MLEXP_AI_BACKEND,
    model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME,
    ai_mode: str = "full",
    app_files: dict[str, str] | None = None,
    environment_setup: dict[str, Any] | None = None,
    stage_name: str = "system_testing",
    phase_name: str = "execution",
    task_id: str = "",
    task_key: str = "",
    external_id: str = "",
) -> dict[str, Any]:
    normalized_project = _require_text(project_name, "project_name")
    if not isinstance(case_payload, dict):
        raise MlexpBackendError("case_payload must be an object")
    resolved_case_id = _require_text(
        case_id or str(case_payload.get("case_id") or case_payload.get("scenario_id") or ""),
        "case_id",
    )
    normalized_task_id = task_id or f"{stage_name}::{phase_name}::{resolved_case_id}"
    normalized_task_key = task_key or resolved_case_id
    normalized_external_id = (
        external_id
        or f"slinky:{normalized_project}:{stage_name}:{phase_name}:{resolved_case_id}"
    )
    payload = {
        "mode": str(case_payload.get("mode") or "pythontest"),
        "external_id": normalized_external_id,
        "project_name": normalized_project,
        "stage_name": stage_name,
        "phase_name": phase_name,
        "task_id": normalized_task_id,
        "task_key": normalized_task_key,
        "options": {
            "ai_mode": str(ai_mode or "full"),
            "backend": ai_backend,
            "model_name": model_name,
        },
        "test_case": dict(case_payload),
    }
    normalized_remote_root = str(remote_workspace_root or "").strip().rstrip("/")
    if app_files:
        payload["app_deploy"] = {
            "method": "inline",
            "workdir": app_workdir,
            "files": dict(app_files),
        }
        payload["report_output"] = {
            "mode": "project_case_dir",
            "root": report_root,
            "case": resolved_case_id,
            "subdir": report_subdir,
            "details_dir": details_dir,
        }
    elif normalized_remote_root:
        payload["app_deploy"] = {
            "method": "mlexp_workspace",
            "path": f"{normalized_remote_root}/{normalized_project}",
            "workdir": app_workdir,
        }
        payload["report_output"] = {
            "mode": "project_case_dir",
            "root": report_root,
            "case": resolved_case_id,
            "subdir": report_subdir,
            "details_dir": details_dir,
        }
    else:
        payload["app_deploy"] = {
            "method": "none",
            "workdir": app_workdir,
        }
    if environment_setup:
        payload["environment_setup"] = dict(environment_setup)
    return payload


# 用途：
# - 读取 MLEXP 落回 Slinky workspace 的 project case report
# 输入：
# - workspace_root/project_name/case_id/root/subdir: 本地 workspaces 根目录和 case report 定位字段
# 输出：
# - report.json 的解析结果
def read_project_case_report(
    *,
    workspace_root: str | Path,
    project_name: str,
    case_id: str,
    root: str = "test/system",
    subdir: str = "mlexp",
) -> dict[str, Any]:
    location = MlexpProjectCaseReportLocation(
        project_name=project_name,
        case_id=case_id,
        root=root,
        subdir=subdir,
    )
    report_path = location.report_path(workspace_root=workspace_root)
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MlexpBackendError(f"MLEXP project case report not found: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise MlexpBackendError(f"MLEXP project case report is invalid JSON: {report_path}") from exc
    if not isinstance(payload, dict):
        raise MlexpBackendError(f"MLEXP project case report is not an object: {report_path}")
    return payload


# 用途：
# - 从 MLEXP system-test report 中提取 LLM usage 和 call 明细
# 输入：
# - report: `report.json` 或 `details/summary.json` 解析结果
# 输出：
# - 包含 `llm_usage` 和 `llm_calls` 的标准字典
def extract_llm_usage_from_report(report: dict[str, Any]) -> dict[str, Any]:
    usage = report.get("llm_usage")
    calls = report.get("llm_calls")
    if not isinstance(usage, dict):
        usage = {
            "calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "cached_tokens": None,
            "total_tokens": None,
            "prompt_chars": 0,
            "completion_chars": 0,
            "latency_ms": 0,
            "provider_usage_available": False,
            "usage_source": "unavailable",
        }
    if not isinstance(calls, list):
        calls = []
    return {
        "llm_usage": dict(usage),
        "llm_calls": [dict(item) for item in calls if isinstance(item, dict)],
    }


# 用途：
# - 从 MLEXP job 终态响应中提取 Tier 统计需要的 token usage
# 输入：
# - terminal: `/api/jobs/{job_id}` 终态响应
# 输出：
# - Tier backend call 兼容的 token_usage 字典
def _usage_from_mlexp_terminal(terminal: dict[str, Any]) -> dict[str, Any]:
    usage_sources = [
        terminal.get("llm_usage"),
        terminal.get("usage"),
    ]
    report = terminal.get("report")
    llm_calls: list[dict[str, Any]] = []
    if isinstance(report, dict):
        usage_sources.extend([report.get("llm_usage"), report.get("usage")])
        raw_calls = report.get("llm_calls")
        if isinstance(raw_calls, list):
            llm_calls = [dict(item) for item in raw_calls if isinstance(item, dict)]
    for usage in usage_sources:
        if not isinstance(usage, dict):
            continue
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
        call_count = int(usage.get("calls") or len(llm_calls) or 1)
        failed_call_count = _failed_mlexp_llm_call_count(usage=usage, llm_calls=llm_calls)
        return {
            "call_count": max(call_count, 0),
            "failed_call_count": max(failed_call_count, 0),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cached_tokens": int(usage.get("cached_tokens") or usage.get("cache_tokens") or 0),
            "prompt_chars": int(usage.get("prompt_chars") or 0),
            "completion_chars": int(usage.get("completion_chars") or 0),
            "latency_ms": _mlexp_usage_latency_ms(usage=usage, llm_calls=llm_calls, call_count=call_count),
            "provider_usage_available": bool(usage.get("provider_usage_available")),
            "usage_source": str(usage.get("usage_source") or ""),
        }
    return {
        "call_count": 0,
        "failed_call_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "prompt_chars": 0,
        "completion_chars": 0,
        "latency_ms": 0,
        "provider_usage_available": False,
        "usage_source": "unavailable",
    }


# 用途：
# - 统计 MLEXP llm_calls 中失败的内部 LLM 调用数
# 输入：
# - usage: MLEXP llm_usage 聚合字段；llm_calls: 调用明细列表
# 输出：
# - 失败调用数量
def _failed_mlexp_llm_call_count(*, usage: dict[str, Any], llm_calls: list[dict[str, Any]]) -> int:
    explicit = usage.get("failed_calls") or usage.get("fail_calls") or usage.get("failed_count")
    if explicit is not None:
        return int(explicit or 0)
    failed = 0
    for item in llm_calls:
        error = str(item.get("error") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        if error or status in {"error", "failed", "fail", "timeout"}:
            failed += 1
    return failed


# 用途：
# - 将 MLEXP usage latency 转为单次调用平均 latency，供 tier 统一 latency 统计使用
# 输入：
# - usage/llm_calls/call_count: 聚合字段、明细字段和调用数
# 输出：
# - 每次内部 LLM 调用的平均耗时毫秒；缺失时为 0
def _mlexp_usage_latency_ms(
    *,
    usage: dict[str, Any],
    llm_calls: list[dict[str, Any]],
    call_count: int,
) -> float:
    if llm_calls:
        latencies = [float(item.get("latency_ms") or 0) for item in llm_calls if float(item.get("latency_ms") or 0) > 0]
        if latencies:
            return sum(latencies) / len(latencies)
    latency_ms = float(usage.get("latency_ms") or 0)
    if latency_ms > 0 and call_count > 1:
        return latency_ms / call_count
    return latency_ms


# 用途：
# - 将 Tier 中的 MLEXP 模型选择字符串拆成 MLEXP options.backend/model_name
# 输入：
# - model_name: 例如 `go/DeepSeek-V4-Flash`、`ollama/gemma4` 或旧式 `ollama:gemma4`
# 输出：
# - `(ai_backend, ai_model_name)` 二元组
def _parse_mlexp_model_selector(model_name: str) -> tuple[str, str]:
    normalized = str(model_name or "").strip()
    if "/" in normalized:
        backend, model = normalized.split("/", 1)
        return backend.strip() or DEFAULT_MLEXP_AI_BACKEND, model.strip() or DEFAULT_MLEXP_AI_MODEL_NAME
    if ":" in normalized:
        backend, model = normalized.split(":", 1)
        return backend.strip() or DEFAULT_MLEXP_AI_BACKEND, model.strip() or DEFAULT_MLEXP_AI_MODEL_NAME
    if normalized:
        return DEFAULT_MLEXP_AI_BACKEND, normalized
    return DEFAULT_MLEXP_AI_BACKEND, DEFAULT_MLEXP_AI_MODEL_NAME


# 用途：
# - 将 MLEXP 支持的内部 LLM Backend alias 归一化为 health readiness key
# 输入：
# - backend: account/backend selector 中的内部 Backend 名称
# 输出：
# - 与 MLEXP `/health.llm_backends` 一致的 Backend key
def _normalize_mlexp_ai_backend(backend: str) -> str:
    normalized = str(backend or "").strip().lower()
    if normalized in {"mnm", "minimax"}:
        return "minimax"
    if normalized in {"go", "opencode-go", "opencodego", "opencode_go"}:
        return "opencode_go"
    if normalized in {"omlx", "mlx"} or normalized.startswith("omlx"):
        return "omlx"
    return normalized or DEFAULT_MLEXP_AI_BACKEND


# 用途：
# - 为 description-only Engineer 调用生成稳定 case id
# 输入：
# - task_id/task_key/prompt: Tier 元数据和调用 prompt
# 输出：
# - 可用于 MLEXP report_output.case 的稳定字符串
def _resolve_mlexp_case_id(*, task_id: str, task_key: str, prompt: str) -> str:
    if task_key:
        return task_key
    if task_id:
        return task_id.rsplit("::", 1)[-1]
    digest = hashlib.sha1(str(prompt or "").encode("utf-8")).hexdigest()[:12]
    return f"engineer-{digest}"


# 用途：
# - 判断一次 MLEXP Engineer 调用是否属于 preflight
# 输入：
# - role_name/phase_name: Tier role 和 Slinky phase
# 输出：
# - True 表示 report 应落到 preflight 子目录并启用 MLEXP preflight 选项
def _is_preflight_call(role_name: str, phase_name: str) -> bool:
    _ = role_name
    return str(phase_name or "").strip().lower() == "preflight"


# 用途：
# - 校验必填文本字段
# 输入：
# - value/name: 原始值和字段名
# 输出：
# - 去空白后的字符串
def _require_text(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise MlexpBackendError(f"missing required MLEXP payload field: {name}")
    return normalized


register_backend("mlexp", MlexpClient)
