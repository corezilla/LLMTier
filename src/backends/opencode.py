from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backends import register_backend
from backends.agent_backend import AgentBackendMixin
from backends.base import BaseBackendClient
from backends.cli_io import build_cli_log_paths, run_cli_with_live_logs
from exceptions import BackendCallError, QuotaExhaustedError
from quota_manager import QuotaManager
from redaction import redact_sensitive_text, redact_sensitive_value


# 用途：
# - 解析默认 opencode CLI 路径，支持环境变量、PATH 和项目本地 tools shim
# 输入：
# - 读取 SLINKY_OPENCODE_CLI_PATH、PATH 和当前代码所在 repo root
# 输出：
# - 可传给 subprocess 的 opencode CLI 路径字符串
def _resolve_default_opencode_cli_path() -> str:
    env_path = str(os.environ.get("SLINKY_OPENCODE_CLI_PATH") or "").strip()
    if env_path:
        return env_path
    path_match = shutil.which("opencode")
    if path_match:
        return path_match
    repo_tool_path = Path(__file__).resolve().parents[2] / "tools" / "opencode"
    if repo_tool_path.exists():
        return str(repo_tool_path)
    return os.path.expanduser("~/.local/bin/opencode")


DEFAULT_OPENCODE_CLI_PATH = _resolve_default_opencode_cli_path()
DEFAULT_OPENCODE_CLI_MODEL = ""
DEFAULT_OPENCODE_CLI_TIMEOUT_SECONDS = 1800


# 用途：
# - 保存 opencode CLI 一次调用的 stdout/stderr、解析内容和实时日志路径
# 输入：
# - 由 _run_opencode_subprocess 创建
# 输出：
# - OpenCodeClient.call 可消费的结构化结果
@dataclass
class OpenCodeCliResult:
    returncode: int | None
    stdout: str
    stderr: str
    result_message: str
    model_name: str
    duration_ms: int
    timed_out: bool = False
    error_type: str = ""
    error_message: str = ""
    command: list[str] = field(default_factory=list)
    stdout_path: str = ""
    stderr_path: str = ""

    # 用途：
    # - 将 CLI 结果转换为可写入 raw_response 的 JSON 结构
    # 输入：
    # - 无；读取实例字段
    # 输出：
    # - 可序列化字典
    def to_serializable(self) -> dict[str, Any]:
        return {
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "result_message": self.result_message,
            "model_name": self.model_name,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "command": list(self.command or []),
            "usage": _parse_opencode_cli_usage(self.stderr, self.stdout),
        }

# 用途：
# - 调用 opencode CLI 并实时保存 stdout/stderr
# 输入：
# - prompt_text/workspace_root/CLI 配置/metadata: 本次调用上下文
# 输出：
# - OpenCodeCliResult
def _invoke_opencode_cli(
    *,
    prompt_text: str,
    workspace_root: str | Path,
    opencode_path: str = DEFAULT_OPENCODE_CLI_PATH,
    model_name: str = DEFAULT_OPENCODE_CLI_MODEL,
    timeout_seconds: int = DEFAULT_OPENCODE_CLI_TIMEOUT_SECONDS,
    dangerously_skip_permissions: bool = True,
    metadata: dict[str, Any] | None = None,
) -> OpenCodeCliResult:
    workspace_root_path = Path(workspace_root).resolve()
    started_at = time.monotonic()

    restricted_env = _build_isolated_env()

    command = _build_opencode_run_command(
        opencode_path=opencode_path,
        model_name=model_name,
        workspace_root=workspace_root_path,
        dangerously_skip_permissions=dangerously_skip_permissions,
        prompt_text=prompt_text,
    )

    result = _run_opencode_subprocess(
        command=command,
        cwd=str(workspace_root_path),
        timeout_seconds=timeout_seconds,
        env=restricted_env,
        started_at=started_at,
        model_name=model_name,
        metadata=metadata,
        prompt_text=prompt_text,
    )

    return result

# 用途：
# - 构建隔离的子进程环境变量
# 输入：
# - 无；读取 os.environ
# 输出：
# - 清理后的环境变量字典
def _build_isolated_env() -> dict[str, str]:
    env = os.environ.copy()
    for k in list(env.keys()):
        if k.startswith("OPENCODE_"):
            del env[k]
    env["OPENCODE_PERMISSION"] = json.dumps({
        "bash": {
            "opencode session delete *": "deny",
            "opencode session *": "deny",
            "*": "allow",
        },
    })
    return env

