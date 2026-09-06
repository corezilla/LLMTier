from __future__ import annotations

import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


# 用途：
# - 保存一次 CLI 子进程执行的 stdout/stderr 捕获结果和落盘路径
# 输入：
# - 由 run_cli_with_live_logs 创建
# 输出：
# - backend client 可解析的 stdout/stderr、returncode、timeout 和日志路径
@dataclass
class CliProcessResult:
    returncode: int | None
    stdout: str
    stderr: str
    stdout_path: str
    stderr_path: str
    timed_out: bool


# 用途：
# - 构建单次 backend CLI 调用的 stdout/stderr 日志文件路径
# 输入：
# - workspace_root/backend/model_name/metadata: 当前调用上下文
# 输出：
# - stdout/stderr 日志文件绝对路径
def build_cli_log_paths(
    *,
    workspace_root: str | Path,
    backend: str,
    model_name: str,
    metadata: dict[str, Any] | None,
) -> tuple[Path, Path]:
    workspace_root_path = Path(workspace_root).resolve()
    metadata_payload = dict(metadata or {})
    configured_stdout_path = str(metadata_payload.get("cli_stdout_path") or "").strip()
    configured_stderr_path = str(metadata_payload.get("cli_stderr_path") or "").strip()
    if configured_stdout_path and configured_stderr_path:
        stdout_path = Path(configured_stdout_path)
        stderr_path = Path(configured_stderr_path)
        if not stdout_path.is_absolute():
            stdout_path = workspace_root_path / stdout_path
        if not stderr_path.is_absolute():
            stderr_path = workspace_root_path / stderr_path
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        return stdout_path, stderr_path
    project_name = _safe_path_part(str(metadata_payload.get("project_name") or workspace_root_path.name or "default"))
    stage_name = _safe_path_part(str(metadata_payload.get("stage_name") or "unknown_stage"))
    phase_name = _safe_path_part(str(metadata_payload.get("phase_name") or "unknown_phase"))
    task_key = _safe_path_part(str(metadata_payload.get("task_key") or metadata_payload.get("task_id") or "unknown_task"))
    attempt = _safe_path_part(str(metadata_payload.get("attempt") or "attempt"))
    backend_part = _safe_path_part(str(backend or "backend"))
    model_part = _safe_path_part(str(model_name or "model"))
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    has_task_context = any(
        str(metadata_payload.get(key) or "").strip()
        for key in ("stage_name", "phase_name", "task_key", "task_id")
    )
    if not has_task_context:
        log_dir = workspace_root_path / "workspaces" / "tier_state" / "cli_io" / stage_name / phase_name / task_key
    elif workspace_root_path.name == project_name:
        project_workspace_path = workspace_root_path
        log_dir = project_workspace_path / "meta" / "cli_io" / stage_name / phase_name / task_key
    else:
        project_workspace_path = workspace_root_path / "workspaces" / project_name
        log_dir = project_workspace_path / "meta" / "cli_io" / stage_name / phase_name / task_key
    log_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{timestamp}.{attempt}.{backend_part}.{model_part}.{os.getpid()}"
    return log_dir / f"{stem}.stdout.log", log_dir / f"{stem}.stderr.log"


# 用途：
# - 执行 CLI 子进程并实时把 stdout/stderr tee 到文件，同时保留内存文本供原解析逻辑使用
# 输入：
# - command/cwd/env/stdin_text/timeout_seconds/stdout_path/stderr_path: 子进程执行上下文和日志目标
# 输出：
# - CliProcessResult
def run_cli_with_live_logs(
    *,
    command: list[str],
    cwd: str,
    env: dict[str, str] | None,
    stdin_text: str,
    timeout_seconds: int,
    stdout_path: str | Path,
    stderr_path: str | Path,
) -> CliProcessResult:
    stdout_file_path = Path(stdout_path)
    stderr_file_path = Path(stderr_path)
    stdout_file_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_file_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_file_path.touch()
    stderr_file_path.touch()
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    timed_out = False
    deadline = time.monotonic() + max(1, int(timeout_seconds))
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", stdout_chunks, stdout_file_path))
    selector.register(process.stderr, selectors.EVENT_READ, ("stderr", stderr_chunks, stderr_file_path))

    # Step 1: 发送 prompt 并关闭 stdin，让 CLI 开始执行。
    try:
        process.stdin.write(str(stdin_text or ""))
        process.stdin.close()

        # Step 2: 轮询 stdout/stderr，把新输出立即追加到文件。
        while selector.get_map():
            if process.poll() is None and time.monotonic() > deadline:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (AttributeError, ProcessLookupError, PermissionError):
                    process.kill()
            events = selector.select(timeout=0.2)
            if not events and process.poll() is not None:
                _drain_registered_streams(selector)
                break
            for key, _ in events:
                stream_name, chunks, file_path = key.data
                data = key.fileobj.readline()
                if data:
                    chunks.append(data)
                    _append_cli_log(file_path, data)
                else:
                    selector.unregister(key.fileobj)

        # Step 3: 等待退出并兜底读取残留输出。
        process.wait(timeout=1)
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except OSError:
                continue

    return CliProcessResult(
        returncode=None if timed_out else int(process.returncode) if process.returncode is not None else None,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
        stdout_path=str(stdout_file_path),
        stderr_path=str(stderr_file_path),
        timed_out=timed_out,
    )


# 用途：
# - 读取 selector 中尚未消费的 stdout/stderr 内容
# 输入：
# - selector: 已注册 stdout/stderr 的 selector
# 输出：
# - 无；直接追加到对应 chunks 和日志文件
def _drain_registered_streams(selector: selectors.DefaultSelector) -> None:
    for key in list(selector.get_map().values()):
        stream_name, chunks, file_path = key.data
        while True:
            data = key.fileobj.readline()
            if not data:
                break
            chunks.append(data)
            _append_cli_log(file_path, data)
        selector.unregister(key.fileobj)


# 用途：
# - 追加一段 CLI 输出到日志文件
# 输入：
# - file_path/text: 日志路径和待追加文本
# 输出：
# - 无；直接写文件
def _append_cli_log(file_path: Path, text: str) -> None:
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()


# 用途：
# - 将 stage/phase/task/model 等上下文转换为安全路径名
# 输入：
# - value: 原始字符串
# 输出：
# - 仅包含路径安全字符的字符串
def _safe_path_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return normalized.strip("._-") or "unknown"
