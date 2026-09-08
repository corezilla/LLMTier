from __future__ import annotations

import json
import os
import re
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


def _resolve_default_claude_cli_path() -> str:
    env_path = str(os.environ.get("SLINKY_CLAUDE_CLI_PATH") or "").strip()
    if env_path:
        return env_path
    path_match = shutil.which("claude")
    if path_match:
        return path_match
    return os.path.expanduser("~/.local/bin/claude")


DEFAULT_CLAUDE_CLI_PATH = _resolve_default_claude_cli_path()
DEFAULT_CLAUDE_CLI_MODEL = ""
DEFAULT_CLAUDE_CLI_SANDBOX = "danger-full-access"
DEFAULT_CLAUDE_CLI_TIMEOUT_SECONDS = 1800


# 用途：
# - 保存 claude CLI 一次调用的 stdout/stderr、解析内容和实时日志路径
# 输入：
# - 由 _invoke_claude_cli 创建
# 输出：
# - ClaudeClient.call 可消费的结构化结果
@dataclass
class ClaudeCliResult:
    returncode: int | None
    stdout: str
    stderr: str
    result_message: str
    model_name: str
    duration_ms: int
    output_message_path: str
    timed_out: bool = False
    error_type: str = ""
    error_message: str = ""
    command: list[str] = field(default_factory=list)
    stdout_path: str = ""
    stderr_path: str = ""
    debug_path: str = ""

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
            "debug_path": self.debug_path,
            "result_message": self.result_message,
            "model_name": self.model_name,
            "duration_ms": self.duration_ms,
            "output_message_path": self.output_message_path,
            "timed_out": self.timed_out,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "command": list(self.command or []),
            "usage": _parse_claude_cli_usage(self.stderr, self.stdout),
        }

# 用途：
# - 调用 claude CLI 并实时保存 stdout/stderr
# 输入：
# - prompt_text/workspace_root/output_message_path/CLI 配置/metadata: 本次调用上下文
# 输出：
# - ClaudeCliResult
def _invoke_claude_cli(
    *,
    prompt_text: str,
    workspace_root: str | Path,
    output_message_path: str | Path,
    claude_path: str = DEFAULT_CLAUDE_CLI_PATH,
    model_name: str = DEFAULT_CLAUDE_CLI_MODEL,
    sandbox_mode: str = DEFAULT_CLAUDE_CLI_SANDBOX,
    timeout_seconds: int = DEFAULT_CLAUDE_CLI_TIMEOUT_SECONDS,
    metadata: dict[str, Any] | None = None,
) -> ClaudeCliResult:
    workspace_root_path = Path(workspace_root).resolve()
    output_message_abs = Path(output_message_path).resolve()
    output_message_abs.parent.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()

    normalized_model = str(model_name or DEFAULT_CLAUDE_CLI_MODEL).strip()
    metadata_payload = dict(metadata or {})
    debug_path = _resolve_claude_debug_path(
        workspace_root=workspace_root_path,
        metadata=metadata_payload,
    )
    command = [
        str(claude_path),
        "--print",
        "--output-format",
        "json",
        "--debug-file",
        str(debug_path),
    ]

    if normalized_model:
        command.extend(["--model", normalized_model])

    normalized_sandbox_mode = str(sandbox_mode or DEFAULT_CLAUDE_CLI_SANDBOX).strip()
    if normalized_sandbox_mode == "danger-full-access":
        command.append("--dangerously-skip-permissions")
    elif normalized_sandbox_mode:
        command.extend(["--permission-mode", normalized_sandbox_mode])

    command.extend(["-"])

    stdout_path, stderr_path = build_cli_log_paths(
        workspace_root=workspace_root_path,
        backend="claude",
        model_name=normalized_model or "claude-default",
        metadata=metadata_payload,
    )
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    debug_path.touch()
    process = run_cli_with_live_logs(
        command=command,
        cwd=str(workspace_root_path),
        env=None,
        stdin_text=str(prompt_text or ""),
        timeout_seconds=int(timeout_seconds),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    if process.timed_out:
        result_message = process.stdout
        output_message_abs.write_text(result_message, encoding="utf-8")
        return ClaudeCliResult(
            returncode=None,
            stdout=process.stdout,
            stderr=process.stderr,
            result_message=result_message,
            model_name=str(model_name or DEFAULT_CLAUDE_CLI_MODEL),
            duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            output_message_path=str(output_message_abs),
            timed_out=True,
            error_type="timeout",
            error_message=f"Claude CLI timed out after {int(timeout_seconds)}s",
            command=command,
            stdout_path=process.stdout_path,
            stderr_path=process.stderr_path,
            debug_path=str(debug_path),
        )

    result_message = process.stdout or ""
    output_message_abs.write_text(result_message, encoding="utf-8")
    return ClaudeCliResult(
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        result_message=result_message,
        model_name=str(model_name or DEFAULT_CLAUDE_CLI_MODEL),
        duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
        output_message_path=str(output_message_abs),
        command=command,
        stdout_path=process.stdout_path,
        stderr_path=process.stderr_path,
        debug_path=str(debug_path),
    )


def _decode_timeout_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)