# 用途：
# - 构建 opencode run 命令行参数
# 输入：
# - opencode_path/model_name/workspace_root/dangerously_skip_permissions/prompt_text: CLI 调用参数与强制工作目录
# 输出：
# - 显式绑定 workspace 的命令行参数列表
def _build_opencode_run_command(
    *,
    opencode_path: str,
    model_name: str,
    workspace_root: str | Path,
    dangerously_skip_permissions: bool,
    prompt_text: str,
) -> list[str]:
    command = [
        str(opencode_path),
        "run",
        "--format", "json",
        "--print-logs",
        "--log-level", "DEBUG",
        "--dir", str(Path(workspace_root).resolve()),
    ]
    normalized_model = str(model_name or DEFAULT_OPENCODE_CLI_MODEL).strip()
    if normalized_model:
        command.extend(["--model", normalized_model])
    if dangerously_skip_permissions:
        command.append("--dangerously-skip-permissions")
    del prompt_text
    return command

# 用途：
# - 执行 opencode CLI 子进程并返回结构化结果
# 输入：
# - command/cwd/timeout_seconds/env/started_at/model_name/metadata: 子进程执行上下文
# 输出：
# - OpenCodeCliResult
def _run_opencode_subprocess(
    *,
    command: list[str],
    cwd: str,
    timeout_seconds: int,
    env: dict[str, str],
    started_at: float,
    model_name: str,
    metadata: dict[str, Any] | None = None,
    prompt_text: str = "",
) -> OpenCodeCliResult:
    stdout_path, stderr_path = build_cli_log_paths(
        workspace_root=cwd,
        backend="opencode",
        model_name=model_name or "opencode-default",
        metadata=metadata,
    )
    process = run_cli_with_live_logs(
        command=command,
        cwd=cwd,
        env=env,
        stdin_text=prompt_text,
        timeout_seconds=int(timeout_seconds),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    if process.timed_out:
        return OpenCodeCliResult(
            returncode=None,
            stdout=process.stdout,
            stderr=process.stderr,
            result_message=process.stdout,
            model_name=str(model_name or DEFAULT_OPENCODE_CLI_MODEL),
            duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            timed_out=True,
            error_type="timeout",
            error_message=f"OpenCode CLI timed out after {int(timeout_seconds)}s",
            command=command,
            stdout_path=process.stdout_path,
            stderr_path=process.stderr_path,
        )

    result_message = _extract_opencode_content(process.stdout)
    return OpenCodeCliResult(
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        result_message=result_message,
        model_name=str(model_name or DEFAULT_OPENCODE_CLI_MODEL),
        duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
        command=command,
        stdout_path=process.stdout_path,
        stderr_path=process.stderr_path,
    )


def _decode_timeout_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)


def _extract_opencode_content(stdout: str) -> str:
    if not stdout or not stdout.strip():
        return ""
    last_content = ""
    saw_structured_event = False
    for raw_line in str(stdout).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        saw_structured_event = True
        event_type = str(event.get("type") or "").strip()
        if event_type == "text":
            part = event.get("part") or {}
            text = part.get("text", "")
            if text:
                last_content = text
        elif event_type == "assistant.message" or event_type == "message":
            data = event.get("data") or event
            content_parts = data.get("content") or []
            if isinstance(content_parts, list):
                parts = []
                for part in content_parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        parts.append(part)
                if parts:
                    last_content = "\n".join(parts)
            elif isinstance(content_parts, str):
                last_content = content_parts
        elif event_type == "result" or event_type == "output":
            data = event.get("data") or event.get("content") or ""
            if isinstance(data, str) and data:
                last_content = data
    if last_content:
        return last_content
    return "" if saw_structured_event else stdout.strip()


