from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backends import register_backend
from backends.agent_backend import AgentBackendMixin
from backends.base import BaseBackendClient
from exceptions import BackendCallError, QuotaExhaustedError
from quota_manager import QuotaManager


def _resolve_default_codex_cli_path() -> str:
    env_path = str(os.environ.get("SLINKY_CODEX_CLI_PATH") or "").strip()
    if env_path:
        return env_path
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    tools_codex = project_root / "tools" / "codex"
    if tools_codex.is_file():
        return str(tools_codex)
    path_match = shutil.which("codex")
    if path_match:
        return path_match
    vscode_bin_root = Path("/home/claw/.vscode-server/extensions")
    if vscode_bin_root.exists():
        matches = sorted(vscode_bin_root.glob("openai.chatgpt-*/bin/linux-x86_64/codex"))
        for match in reversed(matches):
            if match.is_file():
                return str(match)
    return os.path.expanduser("~/.local/bin/codex")


DEFAULT_CODEX_CLI_PATH = _resolve_default_codex_cli_path()
DEFAULT_CODEX_CLI_MODEL = "gpt-5.4"
DEFAULT_CODEX_CLI_SANDBOX = "danger-full-access"
DEFAULT_CODEX_CLI_TIMEOUT_SECONDS = 1800


@dataclass
class CodexCliResult:
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

    def to_serializable(self) -> dict[str, Any]:
        return {
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "result_message": self.result_message,
            "model_name": self.model_name,
            "duration_ms": self.duration_ms,
            "output_message_path": self.output_message_path,
            "timed_out": self.timed_out,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "command": list(self.command or []),
            "usage": _parse_codex_cli_usage(self.stderr, self.stdout),
        }


def _invoke_codex_cli(
    *,
    prompt_text: str,
    workspace_root: str | Path,
    output_message_path: str | Path,
    codex_path: str = DEFAULT_CODEX_CLI_PATH,
    model_name: str = DEFAULT_CODEX_CLI_MODEL,
    sandbox_mode: str = DEFAULT_CODEX_CLI_SANDBOX,
    timeout_seconds: int = DEFAULT_CODEX_CLI_TIMEOUT_SECONDS,
) -> CodexCliResult:
    workspace_root_path = Path(workspace_root).resolve()
    output_message_abs = Path(output_message_path).resolve()
    output_message_abs.parent.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()
    command = [
        str(codex_path),
        "-m",
        str(model_name or DEFAULT_CODEX_CLI_MODEL),
    ]
    normalized_sandbox_mode = str(sandbox_mode or DEFAULT_CODEX_CLI_SANDBOX).strip()
    if normalized_sandbox_mode == "danger-full-access":
        command.extend(
            [
                "exec",
                "--json",
                "--dangerously-bypass-approvals-and-sandbox",
            ]
        )
    else:
        command.extend(
            [
                "-a",
                "never",
                "exec",
                "--json",
                "--sandbox",
                normalized_sandbox_mode,
            ]
        )
    command.extend(
        [
            "--skip-git-repo-check",
            "--cd",
            str(workspace_root_path),
            "--output-last-message",
            str(output_message_abs),
            "-",
        ]
    )
    try:
        process = subprocess.run(
            command,
            cwd=str(workspace_root_path),
            text=True,
            input=str(prompt_text or ""),
            capture_output=True,
            timeout=int(timeout_seconds),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result_message = output_message_abs.read_text(encoding="utf-8") if output_message_abs.exists() else ""
        return CodexCliResult(
            returncode=None,
            stdout=_decode_timeout_output(exc.stdout),
            stderr=_decode_timeout_output(exc.stderr),
            result_message=result_message,
            model_name=str(model_name or DEFAULT_CODEX_CLI_MODEL),
            duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            output_message_path=str(output_message_abs),
            timed_out=True,
            error_type="timeout",
            error_message=f"Codex CLI timed out after {int(timeout_seconds)}s",
            command=command,
        )
    result_message = output_message_abs.read_text(encoding="utf-8") if output_message_abs.exists() else ""
    return CodexCliResult(
        returncode=int(process.returncode),
        stdout=process.stdout,
        stderr=process.stderr,
        result_message=result_message,
        model_name=str(model_name or DEFAULT_CODEX_CLI_MODEL),
        duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
        output_message_path=str(output_message_abs),
        command=command,
    )


def _decode_timeout_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)


def _parse_codex_cli_usage(stderr: str, stdout: str = "") -> dict[str, Any]:
    json_usage = _parse_codex_cli_json_usage(stdout)
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


def _parse_codex_cli_json_usage(stdout: str) -> dict[str, Any]:
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
    cached_input_tokens = _to_int(latest_usage.get("cached_input_tokens"))
    output_tokens = _to_int(latest_usage.get("output_tokens"))
    total_tokens = _to_int(latest_usage.get("total_tokens")) or input_tokens + output_tokens
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_details": {
            "cached_tokens": cached_input_tokens,
        },
        "cached_input_tokens": cached_input_tokens,
        "raw": dict(latest_usage),
    }


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class CodexClient(BaseBackendClient, AgentBackendMixin):
    def __init__(self, cli_path: str = "", model_name: str = "", sandbox: str = "danger-full-access", timeout_seconds: int = 180, **kwargs: Any) -> None:
        self._cli_path = cli_path or DEFAULT_CODEX_CLI_PATH
        self._model_name = model_name or DEFAULT_CODEX_CLI_MODEL
        self._sandbox = sandbox
        self._timeout_seconds = timeout_seconds

    @property
    def backend(self) -> str:
        return "codex"

    @property
    def backend_type(self) -> str:
        return "CLI"

    def supported_models(self) -> list[str]:
        return [self._model_name]

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
            cli_result = _invoke_codex_cli(
                prompt_text=prompt,
                workspace_root=workspace_root,
                output_message_path=output_path,
                codex_path=self._cli_path,
                model_name=self._model_name,
                sandbox_mode=self._sandbox,
                timeout_seconds=timeout_seconds or self._timeout_seconds,
            )
            latency = (time.time() - started) * 1000
            if cli_result.returncode != 0:
                err_text = cli_result.stderr or ""
                stdout_text = cli_result.stdout or ""
                if QuotaManager.is_quota_error(err_text) or QuotaManager.is_quota_error(stdout_text):
                    detail = stdout_text[:800] if QuotaManager.is_quota_error(stdout_text) else err_text
                    raise QuotaExhaustedError(self.backend, model_name, detail)
                raise BackendCallError(self.backend, f"CLI exited with code {cli_result.returncode}: {err_text}")
            content = ""
            if os.path.exists(output_path):
                content = open(output_path, encoding="utf-8").read()
            if not content and cli_result.stdout:
                content = cli_result.stdout
            if QuotaManager.is_quota_error(content or ""):
                raise QuotaExhaustedError(self.backend, self._model_name, content[:500])
            if QuotaManager.is_quota_error(cli_result.stdout):
                raise QuotaExhaustedError(self.backend, self._model_name, cli_result.stdout[:500])
            return {
                "ok": True,
                "content": content,
                "model_name": self._model_name,
                "latency_ms": latency,
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "raw_response": {"returncode": cli_result.returncode, "stdout": cli_result.stdout, "stderr": cli_result.stderr},
                "error_code": 0,
                "error_message": "",
            }
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


register_backend("codex", CodexClient)