# 用途：
# - 解析 Claude debug log 文件路径，优先使用上层预登记路径
# 输入：
# - workspace_root/metadata: 当前工作目录和调用 metadata
# 输出：
# - debug log 绝对路径
def _resolve_claude_debug_path(*, workspace_root: Path, metadata: dict[str, Any]) -> Path:
    configured_debug_path = str(metadata.get("cli_debug_path") or "").strip()
    if configured_debug_path:
        path = Path(configured_debug_path)
        return path if path.is_absolute() else workspace_root / path
    stdout_path, _stderr_path = build_cli_log_paths(
        workspace_root=workspace_root,
        backend="claude",
        model_name=str(metadata.get("model_name") or "claude-default"),
        metadata=metadata,
    )
    return stdout_path.with_suffix(".debug.log")


def _parse_claude_cli_usage(stderr: str, stdout: str = "") -> dict[str, Any]:
    json_usage = _parse_claude_cli_json_usage(stdout)
    if json_usage:
        return json_usage

    text = str(stderr or "")
    match = re.search(r"tokens used\s*\n\s*([0-9][0-9,]*)", text, flags=re.IGNORECASE)
    total_tokens = 0
    if match:
        try:
            total_tokens = int(match.group(1).replace(",", ""))
        except ValueError:
            total_tokens = 0
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": total_tokens,
        "raw": {
            "tokens_used": total_tokens,
        },
    }


def _parse_claude_cli_json_usage(stdout: str) -> dict[str, Any]:
    latest_usage: dict[str, Any] = {}
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
            latest_usage = dict(raw_usage)

        if str(event.get("type") or "").strip() == "turn.completed" and isinstance(raw_usage, dict):
            latest_usage = dict(raw_usage)

    if not latest_usage:
        return {}

    input_tokens = _to_int(latest_usage.get("input_tokens"))
    cached_input_tokens = _to_int(latest_usage.get("cache_read_input_tokens", 0) or latest_usage.get("cached_input_tokens", 0))
    output_tokens = _to_int(latest_usage.get("output_tokens"))
    total_tokens = _to_int(latest_usage.get("total_tokens")) or input_tokens + cached_input_tokens + output_tokens

    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_details": {
            "cached_tokens": cached_input_tokens,
        },
        "cache_read_input_tokens": cached_input_tokens,
        "raw": dict(latest_usage),
    }


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


# 用途：
# - 通过 claude CLI 提供 llm_tier backend client，并保存可审计 CLI 输出
# 输入：
# - cli_path/model_name/sandbox/timeout_seconds: backend 配置
# 输出：
# - BaseBackendClient 兼容 client
class ClaudeClient(BaseBackendClient, AgentBackendMixin):
    def __init__(self, cli_path: str = "", model_name: str = "", sandbox: str = "danger-full-access", timeout_seconds: int = 180, **kwargs: Any) -> None:
        self._cli_path = cli_path or DEFAULT_CLAUDE_CLI_PATH
        self._model_name = model_name
        self._sandbox = sandbox
        self._timeout_seconds = timeout_seconds

    @property
    def backend(self) -> str:
        return "claude"

    @property
    def backend_type(self) -> str:
        return "CLI"

    def supported_models(self) -> list[str]:
        return [self._model_name] if self._model_name else []

    # 用途：
    # - 执行一次 claude CLI 调用并返回 tier 标准响应
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
        import tempfile
        started = time.time()
        workspace_root = str((metadata or {}).get("workspace_root") or os.getcwd())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = f.name
        try:
            cli_result = _invoke_claude_cli(
                prompt_text=prompt,
                workspace_root=workspace_root,
                output_message_path=output_path,
                claude_path=self._cli_path,
                model_name=self._model_name,
                sandbox_mode=self._sandbox,
                timeout_seconds=timeout_seconds or self._timeout_seconds,
                metadata=metadata,
            )
            latency = (time.time() - started) * 1000
            if cli_result.returncode != 0:
                err_text = cli_result.error_message or cli_result.stderr or cli_result.stdout or ""
                if QuotaManager.is_quota_error(err_text):
                    raise QuotaExhaustedError(self.backend, model_name, err_text)
                if cli_result.returncode is None:
                    raise BackendCallError(
                        self.backend,
                        err_text or "Claude CLI failed without return code",
                        raw_response=cli_result.to_serializable(),
                    )
                raise BackendCallError(
                    self.backend,
                    f"CLI exited with code {cli_result.returncode}: {err_text}",
                    raw_response=cli_result.to_serializable(),
                )
            content = ""
            if os.path.exists(output_path):
                content = open(output_path, encoding="utf-8").read()
            if not content and cli_result.stdout:
                content = cli_result.stdout
            return {
                "ok": True,
                "content": content,
                "model_name": self._model_name or "claude-default",
                "latency_ms": latency,
                "token_usage": _parse_claude_cli_usage(cli_result.stderr, cli_result.stdout),
                "raw_response": {
                    "returncode": cli_result.returncode,
                    "stdout": cli_result.stdout,
                    "stderr": cli_result.stderr,
                    "stdout_path": cli_result.stdout_path,
                    "stderr_path": cli_result.stderr_path,
                    "debug_path": cli_result.debug_path,
                },
                "error_code": 0,
                "error_message": "",
            }
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


register_backend("claude", ClaudeClient)