# Purpose: Reject malformed or non-JSON lines in the OpenCode JSONL protocol.
# Inputs: Complete CLI stdout.
# Outputs: None; raises BackendCallError when any non-empty line is not a JSON object.
def _validate_opencode_jsonl(stdout: str) -> None:
    for raw_line in str(stdout or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BackendCallError("opencode", "malformed OpenCode JSONL output") from exc
        if not isinstance(event, dict):
            raise BackendCallError("opencode", "malformed OpenCode JSONL event")


# Purpose: Read the final OpenCode step termination reason from JSONL output.
# Inputs: Complete OpenCode stdout containing zero or more structured events.
# Outputs: Final step_finish reason, or an empty string when no terminal event exists.
def _extract_opencode_terminal_reason(stdout: str) -> str:
    terminal_reason = ""
    for raw_line in str(stdout or "").splitlines():
        try:
            event = json.loads(raw_line.strip())
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(event, dict) or str(event.get("type") or "").strip() != "step_finish":
            continue
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        terminal_reason = str(part.get("reason") or "").strip()
    return terminal_reason


def _extract_opencode_model_name(stdout: str, stderr: str = "") -> str:
    """从 opencode CLI 输出中提取实际使用的模型名

    优先从 stderr 的 agent 指示行提取（格式: > agent · model），
    回退到 stdout JSON lines 的 part.model 字段。

    输入:
    - stdout: 标准输出
    - stderr: 标准错误输出

    输出:
    - 模型名字符串，未找到返回空串
    """
    for raw_line in str(stderr or "").splitlines():
        line = raw_line.strip()
        stripped = _strip_ansi(line)
        if "·" in stripped:
            parts = stripped.split("·")
            if len(parts) >= 2:
                model_part = parts[-1].strip()
                if model_part:
                    return model_part
    for raw_line in str(stdout or "").splitlines():
        line = raw_line.strip()
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        part = event.get("part") or {}
        model = part.get("model")
        if isinstance(model, str) and model:
            return model
    return ""


_ANSI_ESCAPE_RE: re.Pattern[str] | None = None


def _strip_ansi(text: str) -> str:
    """移除 ANSI 转义序列

    输入:
    - text: 可能包含 ANSI 转义的文本

    输出:
    - 清理后的纯文本
    """
    global _ANSI_ESCAPE_RE
    if _ANSI_ESCAPE_RE is None:
        import re
        _ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]\d[^;]*;")
    return _ANSI_ESCAPE_RE.sub("", text)


# 用途：
# - 从 opencode run --format json 输出中提取整次 agent run 的 token 用量
# 输入：
# - stderr: 标准错误输出，当前保留给兼容调用方
# - stdout: 标准输出 JSON lines
# 输出：
# - 聚合后的 prompt/completion/total token usage 与原始 step 摘要
def _parse_opencode_cli_usage(stderr: str, stdout: str = "") -> dict[str, Any]:
    step_usages: list[dict[str, Any]] = []
    fallback_usage: dict[str, Any] = {}

    # 逐行解析 opencode JSONL 事件，收集每个 step_finish 的 token 事件。
    for raw_line in str(stdout or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        raw_usage = event.get("usage")
        if isinstance(raw_usage, dict):
            fallback_usage = dict(raw_usage)
        event_type = str(event.get("type") or "").strip()
        if event_type == "step_finish":
            part = event.get("part") or {}
            tokens = part.get("tokens")
            if isinstance(tokens, dict):
                step_usages.append(dict(tokens))

    # opencode agent run 可能包含多次内部 LLM 调用；按 step 聚合才是整次 run 的用量。
    if step_usages:
        return _aggregate_opencode_step_usages(step_usages)

    if not fallback_usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "raw": {}}
    input_tokens = _to_int(fallback_usage.get("input_tokens") or fallback_usage.get("input"))
    output_tokens = _to_int(fallback_usage.get("output_tokens") or fallback_usage.get("output"))
    total_tokens = _to_int(fallback_usage.get("total_tokens") or fallback_usage.get("total")) or input_tokens + output_tokens
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
        "raw": dict(fallback_usage),
    }


# 用途：
# - 聚合 opencode 多个 step_finish token payload
# 输入：
# - step_usages: 每个 step_finish.part.tokens 的字典列表
# 输出：
# - llm_tier 统一 usage 字典，保留 step_count/cache/reasoning 明细
def _aggregate_opencode_step_usages(step_usages: list[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = 0
    output_tokens = 0
    reasoning_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0
    total_tokens = 0
    for usage in step_usages:
        step_input_tokens = _opencode_usage_int(usage, "input")
        step_output_tokens = _opencode_usage_int(usage, "output")
        step_reasoning_tokens = _opencode_usage_int(usage, "reasoning")
        cache = usage.get("cache") if isinstance(usage.get("cache"), dict) else {}
        step_cache_read_tokens = _to_int(cache.get("read")) + _to_int(usage.get("cache_read_input_tokens"))
        step_cache_write_tokens = _to_int(cache.get("write")) + _to_int(usage.get("cache_creation_input_tokens"))
        input_tokens += step_input_tokens
        output_tokens += step_output_tokens
        reasoning_tokens += step_reasoning_tokens
        cache_read_tokens += step_cache_read_tokens
        cache_write_tokens += step_cache_write_tokens
        total_tokens += _opencode_usage_int(usage, "total") or (
            step_input_tokens + step_output_tokens + step_reasoning_tokens + step_cache_read_tokens + step_cache_write_tokens
        )
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_details": {
            "cached_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
        },
        "reasoning_tokens": reasoning_tokens,
        "cache_read_input_tokens": cache_read_tokens,
        "cache_creation_input_tokens": cache_write_tokens,
        "raw": {
            "step_count": len(step_usages),
            "steps": [dict(item) for item in step_usages],
        },
    }


# 用途：
# - 兼容 opencode token payload 的短字段名与长字段名
# 输入：
# - usage/key: step token payload 与标准短字段名
# 输出：
# - 对应整数 token 值
def _opencode_usage_int(usage: dict[str, Any], key: str) -> int:
    return _to_int(usage.get(f"{key}_tokens") or usage.get(key))


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


# 用途：
# - 通过 opencode CLI 提供 llm_tier backend client，并保存可审计 CLI 输出
# 输入：
# - cli_path/model_name/timeout_seconds: backend 配置
# 输出：
# - BaseBackendClient 兼容 client
class OpenCodeClient(BaseBackendClient, AgentBackendMixin):
    def __init__(self, cli_path: str = "", model_name: str = "", timeout_seconds: int = 180, **kwargs: Any) -> None:
        self._cli_path = cli_path or DEFAULT_OPENCODE_CLI_PATH
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds

    @property
    def backend(self) -> str:
        return "opencode"

    @property
    def backend_type(self) -> str:
        return "CLI"

    def supported_models(self) -> list[str]:
        return [self._model_name] if self._model_name else []

    # 用途：
    # - 执行一次 opencode CLI 调用并返回 tier 标准响应
    # 输入：
    # - model_name/prompt/temperature/timeout_seconds/metadata: 当前 LLM 调用上下文
    # 输出：
    # - 包含 content/token_usage/raw_response 的响应字典
    def call(
        self,
        model_name: str = "",
        prompt: str = "",
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = 180,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        started = time.time()
        workspace_root = str((metadata or {}).get("workspace_root") or os.getcwd())
        cli_result = _invoke_opencode_cli(
            prompt_text=prompt,
            workspace_root=workspace_root,
            opencode_path=self._cli_path,
            model_name=model_name or self._model_name,
            timeout_seconds=timeout_seconds or self._timeout_seconds,
            metadata=metadata,
        )
        latency = (time.time() - started) * 1000
        if cli_result.returncode != 0:
            err_text = cli_result.error_message or cli_result.stderr or cli_result.stdout or ""
            stdout_text = cli_result.stdout or ""
            if QuotaManager.is_quota_error(err_text) or QuotaManager.is_quota_error(stdout_text):
                detail = redact_sensitive_text(stdout_text[:800] if QuotaManager.is_quota_error(stdout_text) else err_text)
                raise QuotaExhaustedError(self.backend, model_name, detail)
            safe_error = redact_sensitive_text(err_text)
            safe_raw_response = redact_sensitive_value(cli_result.to_serializable())
            if cli_result.returncode is None:
                raise BackendCallError(
                    self.backend,
                    safe_error or "OpenCode CLI failed without return code",
                    raw_response=safe_raw_response,
                )
            raise BackendCallError(
                self.backend,
                f"CLI exited with code {cli_result.returncode}: {safe_error}",
                raw_response=safe_raw_response,
            )
        _validate_opencode_jsonl(cli_result.stdout)
        terminal_reason = _extract_opencode_terminal_reason(cli_result.stdout)
        if terminal_reason == "length":
            raise BackendCallError(
                self.backend,
                "OpenCode CLI output was truncated at the model output limit",
                raw_response=cli_result.to_serializable(),
            )
        content = cli_result.result_message
        if not content and cli_result.stdout:
            content = _extract_opencode_content(cli_result.stdout)
        if not str(content or "").strip():
            raise BackendCallError(
                self.backend,
                "OpenCode CLI completed without assistant text",
                raw_response=cli_result.to_serializable(),
            )
        usage = _parse_opencode_cli_usage(cli_result.stderr, cli_result.stdout)
        actual_model = _extract_opencode_model_name(cli_result.stdout, cli_result.stderr) or self._model_name or model_name or "opencode-default"
        return {
            "ok": True,
            "content": content,
            "model_name": actual_model,
            "latency_ms": latency,
            "token_usage": usage,
            "raw_response": {
                "returncode": cli_result.returncode,
                "stdout": cli_result.stdout,
                "stderr": cli_result.stderr,
                "stdout_path": cli_result.stdout_path,
                "stderr_path": cli_result.stderr_path,
            },
            "error_code": 0,
            "error_message": "",
        }


register_backend("opencode", OpenCodeClient)
