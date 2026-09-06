from __future__ import annotations

import json
import hashlib
import os
import sys
import threading
import time
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from llm_tier.client import (
    BUSY_MAX_RETRY_INTERVAL_SECONDS,
    BUSY_RETRY_INTERVAL_SECONDS,
    _busy_retry_schedule_seconds,
    is_trusted_tier_host,
)
from llm_tier.provider_usage import ProviderUsageManager, provider_usage_key, resolved_quota_provider
from llm_tier.redaction import redact_sensitive_text, redact_sensitive_value

RUNTIME_STATS_CACHE_SECONDS = 2.0
MAX_JSON_BODY_BYTES = 2 * 1024 * 1024
EXHAUSTED_PROBE_INTERVAL_SECONDS = 10 * 60
EXHAUSTED_PROBE_SCAN_SECONDS = 60.0
EXHAUSTED_PROBE_MIN_DELAY_SECONDS = 1.0
PROBE_STATUS_FRESH_SECONDS = 300.0


# 用途：
# - 从 parse_qs 结果读取单个 query 参数
# 输入：
# - params/name: query 参数字典和字段名
# 输出：
# - 去空白后的第一个参数值；缺失时为空字符串
def _first_query_value(params: dict[str, list[str]], name: str) -> str:
    values = params.get(name) or []
    if not values:
        return ""
    return str(values[0] or "").strip()


# 用途：
# - 解析 dashboard stats API 传入的 workspace 路径
# 输入：
# - workspace_value: 绝对路径或 repo-relative workspace 路径
# 输出：
# - workspace 绝对路径字符串
def _resolve_workspace_root_for_api(workspace_value: str) -> str:
    text = str(workspace_value or "").strip()
    if not text:
        return ""
    if text.startswith("/workspaces/"):
        return str((Path.cwd() / text.lstrip("/")).resolve())
    path = Path(text)
    if path.is_absolute():
        return str(path)
    return str((Path.cwd() / path).resolve())


# 用途：
# - 将 provider usage 的数值字段解析成 float，过滤缺失或非法值
# 输入：
# - value: provider usage snapshot 中的 percent/remaining 字段
# 输出：
# - 可比较的 float；非法或缺失时返回 None
def _provider_usage_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


# 用途：
# - 判断 provider usage 是否明确显示当前账号仍有可用额度
# 输入：
# - snapshot: `_refresh_provider_usage_for_probe` 返回的 provider usage snapshot
# 输出：
# - True 表示可清理 stale exhausted 并继续真实 probe
def _provider_usage_snapshot_has_capacity(snapshot: dict[str, Any]) -> bool:
    status = str(snapshot.get("status") or "").strip().lower()
    if status == "unlimited":
        return True
    if status != "ok":
        return False

    candidates: list[dict[str, Any]] = [snapshot]
    for window in snapshot.get("windows") or []:
        if isinstance(window, dict):
            candidates.append(window)

    for item in candidates:
        remaining = _provider_usage_number(item.get("remaining"))
        if remaining is not None and remaining > 0:
            return True
        percent = _provider_usage_number(item.get("percent"))
        if percent is not None and percent < 100:
            return True
    return False


# 用途：
# - 从 provider usage snapshot 中提取最早的 reset_at
# 输入：
# - snapshot: provider usage 统一快照
# 输出：
# - reset_at 字符串；找不到时返回空字符串
def _provider_usage_reset_at(snapshot: dict[str, Any]) -> str:
    candidates: list[str] = []
    reset_at = str(snapshot.get("reset_at") or "").strip()
    if reset_at:
        candidates.append(reset_at)
    for window in snapshot.get("windows") or []:
        if not isinstance(window, dict):
            continue
        window_reset_at = str(window.get("reset_at") or "").strip()
        if window_reset_at:
            candidates.append(window_reset_at)
    if not candidates:
        return ""
    return min(candidates, key=lambda item: _parse_exhausted_probe_epoch(item) or float("inf"))


# Purpose: Parse a quota reset timestamp into Unix epoch seconds.
# Inputs: ISO, date-time, or clock-only text.
# Outputs: Schedulable epoch seconds, or None when every supported format rejects the value.
def _parse_exhausted_probe_epoch(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        with suppress(ValueError):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    with suppress(ValueError):
        return datetime.fromisoformat(text).timestamp()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(datetime.strptime(text, fmt).timetuple())
        except ValueError:
            continue
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            parsed = datetime.strptime(text.upper(), fmt)
        except ValueError:
            continue
        now = datetime.now()
        scheduled = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
        if scheduled <= now:
            scheduled += timedelta(days=1)
        return scheduled.timestamp()
    return None

from llm_tier.tier_config import TierConfig
from llm_tier.router_core import LLMRouter
from llm_tier.stats_collector import StatsCollector
from llm_tier.tier_model import (
    TierCallRequest,
    TierCallResult,
    TierModel,
    TierStatsQuery,
    backend_call_model_name,
    backend_client_name,
)
from llm_tier.exceptions import QuotaExhaustedError, BackendCallError
from llm_tier.quota_manager import QuotaManager


def _log(msg: str, *args: Any) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"{ts} [llm_tier] {msg}"
    if args:
        line = line % args
    print(line, file=sys.stderr, flush=True)


# 用途：
# - 读取 file 模式传入的 prompt 文件，并兼容 Slinky combined prompt 审计包装
# 输入：
# - prompt/prompt_path: HTTP content 模式正文和 file 模式 prompt 文件路径
# 输出：
# - 实际发送给 backend 的 prompt 正文
def _resolve_request_prompt(prompt: str, prompt_path: str) -> str:
    normalized_prompt = str(prompt or "")
    normalized_path = str(prompt_path or "").strip()
    if not normalized_path:
        return normalized_prompt
    try:
        text = Path(normalized_path).read_text(encoding="utf-8")
    except OSError:
        return normalized_prompt
    marker = "=== USER PROMPT ==="
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text


# 用途：
# - 以原子替换方式写入 tier file 模式的 LLM IO 文件
# 输入：
# - target_path/content: 目标路径和待写入内容
# 输出：
# - 写入成功时返回目标路径；失败时返回空字符串
def _write_tier_text_file(target_path: str, content: str) -> str:
    normalized_path = str(target_path or "").strip()
    if not normalized_path:
        return ""
    try:
        path = Path(normalized_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
        return str(path)
    except OSError as exc:
        _log("failed to write tier artifact %s: %s", normalized_path, exc)
        return ""


# 用途：
# - 为 file mode 错误结果确定 sidecar 路径
# 输入：
# - req: 当前 tier 请求
# 输出：
# - 显式 error_response_path，或由 response_path 推导出的 `.error.json`
def _tier_error_response_path(req: TierCallRequest) -> str:
    explicit_path = str(req.error_response_path or "").strip()
    if explicit_path:
        return explicit_path
    response_path = str(req.response_path or "").strip()
    if not response_path:
        return ""
    path = Path(response_path)
    if path.suffix:
        return str(path.with_suffix(".error.json"))
    return f"{response_path}.error.json"


# 用途：
# - 构造 file mode 错误 sidecar payload，保持错误通道与业务 response 原文分离
# 输入：
# - req/result: 当前请求和失败结果
# 输出：
# - 可写入 `response.error.json` 的 JSON dict
def _tier_error_payload(req: TierCallRequest, result: TierCallResult) -> dict[str, Any]:
    now_text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "success": False,
        "error_type": _tier_error_type(result),
        "error_code": int(result.error_code or 0),
        "message": redact_sensitive_text(result.error_message),
        "backend": str(result.backend or ""),
        "account": str(result.account or ""),
        "model_name": str(result.model_name or ""),
        "backend_type": str(result.backend_type or ""),
        "tier": str(result.tier or ""),
        "stage_name": str(req.stage_name or ""),
        "phase_name": str(req.phase_name or ""),
        "task_id": str(req.task_id or ""),
        "task_key": str(req.task_key or ""),
        "finished_at": now_text,
        "raw_response": result.raw_response if isinstance(result.raw_response, dict) else {},
        "debug_paths": {
            "prompt_path": str(req.prompt_path or ""),
            "response_path": str(req.response_path or ""),
            "raw_response_path": str(req.raw_response_path or ""),
        },
    }


# 用途：
# - 将 TierCallResult 错误信息归类为稳定的 sidecar error_type
# 输入：
# - result: 失败调用结果
# 输出：
# - empty_response / timeout / completion_truncated / backend_call_failed 等错误类型
def _tier_error_type(result: TierCallResult) -> str:
    message = str(result.error_message or "").lower()
    if "empty_response" in message or "empty response" in message:
        return "empty_response"
    if "timeout" in message:
        return "timeout"
    if int(result.error_code or 0) == 1007:
        return "completion_truncated"
    if int(result.error_code or 0) == 1006:
        return "transport_timeout"
    return "backend_call_failed"


# 用途：
# - 在 file 模式下由 tier 写成功 response/raw response 或失败 error sidecar
# 输入：
# - req/result: 当前 tier 请求和 backend 调用结果
# 输出：
# - public artifact path 字典和 raw response 是否已写入
def _write_tier_call_artifacts(req: TierCallRequest, result: TierCallResult) -> tuple[dict[str, str], bool]:
    artifact_paths: dict[str, str] = {}
    raw_response_written = False
    if not result.ok:
        error_path = _write_tier_text_file(
            _tier_error_response_path(req),
            json.dumps(_tier_error_payload(req, result), ensure_ascii=False, indent=2) + "\n",
        )
        if error_path:
            artifact_paths["error_response_path"] = error_path
        return artifact_paths, raw_response_written

    response_path = _write_tier_text_file(req.response_path, str(result.content or "") + "\n")
    if response_path:
        artifact_paths["response_path"] = response_path
    if str(req.raw_response_path or "").strip():
        raw_payload = {
            "ok": result.ok,
            "backend": result.backend,
            "account": result.account,
            "model_name": result.model_name,
            "backend_type": result.backend_type,
            "tier": result.tier,
            "tier_priority": result.tier_priority,
            "latency_ms": result.latency_ms,
            "token_usage": result.token_usage,
            "is_fallback": result.is_fallback,
            "fallback_count": result.fallback_count,
            "raw_response": result.raw_response,
            "error_code": result.error_code,
            "error_message": result.error_message,
        }
        raw_path = _write_tier_text_file(
            req.raw_response_path,
            json.dumps(raw_payload, ensure_ascii=False, indent=2),
        )
        if raw_path:
            raw_response_written = True
    return artifact_paths, raw_response_written


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_API_PROBE_TIMEOUT_SECONDS = 10
DEFAULT_CLI_PROBE_TIMEOUT_SECONDS = 300
PROBE_PROMPT = "Reply with OK."
TRACE_LEVELS = {
    "trace": 5,
    "debug": 10,
    "info": 20,
    "warn": 30,
    "warning": 30,
    "error": 40,
}
DEFAULT_TRACE_TYPES = {"job", "router", "backend", "poll", "client", "error"}
# 用途：
# - 从环境变量读取非负浮点秒数，供 server 与 client 使用同名 busy retry 配置
# 输入：
# - env_name/default: 环境变量名和默认值
# 输出：
# - 解析后的非负浮点数；缺失或非法时返回默认值
def _env_float(env_name: str, default: float) -> float:
    raw_value = str(os.environ.get(env_name) or "").strip()
    if not raw_value:
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


# 用途：
# - 提供 llm_tier 独立 HTTP server，集中管理路由、配额、并发、统计和运行时调试
# 输入：
# - host/port/settings_path: 监听地址、端口和 tier 配置路径
# 输出：
# - HTTP API、runtime snapshot、stats 和异步 job 调度能力
class TierServer:
    # 用途：
    # - 初始化 tier server 的配置、router、stats、backend 状态、job 表和 debug trace 状态
    # 输入：
    # - host/port/settings_path: server 地址、端口和 settings.json 路径
    # 输出：
    # - 无；构建可启动的 TierServer 实例
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 settings_path: str | None = None) -> None:
        normalized_host = str(host or "").strip().lower()
        if not is_trusted_tier_host(normalized_host):
            raise ValueError("TierServer host must be localhost, loopback, or a private IP")
        if not 0 <= int(port) <= 65535:
            raise ValueError("TierServer port must be between 0 and 65535")
        self.host = host
        self.port = int(port)

        self._import_backends()
        self._config = TierConfig(settings_path)
        self._stats_dir = self._resolve_stats_dir()
        self._debug_lock = threading.Lock()
        self._debug_state = self._load_runtime_debug_state()
        self._router = LLMRouter(self._config, state_dir=self._stats_dir, trace_hook=self._trace)
        self._stats = StatsCollector(self._stats_dir)
        self._provider_usage = ProviderUsageManager()

        self._jobs: dict[str, dict[str, Any]] = {}
        self._backend_status: dict[str, dict[str, Any]] = {}
        self._probe_running = False
        self._exhausted_probe_timers: dict[str, threading.Timer] = {}
        self._exhausted_probe_due_epoch: dict[str, float] = {}
        self._exhausted_probe_monitor_started = False
        self._lock = threading.Lock()
        self._runtime_stats_lock = threading.Lock()
        self._runtime_stats_cache_at = 0.0
        self._runtime_stats_cache: dict[str, Any] = {}
        self._busy_retry_interval_seconds = _env_float(
            "TIER_BUSY_RETRY_INTERVAL_SECONDS",
            BUSY_RETRY_INTERVAL_SECONDS,
        )
        self._http_server: ThreadingHTTPServer | None = None
        self._running = False
        self._started_at_epoch = time.time()
        self._load_runtime_config_state()

    # Purpose: Register every supported Backend implementation available in this installation.
    # Inputs: None; imports the fixed Backend module inventory.
    # Outputs: None; unavailable optional Backend modules are skipped.
    @staticmethod
    def _import_backends() -> None:
        for module_name in ("xfyun", "volc", "deepseek", "minimax", "opencode_go", "debug"):
            try:
                __import__(f"llm_tier.backends.{module_name}", fromlist=["llm_tier.backends"])
            except Exception:
                continue

    # 用途：
    # - 解析 LLMTier 自有 runtime state/stats 目录
    # 输入：
    # - 无；读取 LLMTIER_STATE_DIR 或项目内 state 默认目录
    # 输出：
    # - stats/tier_trace 等运行时文件所在目录
    def _resolve_stats_dir(self) -> str:
        configured_path = os.environ.get("LLMTIER_STATE_DIR", "").strip()
        if configured_path:
            return str(Path(configured_path).expanduser().resolve())
        return str(Path(__file__).resolve().parent.parent.parent / "state")

    # 用途：
    # - 根据环境变量初始化 tier runtime debug/trace 开关
    # 输入：
    # - 无；读取 TIER_TRACE_* 环境变量和当前 stats_dir
    # 输出：
    # - 可序列化的 debug state
    def _load_runtime_debug_state(self) -> dict[str, Any]:
        enabled_text = os.environ.get("TIER_TRACE_ENABLED", "").strip().lower()
        enabled = enabled_text in {"1", "true", "yes", "on"}
        level = os.environ.get("TIER_TRACE_LEVEL", "info").strip().lower() or "info"
        if level not in TRACE_LEVELS:
            level = "info"
        types_text = os.environ.get("TIER_TRACE_TYPES", ",".join(sorted(DEFAULT_TRACE_TYPES)))
        trace_types = self._normalize_trace_types(types_text)
        trace_path = os.environ.get("TIER_TRACE_PATH", "").strip()
        if not trace_path:
            trace_path = str(Path(self._stats_dir) / "tier_trace.jsonl")
        state_path = os.environ.get("TIER_TRACE_STATE_PATH", "").strip()
        if not state_path:
            state_path = str(Path(trace_path).with_name("tier_debug.json"))
        return {
            "enabled": enabled,
            "level": level,
            "types": sorted(trace_types),
            "path": trace_path,
            "state_path": state_path,
        }

    # 用途：
    # - 规范化外部传入的 trace 类型过滤条件
    # 输入：
    # - raw_types: 字符串、列表或集合形式的类型配置
    # 输出：
    # - 小写类型集合；空输入时使用默认类型集合
    def _normalize_trace_types(self, raw_types: Any) -> set[str]:
        if isinstance(raw_types, str):
            parts = raw_types.split(",")
        elif isinstance(raw_types, (list, tuple, set)):
            parts = list(raw_types)
        else:
            parts = []
        normalized = {str(item or "").strip().lower() for item in parts}
        normalized = {item for item in normalized if item}
        return normalized or set(DEFAULT_TRACE_TYPES)

    # 用途：
    # - 返回当前 tier runtime debug/trace 配置快照
    # 输入：
    # - 无；读取内存态 debug state
    # 输出：
    # - 可返回给 /runtime 和 /debug 的配置副本
    def _runtime_debug_snapshot(self) -> dict[str, Any]:
        with self._debug_lock:
            snapshot = dict(self._debug_state)
        snapshot["levels"] = ["trace", "debug", "info", "warn", "error"]
        snapshot["available_types"] = ["all", "job", "router", "backend", "poll", "client", "http", "escalation", "error"]
        return snapshot

    # 用途：
    # - 通过 HTTP 命令更新 tier runtime debug/trace 开关
    # 输入：
    # - data: /debug POST 的 JSON payload
    # 输出：
    # - 更新后的 debug state；clear_trace 为 true 时清空 trace 文件
    def _update_runtime_debug(self, data: dict[str, Any]) -> dict[str, Any]:
        invalid_level = ""
        with self._debug_lock:
            current = dict(self._debug_state)
            if "enabled" in data:
                current["enabled"] = bool(data.get("enabled"))
            if str(data.get("level") or "").strip():
                level = str(data.get("level") or "").strip().lower()
                if level not in TRACE_LEVELS:
                    invalid_level = level
                else:
                    current["level"] = level
            if "types" in data:
                current["types"] = sorted(self._normalize_trace_types(data.get("types")))
            if str(data.get("path") or "").strip():
                current["path"] = str(data.get("path") or "").strip()
                if not str(data.get("state_path") or "").strip():
                    current["state_path"] = str(Path(current["path"]).with_name("tier_debug.json"))
            if str(data.get("state_path") or "").strip():
                current["state_path"] = str(data.get("state_path") or "").strip()
            if not invalid_level:
                self._debug_state = current
            trace_path = str(current.get("path") or "")
        if invalid_level:
            return {"ok": False, "error": "invalid_debug_level", "debug": self._runtime_debug_snapshot()}

        if bool(data.get("clear_trace")) and trace_path:
            try:
                path = Path(trace_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            except OSError as exc:
                return {"ok": False, "error": f"clear_trace_failed: {exc}", "debug": self._runtime_debug_snapshot()}
        self._persist_runtime_debug_state()
        return {"ok": True, "debug": self._runtime_debug_snapshot()}

    # 用途：
    # - 将 runtime debug state 写入本地文件，供 TierClient 进程无需重启即可读取开关
    # 输入：
    # - 无；读取 `_debug_state`
    # 输出：
    # - 无；写入失败只记 stderr
    def _persist_runtime_debug_state(self) -> None:
        snapshot = self._runtime_debug_snapshot()
        state_path = str(snapshot.get("state_path") or "").strip()
        if not state_path:
            return
        payload = {
            "enabled": bool(snapshot.get("enabled")),
            "level": str(snapshot.get("level") or "info"),
            "types": list(snapshot.get("types") or []),
            "path": str(snapshot.get("path") or ""),
            "state_path": state_path,
        }
        try:
            path = Path(state_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            _log("failed to write tier debug state: %s", exc)

    # 用途：
    # - 读取 trace JSONL 文件尾部，供外部命令快速查看最近事件
    # 输入：
    # - limit: 最大返回行数
    # 输出：
    # - trace 文件路径和最近事件列表
    def _read_trace_tail(self, limit: int = 100) -> dict[str, Any]:
        snapshot = self._runtime_debug_snapshot()
        trace_path = str(snapshot.get("path") or "")
        resolved_limit = max(1, min(int(limit or 100), 1000))
        path = Path(trace_path)
        if not trace_path or not path.exists():
            return {"ok": True, "path": trace_path, "events": []}
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[-resolved_limit:]
        except OSError as exc:
            return {"ok": False, "path": trace_path, "error": str(exc), "events": []}
        events: list[dict[str, Any]] = []
        for line in lines:
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed = {"raw": line}
            if isinstance(parsed, dict):
                events.append(parsed)
        return {"ok": True, "path": trace_path, "events": events}

    # 用途：
    # - 按 runtime debug 开关写入 tier_trace.jsonl
    # 输入：
    # - event_type/level/event/fields: 类型、级别、事件名和结构化字段
    # 输出：
    # - 无；写入失败只写 stderr，不影响主请求
    def _trace(
        self,
        event_type: str,
        level: str,
        event: str,
        fields: dict[str, Any] | None = None,
    ) -> None:
        normalized_type = str(event_type or "runtime").strip().lower()
        normalized_level = str(level or "info").strip().lower()
        if normalized_level == "warning":
            normalized_level = "warn"
        with self._debug_lock:
            snapshot = dict(self._debug_state)
        if not bool(snapshot.get("enabled")):
            return
        configured_level = str(snapshot.get("level") or "info").strip().lower()
        if TRACE_LEVELS.get(normalized_level, 20) < TRACE_LEVELS.get(configured_level, 20):
            return
        configured_types = self._normalize_trace_types(snapshot.get("types"))
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
            trace_path = Path(str(snapshot.get("path") or Path(self._stats_dir) / "tier_trace.jsonl"))
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:
            _log("failed to write tier trace: %s", exc)

    # 用途：
    # - 从当前 config 内存态初始化 backend enabled 状态，真实 probing 只能由 `_begin_probe` 写入
    # 输入：
    # - 无；读取 TierConfig 当前内存配置
    # 输出：
    # - 无；更新 server/router 运行时状态
    def _load_runtime_config_state(self) -> None:
        for tier_name in self._config._config.get("llm_tiers", {}):
            for model in self._config.get_tier_models(tier_name):
                self._router.set_backend_enabled(
                    model.backend,
                    model.model_name,
                    bool(model.enabled),
                    tier_name=tier_name,
                    account=model.account,
                )
                if not bool(model.enabled):
                    self._set_backend_status(tier_name, model.account, model.backend, model.model_name, "disabled")
                    continue
                if self._router._quota.is_exhausted(model.backend, model.model_name):
                    self._set_backend_status(tier_name, model.account, model.backend, model.model_name, "exhausted")
                    continue
                self._set_backend_status(tier_name, model.account, model.backend, model.model_name, "unreachable")

    # 用途：
    # - 将一次 Tier 调用的 stage/phase/task 上下文和字符长度补入 llm_tier runtime stats event
    # 输入：
    # - event/req/result/job_id: router 原始统计事件、Tier 请求、最终返回结果和可选 HTTP job 标识
    # 输出：
    # - 可直接写入 StatsCollector 的完整 event
    def _stats_event_for_request(
        self,
        event: dict[str, Any],
        req: TierCallRequest,
        result: TierCallResult,
        *,
        job_id: str = "",
    ) -> dict[str, Any]:
        base_event = dict(event or {})
        event_metadata = base_event.get("metadata") if isinstance(base_event.get("metadata"), dict) else {}
        metadata = {**dict(event_metadata), **dict(req.metadata or {})}
        execution_level = str(metadata.get("execution_level") or "").strip()
        role_profile = str(metadata.get("role_profile") or "").strip()
        if execution_level:
            metadata["execution_level"] = execution_level
        if role_profile:
            metadata["role_profile"] = role_profile
        if str(job_id or "").strip():
            metadata["job_id"] = str(job_id).strip()
        return {
            **base_event,
            "project": req.project_name,
            "stage_name": req.stage_name,
            "phase_name": req.phase_name,
            "task_id": req.task_id,
            "task_key": req.task_key,
            "role": req.role_name,
            "prompt_name": str(metadata.get("prompt_name") or "").strip(),
            "prompt_kind": str(metadata.get("prompt_kind") or "").strip(),
            "execution_level": execution_level,
            "role_profile": role_profile,
            "metadata": metadata,
            "prompt_chars": len(str(req.prompt or "")),
            "completion_chars": len(str(result.content or "")),
            "error_code": int(result.error_code or 0),
            "error_message": str(result.error_message or ""),
            "selection_debug": str(metadata.get("selection_debug") or event.get("selection_debug") or ""),
        }

    # 用途：
    # - 判断一次 Tier stats event 是否只是 backend 全忙的临时诊断事件
    # 输入：
    # - event: 已标准化或待写入 stats store 的调用事件
    # 输出：
    # - True 表示该事件不应默认写入 stats/recent_errors，只在 debug trace 中保留
    def _is_all_backends_busy_event(self, event: dict[str, Any]) -> bool:
        error_message = str(event.get("error_message") or "").strip().lower()
        selection_debug = str(event.get("selection_debug") or "").strip().lower()
        try:
            error_code = int(event.get("error_code") or 0)
        except (TypeError, ValueError):
            error_code = 0
        if error_message == "all_backends_busy" or error_message.startswith("all_backends_busy:"):
            return True
        return error_code == 1005 and "request_busy" in selection_debug

    # 用途：
    # - 判断一次 TierCallResult 是否是 transient busy，可在 server job 内等待后重试
    # 输入：
    # - result: router.call 返回的结果
    # 输出：
    # - True 表示命中 all_backends_busy/request_busy，不能立即写失败 Artifact
    def _is_busy_result(self, result: TierCallResult) -> bool:
        if result.ok:
            return False
        error_message = str(result.error_message or "").strip().lower()
        if error_message == "all_backends_busy" or error_message.startswith("all_backends_busy:"):
            return True
        try:
            error_code = int(result.error_code or 0)
        except (TypeError, ValueError):
            error_code = 0
        selection_debug = ""
        if isinstance(result.raw_response, dict):
            selection_debug = str(result.raw_response.get("selection_debug") or "").strip().lower()
        return error_code == 1005 and "request_busy" in selection_debug

    # 用途：
    # - 对 server 异步/file-mode job 统一处理 all_backends_busy，等待并重试到成功或非 busy 结果
    # 输入：
    # - req/job_id/request_metadata: 当前 Tier 请求、job id 和请求元数据
    # 输出：
    # - 最终 TierCallResult 与 stats_event；busy 不会作为最终结果返回给业务层
    def _router_call_with_busy_retry(
        self,
        *,
        req: TierCallRequest,
        job_id: str,
        request_metadata: dict[str, Any],
    ) -> tuple[TierCallResult, dict[str, Any]]:
        started_at = time.time()
        busy_retry_count = 0
        busy_timeout_seconds = max(1.0, float(req.timeout_seconds or 600))

        while True:
            result, stats_event = self._router.call(
                role_name=req.role_name,
                prompt=req.prompt,
                temperature=req.temperature,
                timeout_seconds=req.timeout_seconds,
                metadata={
                    "stage_name": req.stage_name,
                    "phase_name": req.phase_name,
                    "task_id": req.task_id,
                    "task_key": req.task_key,
                    "project_name": req.project_name,
                    "job_id": job_id,
                    **request_metadata,
                },
            )
            if not isinstance(result, TierCallResult) or not isinstance(stats_event, dict):
                raise TypeError("invalid malformed router result")
            if not self._is_busy_result(result):
                return result, stats_event

            elapsed_seconds = time.time() - started_at
            busy_retry_count += 1
            retry_after_seconds = self._busy_retry_delay_seconds(
                result,
                elapsed_seconds=elapsed_seconds,
                retry_count=busy_retry_count,
            )
            remaining_seconds = max(0.0, busy_timeout_seconds - elapsed_seconds)
            if remaining_seconds <= 0:
                self._trace(
                    "job",
                    "warn",
                    "router.call.busy_timeout",
                    {
                        "job_id": job_id,
                        "role_name": req.role_name,
                        "task_id": req.task_id,
                        "elapsed_seconds": round(elapsed_seconds, 3),
                        "timeout_seconds": busy_timeout_seconds,
                    },
                )
                return result, stats_event
            self._mark_job_pending(job_id, status="waiting")

            self._trace(
                "job",
                "debug",
                "router.call.busy_retry",
                {
                    "job_id": job_id,
                    "role_name": req.role_name,
                    "project_name": req.project_name,
                    "stage_name": req.stage_name,
                    "phase_name": req.phase_name,
                    "task_id": req.task_id,
                    "error_message": result.error_message,
                    "selection_debug": (
                        str(result.raw_response.get("selection_debug") or "")
                        if isinstance(result.raw_response, dict)
                        else ""
                    ),
                    "elapsed_seconds": round(elapsed_seconds, 3),
                    "retry_after_seconds": round(min(retry_after_seconds, remaining_seconds), 3),
                },
            )
            time.sleep(min(retry_after_seconds, remaining_seconds))
            if time.time() - started_at >= busy_timeout_seconds:
                self._trace(
                    "job",
                    "warn",
                    "router.call.busy_timeout",
                    {
                        "job_id": job_id,
                        "role_name": req.role_name,
                        "task_id": req.task_id,
                        "elapsed_seconds": round(time.time() - started_at, 3),
                        "timeout_seconds": busy_timeout_seconds,
                    },
                )
                return result, stats_event

    # 用途：
    # - 从 router busy 结果中读取下一次重试建议，并按已等待时长逐步扩大重试间隔
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
            initial_seconds=getattr(self, "_busy_retry_interval_seconds", BUSY_RETRY_INTERVAL_SECONDS),
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
    # - 写入正式 LLM 调用 stats，并默认抑制 all_backends_busy 这类临时资源诊断噪声
    # 输入：
    # - event: `_stats_event_for_request` 生成的完整 stats event
    # 输出：
    # - 无；必要时写入 stats store，抑制事件仅通过 debug trace 暴露
    def _write_call_stats_event(self, event: dict[str, Any]) -> None:
        if not self._is_all_backends_busy_event(event):
            self._stats.write(event)
            return
        self._trace(
            "stats",
            "debug",
            "stats.call.suppressed",
            {
                "reason": "all_backends_busy",
                "project": str(event.get("project") or ""),
                "stage_name": str(event.get("stage_name") or ""),
                "phase_name": str(event.get("phase_name") or ""),
                "task_id": str(event.get("task_id") or ""),
                "role": str(event.get("role") or ""),
                "selection_debug": str(event.get("selection_debug") or ""),
            },
        )

    # 用途：
    # - 修复旧统计事件缺失 tier 时的展示上下文，避免 dashboard 出现未知 Tier
    # 输入：
    # - event: 从 SQLite stats store 读取的一条 LLM 调用事件
    # 输出：
    # - 带有可展示 tier 字段的事件副本
    def _stats_event_for_response(self, event: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(event or {})
        if str(normalized.get("tier") or "").strip():
            return normalized
        role_name = str(normalized.get("role") or "").strip()
        if role_name:
            normalized["tier"] = self._config.get_tier_for_role(role_name)
        return normalized

    # 用途：
    # - 为 `/runtime` 提供短 TTL 的 authoritative stats 快照，避免 dashboard 并发刷新重复扫 SQLite
    # 输入：
    # - 无；读取 StatsCollector 并使用 server 内部缓存
    # 输出：
    # - stats_by_key、recent_errors、summary 三部分 runtime stats 数据
    def _runtime_stats_snapshot(self) -> dict[str, Any]:
        now = time.time()
        cached = self._runtime_stats_cache
        if cached and now - self._runtime_stats_cache_at <= RUNTIME_STATS_CACHE_SECONDS:
            return dict(cached)
        with self._runtime_stats_lock:
            now = time.time()
            cached = self._runtime_stats_cache
            if cached and now - self._runtime_stats_cache_at <= RUNTIME_STATS_CACHE_SECONDS:
                return dict(cached)
            snapshot = {
                "stats_by_key": self._runtime_stats_by_backend(),
                "recent_errors": self._runtime_recent_error_events(),
                "summary": self._stats.get_summary(),
            }
            self._runtime_stats_cache = snapshot
            self._runtime_stats_cache_at = now
            return dict(snapshot)

    # 用途：
    # - 从 StatsCollector 聚合 backend 统计，供 `/runtime.tiers[*].stats` 展示
    # 输入：
    # - 无；读取 llm_stats SQLite authoritative 统计
    # 输出：
    # - `tier:account:model_name` 到 stats 字典的映射
    def _runtime_stats_by_backend(self) -> dict[str, dict[str, Any]]:
        stats_by_key: dict[str, dict[str, Any]] = {}
        for row in self._stats.get_stats(TierStatsQuery(limit=9999)):
            key = self._backend_identity_key(row.tier, row.account, row.model_name)
            stats_by_key[key] = {
                "calls": row.calls,
                "success_count": row.success_count,
                "fail_count": row.fail_count,
                "total_tokens": row.total_tokens,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "cached_tokens": row.cached_tokens,
                "prompt_chars": row.prompt_chars,
                "prompt_chars_avg": row.prompt_chars_avg,
                "prompt_chars_p50": row.prompt_chars_p50,
                "prompt_chars_p95": row.prompt_chars_p95,
                "prompt_chars_p99": row.prompt_chars_p99,
                "completion_chars": row.completion_chars,
                "completion_chars_avg": row.completion_chars_avg,
                "completion_chars_p50": row.completion_chars_p50,
                "completion_chars_p95": row.completion_chars_p95,
                "completion_chars_p99": row.completion_chars_p99,
                "prompt_tokens_avg": row.prompt_tokens_avg,
                "prompt_tokens_p50": row.prompt_tokens_p50,
                "prompt_tokens_p95": row.prompt_tokens_p95,
                "prompt_tokens_p99": row.prompt_tokens_p99,
                "completion_tokens_avg": row.completion_tokens_avg,
                "completion_tokens_p50": row.completion_tokens_p50,
                "completion_tokens_p95": row.completion_tokens_p95,
                "completion_tokens_p99": row.completion_tokens_p99,
                "latency_avg_ms": row.latency_avg_ms,
                "latency_p50_ms": row.latency_p50_ms,
                "latency_p90_ms": row.latency_p90_ms,
                "latency_p95_ms": row.latency_p95_ms,
                "latency_p99_ms": row.latency_p99_ms,
                "fallback_count": row.fallback_count,
            }
        return stats_by_key

    # 用途：
    # - 读取并过滤 `/runtime.recent_errors`，排除成功事件和 all_backends_busy 轮询噪声
    # 输入：
    # - 无；读取最近 LLM stats events
    # 输出：
    # - 最多 30 条 dashboard 可展示的错误事件
    def _runtime_recent_error_events(self) -> list[dict[str, Any]]:
        recent_error_events: list[dict[str, Any]] = []
        for event in self._stats.get_events(TierStatsQuery(limit=200)):
            normalized_event = self._stats_event_for_response(event)
            if bool(normalized_event.get("ok")):
                continue
            if self._is_all_backends_busy_event(normalized_event):
                continue
            error_message = str(normalized_event.get("error_message") or "").strip()
            error_code = int(normalized_event.get("error_code") or 0)
            if not error_message and error_code <= 0:
                continue
            recent_error_events.append(
                {
                    "ts": str(normalized_event.get("ts") or ""),
                    "tier": str(normalized_event.get("tier") or ""),
                    "backend": str(normalized_event.get("backend") or ""),
                    "account": str(normalized_event.get("account") or ""),
                    "backend_type": str(normalized_event.get("backend_type") or ""),
                    "model": str(normalized_event.get("model") or ""),
                    "role": str(normalized_event.get("role") or ""),
                    "stage_name": str(normalized_event.get("stage_name") or ""),
                    "phase_name": str(normalized_event.get("phase_name") or ""),
                    "task_id": str(normalized_event.get("task_id") or ""),
                    "prompt_name": str(normalized_event.get("prompt_name") or ""),
                    "error_code": error_code,
                    "error_message": error_message,
                    "selection_debug": str(normalized_event.get("selection_debug") or ""),
                    "prompt_chars": int(normalized_event.get("prompt_chars") or 0),
                    "completion_chars": int(normalized_event.get("completion_chars") or 0),
                    "latency_ms": float(normalized_event.get("latency_ms") or 0),
                    "fallback_count": int(normalized_event.get("fallback_count") or 0),
                }
            )
            if len(recent_error_events) >= 30:
                break
        return recent_error_events

    # =========================================================================
    # 生命周期
    # =========================================================================

    # 用途：
    # - 启动 tier HTTP server，并在 HTTP 可服务后初始化后台 backend probe
    # 输入：
    # - blocking: True 表示在当前线程 serve_forever；False 表示后台线程运行
    # 输出：
    # - 无；server 状态写入实例字段
    def start(self, blocking: bool = False) -> None:
        if self._http_server is not None:
            raise RuntimeError("TierServer is already running")
        handler = self._make_handler()
        self._http_server = ThreadingHTTPServer((self.host, self.port), handler)
        self._http_server.daemon_threads = True
        self.port = int(self._http_server.server_address[1])
        self._running = True
        _log("started on %s:%s", self.host, self.port)
        if blocking:
            self._start_backend_probe(delay_seconds=0.1)
            self._start_exhausted_probe_monitor()
            try:
                self._http_server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            t = threading.Thread(target=self._http_server.serve_forever,
                                 daemon=True)
            t.start()
            self._start_backend_probe(delay_seconds=0.1)
            self._start_exhausted_probe_monitor()

    # 用途：
    # - 在后台启动一次 backend 配额与可用性探测，并防止并发 probe 叠加
    # 输入：
    # - delay_seconds: 探测开始前等待秒数；server 启动时用于等待 HTTP 就绪
    # 输出：
    # - True 表示已启动新的 probe；False 表示已有 probe 正在运行
    def _start_backend_probe(self, *, delay_seconds: float = 0.0) -> bool:
        with self._lock:
            if self._probe_running:
                _log("probe skipped: already running")
                return False
            self._probe_running = True
        threading.Thread(
            target=self._probe_backends,
            kwargs={"delay_seconds": delay_seconds},
            daemon=True,
        ).start()
        return True

    # 用途：
    # - 并行启动每个 backend 的最小语义请求，检查配额状态并刷新 exhausted 标记
    # 输入：
    # - delay_seconds: 探测前等待秒数
    # 输出：
    # - 无；探测结果写回 quota manager
    def _probe_backends(self, *, delay_seconds: float = 0.0) -> None:
        probe_threads: list[threading.Thread] = []
        try:
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            tier_names = list(self._config._config.get("llm_tiers", {}).keys())
            probed: set[str] = set()
            for tn in tier_names:
                models = self._config.get_tier_models(tn)
                for m in models:
                    key = self._backend_identity_key(tn, m.account, m.model_name)
                    if key in probed:
                        continue
                    probed.add(key)
                    if not self._router.is_backend_enabled(m.backend, m.model_name, tier_name=tn, account=m.account):
                        self._set_backend_status(tn, m.account, m.backend, m.model_name, "disabled")
                        continue
                    if self._router._quota.is_exhausted(m.backend, m.model_name):
                        usage_snapshot = self._refresh_provider_usage_for_probe(tn, m)
                        if _provider_usage_snapshot_has_capacity(usage_snapshot):
                            self._router._quota.reset_backend(m.backend, m.model_name)
                        else:
                            self._set_backend_status(tn, m.account, m.backend, m.model_name, "exhausted")
                            continue  # provider usage 未确认恢复，保留 exhausted 状态
                    try:
                        creds = self._router._get_backend_credentials(
                            m.backend,
                            m.provider,
                            m.model_name,
                            m.model_key,
                            m.account,
                        )
                        probe_timeout = self._probe_timeout_seconds(m.backend_type, creds)
                        probe_id = self._begin_probe(tn, m.account, m.backend, m.model_name, probe_timeout)
                        _log("probing %s (%s)...", m.backend, m.model_name)
                        thread = threading.Thread(
                            target=self._run_single_backend_probe,
                            args=(tn, m, creds, probe_timeout, probe_id),
                            daemon=True,
                        )
                        thread.start()
                        probe_threads.append(thread)
                    except Exception as exc:
                        self._router._record_unhealthy_failure(
                            m.backend,
                            m.model_name,
                            str(exc),
                            tier_name=tn,
                            account=m.account,
                            source="probe",
                        )
                        self._sync_backend_meta_from_router(tn, m.account, m.backend, m.model_name)
                        self._refresh_provider_usage_for_probe(tn, m)
                        self._finish_probe_if_current(tn, m.account, m.backend, m.model_name, probe_id, "unreachable")
                        _log("  %s: error %s", m.backend, str(exc)[:80])
            for thread in probe_threads:
                thread.join()
        finally:
            with self._lock:
                self._probe_running = False

    # 用途：
    # - 计算 backend probe 超时，避免 CLI backend 因启动慢被误判为不可达
    # 输入：
    # - backend_type: backend 类型；CLI 使用更宽松的健康检查窗口
    # - creds: backend credential 配置，可包含 timeout_seconds
    # 输出：
    # - probe 调用使用的超时秒数
    def _probe_timeout_seconds(self, backend_type: str, creds: dict[str, Any]) -> int:
        normalized_type = str(backend_type or "").lower()
        configured_timeout = int(creds.get("timeout_seconds") or 0)
        if normalized_type == "cli":
            return max(DEFAULT_CLI_PROBE_TIMEOUT_SECONDS, configured_timeout)
        if normalized_type == "mlp":
            return max(30, configured_timeout)
        return max(DEFAULT_API_PROBE_TIMEOUT_SECONDS, configured_timeout)

    # 用途：
    # - 生成 Tier 内 backend runtime identity，口径为 tier:account:model
    # 输入：
    # - tier_name/account/model_name: Tier、账号和模型名
    # 输出：
    # - 供 server/router runtime 状态表使用的稳定 key
    def _backend_identity_key(self, tier_name: str, account: str, model_name: str) -> str:
        return self._router.backend_key("", model_name, tier_name=tier_name, account=account)

    # 用途：
    # - 记录最近一次 backend probe 状态，供 tier dashboard 展示 backend 可用性
    # 输入：
    # - tier_name/account/backend/model_name/status: Tier 内 backend identity 和规范化状态
    # 输出：
    # - 无；状态写入内存 health payload
    def _set_backend_status(self, tier_name: str, account: str, backend: str, model_name: str, status: str) -> None:
        key = self._backend_identity_key(tier_name, account, model_name)
        self._router.set_backend_runtime_status(backend, model_name, status, tier_name=tier_name, account=account)
        with self._lock:
            current = dict(self._backend_status.get(key) or {})
            current["status"] = status
            current["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if status != "probing":
                current.pop("started_at_epoch", None)
                current.pop("timeout_seconds", None)
                current.pop("probe_id", None)
            self._backend_status[key] = current
        if status == "exhausted":
            self._schedule_exhausted_backend_probe_for_identity(tier_name, account, backend, model_name)
        elif status in {"running", "disabled"}:
            self._cancel_exhausted_backend_probe(key)

    # 用途：
    # - 启动后台扫描，给所有 quota exhausted backend 补齐自动恢复 probe 计时器
    # 输入：
    # - 无；读取当前 quota/runtime 状态
    # 输出：
    # - 无；后台线程周期性调度单 backend probe
    def _start_exhausted_probe_monitor(self) -> None:
        if not hasattr(self, "_exhausted_probe_timers"):
            return
        with self._lock:
            if self._exhausted_probe_monitor_started:
                return
            self._exhausted_probe_monitor_started = True
        threading.Thread(target=self._exhausted_probe_monitor_loop, daemon=True).start()

    # 用途：
    # - 周期扫描 exhausted 状态，覆盖 router fallback 后 server 未即时写 status 的场景
    # 输入：
    # - 无
    # 输出：
    # - 无；为 exhausted backend 注册到期 probe
    def _exhausted_probe_monitor_loop(self) -> None:
        while self._running:
            self._schedule_exhausted_backend_probes()
            time.sleep(EXHAUSTED_PROBE_SCAN_SECONDS)

    # 用途：
    # - 为当前所有 exhausted backend 注册自动恢复 probe
    # 输入：
    # - 无；遍历当前 llm_tiers 和 quota manager
    # 输出：
    # - 无；计时器到期后调用现有单 backend probe
    def _schedule_exhausted_backend_probes(self) -> None:
        for tier_name in self._config._config.get("llm_tiers", {}):
            for model in self._config.get_tier_models(tier_name):
                if not self._router._quota.is_exhausted(model.backend, model.model_name):
                    continue
                self._schedule_exhausted_backend_probe_for_model(tier_name, model)

    # 用途：
    # - 根据 backend identity 查找配置模型并注册 exhausted 自动恢复 probe
    # 输入：
    # - tier_name/account/backend/model_name: backend identity
    # 输出：
    # - 无；找不到配置或未 exhausted 时不调度
    def _schedule_exhausted_backend_probe_for_identity(
        self,
        tier_name: str,
        account: str,
        backend: str,
        model_name: str,
    ) -> None:
        if not hasattr(self, "_exhausted_probe_timers"):
            return
        models = self._config.get_tier_models(str(tier_name or "").strip())
        target = next(
            (
                model for model in models
                if model.backend == backend
                and model.model_name == model_name
                and str(model.account or "").strip() == str(account or "").strip()
            ),
            None,
        )
        if target is not None and self._router._quota.is_exhausted(target.backend, target.model_name):
            self._schedule_exhausted_backend_probe_for_model(str(tier_name or "").strip(), target)

    # 用途：
    # - 为单个 exhausted backend 计算恢复时间并注册计时器
    # 输入：
    # - tier_name/model: Tier 名称和 backend 配置
    # 输出：
    # - 无；到期后触发 `_probe_single_backend`
    def _schedule_exhausted_backend_probe_for_model(self, tier_name: str, model: TierModel) -> None:
        if not hasattr(self, "_exhausted_probe_timers"):
            return
        if not self._router.is_backend_enabled(model.backend, model.model_name, tier_name=tier_name, account=model.account):
            return
        exhausted_info = self._router._quota.get_exhausted_info(model.backend, model.model_name)
        if not exhausted_info:
            return
        status_snapshot = self._backend_status_snapshot(tier_name, model.account, model.backend, model.model_name)
        provider_usage = status_snapshot.get("provider_usage") if isinstance(status_snapshot.get("provider_usage"), dict) else {}
        reset_at = str(exhausted_info.get("reset_at") or _provider_usage_reset_at(provider_usage) or "").strip()
        if reset_at:
            self._router._quota.update_exhausted_reset_at(model.backend, model.model_name, reset_at)
        due_epoch = self._exhausted_probe_due_epoch_for_info(exhausted_info, reset_at)
        if due_epoch is None:
            return
        key = self._backend_identity_key(tier_name, model.account, model.model_name)
        self._schedule_exhausted_backend_probe_timer(tier_name, model, key, due_epoch)

    # 用途：
    # - 计算 exhausted backend 下次 probe 的 Unix 秒时间
    # 输入：
    # - exhausted_info/reset_at: quota state 记录和仅用于展示的 provider reset 时间
    # 输出：
    # - 严格晚于当前时间的下一个600秒周期边界
    def _exhausted_probe_due_epoch_for_info(self, exhausted_info: dict[str, Any], reset_at: str) -> float | None:
        del reset_at
        now = time.time()
        try:
            exhausted_ts = float(exhausted_info.get("exhausted_ts") or 0.0)
        except (TypeError, ValueError):
            exhausted_ts = 0.0
        if exhausted_ts <= 0 or exhausted_ts > now:
            exhausted_ts = now
        elapsed_seconds = max(0.0, now - exhausted_ts)
        completed_intervals = int(elapsed_seconds // EXHAUSTED_PROBE_INTERVAL_SECONDS)
        return exhausted_ts + ((completed_intervals + 1) * EXHAUSTED_PROBE_INTERVAL_SECONDS)

    # 用途：
    # - 注册或更新 exhausted backend 的单次恢复 probe 计时器
    # 输入：
    # - tier_name/model/key/due_epoch: backend identity 和到期时间
    # 输出：
    # - 无；避免为同一 backend 重复注册相同计时器
    def _schedule_exhausted_backend_probe_timer(
        self,
        tier_name: str,
        model: TierModel,
        key: str,
        due_epoch: float,
    ) -> None:
        delay_seconds = max(EXHAUSTED_PROBE_MIN_DELAY_SECONDS, due_epoch - time.time())
        with self._lock:
            existing_due = self._exhausted_probe_due_epoch.get(key)
            existing_timer = self._exhausted_probe_timers.get(key)
            if existing_timer is not None and existing_timer.is_alive() and existing_due is not None:
                if abs(existing_due - due_epoch) < EXHAUSTED_PROBE_SCAN_SECONDS:
                    return
                existing_timer.cancel()
            timer = threading.Timer(
                delay_seconds,
                self._run_scheduled_exhausted_probe,
                args=(tier_name, model.account, model.backend, model.model_name, key, due_epoch),
            )
            timer.daemon = True
            self._exhausted_probe_timers[key] = timer
            self._exhausted_probe_due_epoch[key] = due_epoch
            timer.start()

    # 用途：
    # - 执行到期的 exhausted 自动恢复 probe
    # 输入：
    # - tier/account/backend/model_name/key/due_epoch: 注册计时器时的 backend identity
    # 输出：
    # - 无；未 exhausted 或计时器已过期时直接返回
    def _run_scheduled_exhausted_probe(
        self,
        tier_name: str,
        account: str,
        backend: str,
        model_name: str,
        key: str,
        due_epoch: float,
    ) -> None:
        if not hasattr(self, "_exhausted_probe_timers"):
            return
        with self._lock:
            current_due = self._exhausted_probe_due_epoch.get(key)
            if current_due is not None and abs(current_due - due_epoch) >= EXHAUSTED_PROBE_SCAN_SECONDS:
                return
            self._exhausted_probe_timers.pop(key, None)
            self._exhausted_probe_due_epoch.pop(key, None)
        if not getattr(self, "_running", False):
            return
        if not self._router._quota.is_exhausted(backend, model_name):
            return
        _log("scheduled exhausted probe %s/%s (%s)", tier_name, account, model_name)
        self._probe_single_backend(
            tier_name=tier_name,
            account=account,
            backend=backend,
            model_name=model_name,
        )

    # 用途：
    # - 取消指定 backend 的 exhausted 自动恢复 probe 计时器
    # 输入：
    # - key: `_backend_identity_key` 生成的 backend identity key
    # 输出：
    # - 无；用于 running/disabled/reset 后清理过期计时器
    def _cancel_exhausted_backend_probe(self, key: str) -> None:
        if not hasattr(self, "_exhausted_probe_timers"):
            return
        with self._lock:
            timer = self._exhausted_probe_timers.pop(key, None)
            self._exhausted_probe_due_epoch.pop(key, None)
        if timer is not None:
            timer.cancel()

    # 用途：
    # - 统一重置 quota exhausted 和 runtime backend 状态
    # 输入：
    # - tier_name: 可选 Tier 名称；为空时重置全部 Tier
    # 输出：
    # - 已恢复 runtime 状态的 backend key 列表
    def _reset_exhausted_runtime_state(self, tier_name: str = "") -> list[str]:
        normalized_tier = str(tier_name or "").strip()
        if normalized_tier:
            self._router._quota.reset_tier(normalized_tier)
        else:
            self._router._quota.reset_all()

        reset_keys = self._router.reset_runtime_statuses(normalized_tier)
        checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            for key in reset_keys:
                current = dict(self._backend_status.get(key) or {})
                current["status"] = "running"
                current["checked_at"] = checked_at
                current.pop("started_at_epoch", None)
                current.pop("timeout_seconds", None)
                current.pop("probe_id", None)
                current.pop("last_error", None)
                current.pop("last_error_type", None)
                current.pop("last_error_at", None)
                current.pop("failure_count", None)
                self._backend_status[key] = current
        return reset_keys

    # 用途：
    # - 启动一次由 server 状态机管理的 probing，并记录开始时间与 timeout
    # 输入：
    # - backend/model_name/timeout_seconds: backend 标识与本次 probe 的超时秒数
    # 输出：
    # - 本次 probe 操作编号；只有持有该编号的完成回调才允许回写最终状态
    def _begin_probe(self, tier_name: str, account: str, backend: str, model_name: str, timeout_seconds: int) -> str:
        key = self._backend_identity_key(tier_name, account, model_name)
        probe_id = str(uuid.uuid4())
        started_at_epoch = time.time()
        self._router.set_backend_runtime_status(backend, model_name, "probing", tier_name=tier_name, account=account)
        with self._lock:
            self._backend_status[key] = {
                "status": "probing",
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at_epoch)),
                "started_at_epoch": started_at_epoch,
                "timeout_seconds": int(timeout_seconds or 0),
                "probe_id": probe_id,
            }
        return probe_id

    # 用途：
    # - 读取 backend 状态快照，并在 probing 非法或超时后由 server 主动收口为 unreachable
    # 输入：
    # - backend/model_name: backend 标识
    # 输出：
    # - 当前 backend 状态快照；超时时返回已收口后的 unreachable 快照
    def _backend_status_snapshot(self, tier_name: str, account: str, backend: str, model_name: str) -> dict[str, Any]:
        key = self._backend_identity_key(tier_name, account, model_name)
        with self._lock:
            snapshot = dict(self._backend_status.get(key) or {})
        checked_at_epoch = float(snapshot.get("checked_at_epoch") or 0.0)
        snapshot["fresh"] = checked_at_epoch > 0 and time.time() - checked_at_epoch <= PROBE_STATUS_FRESH_SECONDS
        if str(snapshot.get("status") or "") == "exhausted" and self._router.backend_runtime_status(
            backend,
            model_name,
            tier_name=tier_name,
            account=account,
        ) == "running":
            self._set_backend_status(tier_name, account, backend, model_name, "running")
            with self._lock:
                refreshed = dict(self._backend_status.get(key) or {})
            refreshed["fresh"] = True
            return refreshed
        if str(snapshot.get("status") or "") != "probing":
            return snapshot
        started_at_epoch = float(snapshot.get("started_at_epoch") or 0.0)
        timeout_seconds = int(snapshot.get("timeout_seconds") or 0)
        if started_at_epoch <= 0 or timeout_seconds <= 0:
            self._router._record_unhealthy_failure(
                backend,
                model_name,
                "probe state missing timeout metadata",
                tier_name=tier_name,
                account=account,
                source="probe",
            )
            self._sync_backend_meta_from_router(tier_name, account, backend, model_name)
            self._set_backend_status(tier_name, account, backend, model_name, "unreachable")
            with self._lock:
                return dict(self._backend_status.get(key) or {})
        if time.time() - started_at_epoch <= timeout_seconds:
            return snapshot
        self._router._record_unhealthy_failure(
            backend,
            model_name,
            f"probe timed out after {timeout_seconds}s",
            tier_name=tier_name,
            account=account,
            source="probe",
        )
        self._sync_backend_meta_from_router(tier_name, account, backend, model_name)
        self._set_backend_status(tier_name, account, backend, model_name, "unreachable")
        with self._lock:
            return dict(self._backend_status.get(key) or {})

    # 用途：
    # - 记录状态机的补充元数据，但不改变主状态
    # 输入：
    # - backend/model_name 和需要更新的键值对
    # 输出：
    # - 无；覆盖更新内存中的唯一当前态
    def _update_backend_state_meta(self, tier_name: str, account: str, backend: str, model_name: str, **fields: Any) -> None:
        key = self._backend_identity_key(tier_name, account, model_name)
        with self._lock:
            current = dict(self._backend_status.get(key) or {})
            for field_name, field_value in fields.items():
                current[field_name] = field_value
            self._backend_status[key] = current

    # 用途：
    # - 将 router 内部的 failure/error 补充元数据同步到 server 当前态
    # 输入：
    # - backend/model_name: backend 标识
    # 输出：
    # - 无；只刷新 server 当前态里的补充字段
    def _sync_backend_meta_from_router(self, tier_name: str, account: str, backend: str, model_name: str) -> None:
        runtime_meta = self._router.backend_runtime_meta(backend, model_name, tier_name=tier_name, account=account)
        self._update_backend_state_meta(
            tier_name,
            account,
            backend,
            model_name,
            failure_count=int(runtime_meta.get("failure_count") or 0),
            last_error=str(runtime_meta.get("last_error") or ""),
            last_error_type=str(runtime_meta.get("last_error_type") or ""),
            last_error_at=str(runtime_meta.get("last_error_at") or ""),
        )

    # 用途：
    # - 在 backend probe 收口前刷新当前 backend 的 provider usage，并缓存到 runtime 状态
    # 输入：
    # - model: 当前 probe 的 backend 配置
    # 输出：
    # - provider usage snapshot；刷新失败时返回显式错误状态，不让 Dashboard 猜测
    def _refresh_provider_usage_for_probe(self, tier_name: str, model: TierModel) -> dict[str, Any]:
        usage_key = provider_usage_key(model)
        try:
            snapshot = self._provider_usage.refresh_for_model(model)
        except Exception as exc:  # noqa: BLE001
            snapshot = {
                "provider": resolved_quota_provider(model),
                "source": "provider_usage_error",
                "status": "unavailable",
                "usage_key": usage_key,
                "account_key": usage_key.rsplit(":", 1)[-1] if ":" in usage_key else usage_key,
                "used": None,
                "quota": None,
                "remaining": None,
                "percent": None,
                "reset_at": "",
                "window": "",
                "windows": [],
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": f"{exc.__class__.__name__}:{str(exc)[:160]}",
            }
        self._update_backend_state_meta(tier_name, model.account, model.backend, model.model_name, provider_usage=snapshot)
        reset_at = _provider_usage_reset_at(snapshot)
        if reset_at:
            self._router._quota.update_exhausted_reset_at(model.backend, model.model_name, reset_at)
        return dict(snapshot)

    # 用途：
    # - 只有当前活跃 probe 自己才能回写最终状态，避免超时后的旧结果覆盖新状态
    # 输入：
    # - backend/model_name/probe_id/status: backend 标识、本次 probe 编号和目标状态
    # 输出：
    # - True 表示成功提交状态；False 表示 probe 已过期或已被 server 收口
    def _finish_probe_if_current(self, tier_name: str, account: str, backend: str, model_name: str, probe_id: str, status: str) -> bool:
        key = self._backend_identity_key(tier_name, account, model_name)
        with self._lock:
            snapshot = dict(self._backend_status.get(key) or {})
        if str(snapshot.get("status") or "") != "probing":
            return False
        if str(snapshot.get("probe_id") or "") != str(probe_id or ""):
            return False
        self._set_backend_status(tier_name, account, backend, model_name, status)
        return True

    # 用途：
    # - 将 runtime/probe 原始状态归一到唯一的主状态基础集合
    # 输入：
    # - probe_status/exhausted: 最近一次 runtime 或 probe 状态，以及 quota exhausted 标记
    # 输出：
    # - `disabled/probing/unreachable/exhausted/running`
    def _normalize_backend_probe_state(self, *, probe_status: str, exhausted: bool) -> str:
        normalized_probe_status = str(probe_status or "").strip().lower()
        if normalized_probe_status == "disabled":
            return "disabled"
        if normalized_probe_status == "probing":
            return "probing"
        if normalized_probe_status == "cooldown":
            return "disabled"
        if normalized_probe_status in {"error", "unreachable", "offline", "failed"}:
            return "unreachable"
        if normalized_probe_status == "exhausted":
            return "exhausted"
        if exhausted:
            return "exhausted"
        if normalized_probe_status == "running":
            return "running"
        return "running"

    # 用途：
    # - 对单个 backend 触发手工 probe，并立即暴露 probing 状态给 dashboard
    # 输入：
    # - tier_name/account/backend/model_name: 页面指定的 Backend identity
    # 输出：
    # - probe 启动结果；最终状态由后台 probe 线程回写
    def _probe_single_backend(self, *, tier_name: str, account: str, backend: str, model_name: str) -> dict[str, Any]:
        normalized_tier = str(tier_name or "").strip()
        normalized_account = str(account or "").strip()
        normalized_backend = str(backend or "").strip()
        normalized_model = str(model_name or "").strip()
        if not normalized_account:
            return {"ok": False, "error": "missing_account"}
        models = self._config.get_tier_models(normalized_tier)
        target = next(
            (
                model for model in models
                if model.backend == normalized_backend and model.model_name == normalized_model
                and str(model.account or "").strip() == normalized_account
            ),
            None,
        )
        if target is None:
            return {"ok": False, "error": "backend_model_not_found"}
        if not self._router.is_backend_enabled(target.backend, target.model_name, tier_name=normalized_tier, account=target.account):
            return {"ok": False, "error": "backend_disabled"}
        try:
            creds = self._router._get_backend_credentials(
                target.backend,
                target.provider,
                target.model_name,
                target.model_key,
                target.account,
            )
            probe_timeout = self._probe_timeout_seconds(target.backend_type, creds)
            probe_id = self._begin_probe(normalized_tier, target.account, target.backend, target.model_name, probe_timeout)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        thread = threading.Thread(
            target=self._run_single_backend_probe,
            args=(normalized_tier, target, creds, probe_timeout, probe_id),
            daemon=True,
        )
        thread.start()
        return {
            "ok": True,
            "status": "probing",
            "tier_name": normalized_tier,
            "backend": target.backend,
            "model_name": target.model_name,
        }

    # 用途：
    # - 执行单个 backend 的后台 probe，并将最终状态写回 server backend status
    # 输入：
    # - tier_name/model/creds/probe_timeout/probe_id: probe 上下文和当前 probe 编号
    # 输出：
    # - 无；只更新 Backend probe 状态，不写入 invoke LLM call 统计
    def _run_single_backend_probe(
        self,
        tier_name: str,
        model: TierModel,
        creds: dict[str, Any],
        probe_timeout: int,
        probe_id: str,
    ) -> None:
        try:
            from llm_tier.backends import get_backend_client
            client_name = backend_client_name(model)
            client = get_backend_client(client_name, **creds)
            if client is None:
                self._router._record_unhealthy_failure(
                    model.backend,
                    model.model_name,
                    "probe client missing",
                    tier_name=tier_name,
                    account=model.account,
                    source="probe",
                )
                self._finish_probe_if_current(tier_name, model.account, model.backend, model.model_name, probe_id, "unreachable")
                return
            result = client.call(
                model_name=backend_call_model_name(model),
                prompt=PROBE_PROMPT,
                timeout_seconds=probe_timeout,
                max_tokens=16,
            )
            if bool(result.get("ok", False)):
                self._router._quota.reset_backend(model.backend, model.model_name)
                self._router._record_backend_success(model.backend, model.model_name, tier_name=tier_name, account=model.account)
                self._sync_backend_meta_from_router(tier_name, model.account, model.backend, model.model_name)
                self._refresh_provider_usage_for_probe(tier_name, model)
                self._finish_probe_if_current(tier_name, model.account, model.backend, model.model_name, probe_id, "running")
                return
            self._router._record_unhealthy_failure(
                model.backend,
                model.model_name,
                "probe returned not ok",
                tier_name=tier_name,
                account=model.account,
                source="probe",
            )
            self._sync_backend_meta_from_router(tier_name, model.account, model.backend, model.model_name)
            self._refresh_provider_usage_for_probe(tier_name, model)
            self._finish_probe_if_current(tier_name, model.account, model.backend, model.model_name, probe_id, "unreachable")
        except QuotaExhaustedError as exc:
            self._router._quota.mark_exhausted(model.backend, model.model_name, str(exc))
            self._sync_backend_meta_from_router(tier_name, model.account, model.backend, model.model_name)
            self._refresh_provider_usage_for_probe(tier_name, model)
            self._finish_probe_if_current(tier_name, model.account, model.backend, model.model_name, probe_id, "exhausted")
        except BackendCallError as exc:
            self._router._record_unhealthy_failure(
                model.backend,
                model.model_name,
                str(exc),
                tier_name=tier_name,
                account=model.account,
                source="probe",
            )
            self._sync_backend_meta_from_router(tier_name, model.account, model.backend, model.model_name)
            self._refresh_provider_usage_for_probe(tier_name, model)
            self._finish_probe_if_current(tier_name, model.account, model.backend, model.model_name, probe_id, "unreachable")
        except Exception as exc:
            self._router._record_unhealthy_failure(
                model.backend,
                model.model_name,
                str(exc),
                tier_name=tier_name,
                account=model.account,
                source="probe",
            )
            self._sync_backend_meta_from_router(tier_name, model.account, model.backend, model.model_name)
            self._refresh_provider_usage_for_probe(tier_name, model)
            self._finish_probe_if_current(tier_name, model.account, model.backend, model.model_name, probe_id, "unreachable")

    # 用途：
    # - 在 runtime 中手工启用或禁用某个 backend，并在 enable 后触发 probe
    # 输入：
    # - tier_name/account/backend/model_name/enabled: 页面指定 Backend 和目标 admin state
    # 输出：
    # - 更新结果与最终状态
    def _update_backend_enabled(
        self,
        *,
        tier_name: str,
        account: str,
        backend: str,
        model_name: str,
        enabled: bool,
    ) -> dict[str, Any]:
        normalized_tier = str(tier_name or "").strip()
        normalized_account = str(account or "").strip()
        normalized_backend = str(backend or "").strip()
        normalized_model = str(model_name or "").strip()
        if not normalized_account:
            return {"ok": False, "error": "missing_account"}
        raw_models = self._config._config.get("llm_tiers", {}).get(normalized_tier)
        if not isinstance(raw_models, list):
            return {"ok": False, "error": "tier_not_found"}
        target_found = False
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                continue
            if str(raw_model.get("backend") or "").strip() != normalized_backend:
                continue
            if str(raw_model.get("account") or "").strip() != normalized_account:
                continue
            if str(raw_model.get("model_name") or "").strip() != normalized_model:
                continue
            raw_model["enabled"] = bool(enabled)
            target_found = True
            break
        if not target_found:
            return {"ok": False, "error": "backend_model_not_found"}
        self._router.set_backend_enabled(
            normalized_backend,
            normalized_model,
            bool(enabled),
            tier_name=normalized_tier,
            account=normalized_account,
        )
        if not enabled:
            self._set_backend_status(normalized_tier, normalized_account, normalized_backend, normalized_model, "disabled")
            return {"ok": True, "admin_state": "disabled", "status": "disabled"}
        probe_result = self._probe_single_backend(
            tier_name=normalized_tier,
            account=normalized_account,
            backend=normalized_backend,
            model_name=normalized_model,
        )
        return {
            "ok": bool(probe_result.get("ok")),
            "admin_state": "enabled",
            "status": str(probe_result.get("status") or "probing"),
            "probe": probe_result,
        }

    # 用途：
    # - 将当前 runtime 可持久化配置写回 settings.json
    # 输入：
    # - 无；读取当前内存中的 model_name、enabled 和 weight
    # 输出：
    # - 保存结果
    def _save_runtime_config(self) -> dict[str, Any]:
        persisted = self._config.persist()
        return {"ok": persisted}

    # 用途：
    # - 从 settings.json 重新加载 runtime 配置并重建 router
    # 输入：
    # - 无；读取当前 settings_path
    # 输出：
    # - 重新加载结果
    def _load_runtime_config(self) -> dict[str, Any]:
        ok = self._config.reload()
        if not ok:
            return {"ok": False}
        self._router = LLMRouter(self._config, state_dir=self._stats_dir, trace_hook=self._trace)
        self._backend_status = {}
        self._load_runtime_config_state()
        probe_started = self._start_backend_probe()
        return {"ok": True, "probe_started": probe_started}

    # 用途：
    # - 清空 provider usage cache 并强制刷新 runtime 中的 provider usage
    # 输入：
    # - 无；provider usage 自行从当前配置指向的 cookie/key 文件读取凭据
    # 输出：
    # - 刷新后的 runtime snapshot；失败时错误保留在 provider_usage 字段中
    def _reload_provider_usage(self) -> dict[str, Any]:
        self._provider_usage.clear_cache()
        return self._build_runtime_snapshot(force_usage_refresh=True, include_stats=False)

    # 用途：
    # - 在不重启 tier server 的情况下修改 backend 选用模型，并同步 provider profile 能力字段
    # 输入：
    # - tier_name/account/backend/old_model_name/new_model_name/new_model_key: 页面提交的 Backend identity 和新模型标注
    # 输出：
    # - 更新结果；同时持久化 model_name/model_key/max_context_tokens
    def _update_runtime_model_name(
        self,
        *,
        tier_name: str,
        account: str,
        backend: str,
        old_model_name: str,
        new_model_name: str,
        new_model_key: str = "",
    ) -> dict[str, Any]:
        tier_name = str(tier_name or "").strip()
        account = str(account or "").strip()
        backend = str(backend or "").strip()
        old_model_name = str(old_model_name or "").strip()
        new_model_name = str(new_model_name or "").strip()
        new_model_key = str(new_model_key or "").strip()
        if not tier_name or not account or not backend or not new_model_name:
            return {"ok": False, "error": "missing tier_name, account, backend, or model_name"}

        tiers = self._config._config.get("llm_tiers", {})
        raw_models = tiers.get(tier_name)
        if not isinstance(raw_models, list):
            return {"ok": False, "error": "tier_not_found"}

        updated = False
        updated_context_tokens = 0
        updated_model_key = new_model_key
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                continue
            if str(raw_model.get("backend") or "").strip() != backend:
                continue
            if str(raw_model.get("account") or "").strip() != account:
                continue
            current_model_name = str(raw_model.get("model_name") or "").strip()
            if old_model_name and current_model_name != old_model_name:
                continue
            raw_model["model_name"] = new_model_name
            provider = str(raw_model.get("provider") or raw_model.get("backend") or "").strip()
            profile_models = self._config.get_provider_profile_models(provider)
            profile_model = next(
                (
                    item for item in profile_models
                    if str(item.get("model_key") or "") == new_model_key
                    or str(item.get("model_name") or "") == new_model_name
                ),
                {},
            )
            resolved_model_key = str(profile_model.get("model_key") or new_model_key or "").strip()
            if resolved_model_key:
                raw_model["model_key"] = resolved_model_key
                updated_model_key = resolved_model_key
            try:
                updated_context_tokens = int(profile_model.get("max_context_tokens") or 0)
            except (TypeError, ValueError):
                updated_context_tokens = 0
            if updated_context_tokens > 0:
                raw_model["max_context_tokens"] = updated_context_tokens
            updated = True
            break
        if not updated:
            return {"ok": False, "error": "backend_model_not_found"}

        old_key = self._backend_identity_key(tier_name, account, old_model_name) if old_model_name else ""
        new_key = self._backend_identity_key(tier_name, account, new_model_name)
        with self._lock:
            if old_key and old_key in self._backend_status and new_key not in self._backend_status:
                self._backend_status[new_key] = dict(self._backend_status[old_key])
        self._router.set_backend_enabled(backend, new_model_name, True, tier_name=tier_name, account=account)
        probe_result = self._probe_single_backend(
            tier_name=tier_name,
            account=account,
            backend=backend,
            model_name=new_model_name,
        )

        settings_path = self._config.__dict__.get("_settings_path")
        persisted = False
        if settings_path:
            persisted = self._config.persist()
            if not persisted:
                persist_error = str(self._config.__dict__.get("_last_persist_error") or "")
                return {
                    "ok": True,
                    "model_name": new_model_name,
                    "model_key": updated_model_key,
                    "max_context_tokens": updated_context_tokens,
                    "persisted": False,
                    "warning": "persist_failed",
                    "persist_error": persist_error,
                    "probe": probe_result,
                }

        return {
            "ok": True,
            "model_name": new_model_name,
            "model_key": updated_model_key,
            "max_context_tokens": updated_context_tokens,
            "persisted": persisted,
            "probe": probe_result,
        }

    # 用途：
    # - 构造 tier server 当前在线 runtime 快照，供 dashboard 渲染状态与可选统计
    # 输入：
    # - force_usage_refresh: 是否忽略 provider usage cache 并重新查询 provider
    # - include_stats: 是否同步读取 SQLite LLM stats、recent errors 和 backend stats
    # 输出：
    # - 可 JSON 序列化的 runtime payload
    def _build_runtime_snapshot(self, *, force_usage_refresh: bool = False, include_stats: bool = True) -> dict[str, Any]:
        with self._lock:
            probe_running = self._probe_running
        stats_snapshot = self._runtime_stats_snapshot() if include_stats else {}
        stats_by_key = dict(stats_snapshot.get("stats_by_key") or {})
        recent_error_events = list(stats_snapshot.get("recent_errors") or [])
        stats_summary = dict(stats_snapshot.get("summary") or {})

        exhausted_reset: dict[str, str] = {}
        for entry in self._router._quota.get_all_exhausted():
            exhausted_reset[str(entry.get("key") or "")] = str(entry.get("reset_at") or "")

        tiers: dict[str, list[dict[str, Any]]] = {}
        account_backend_counts: dict[str, int] = {}
        account_stat_keys: dict[str, set[str]] = {}
        usage_account_providers: dict[str, str] = {}
        usage_account_counts: dict[str, int] = {}
        usage_account_stat_keys: dict[str, set[str]] = {}
        usage_account_runtime_keys: dict[str, set[str]] = {}
        account_provider_usage: dict[str, dict[str, Any]] = {}
        active_backend_jobs, active_account_jobs = self._active_job_runtime_counts()
        for tier_name in self._config._config.get("llm_tiers", {}):
            models = self._config.get_tier_models(tier_name)
            tier_rows: list[dict[str, Any]] = []
            for model in models:
                account_key = str(model.account or "").strip()
                runtime_key = self._backend_identity_key(tier_name, account_key, model.model_name)
                stats_key = runtime_key
                usage_account_key = str(model.usage_account or account_key).strip()
                if account_key:
                    account_backend_counts[account_key] = account_backend_counts.get(account_key, 0) + 1
                    account_stat_keys.setdefault(account_key, set()).add(stats_key)
                if usage_account_key:
                    usage_account_counts[usage_account_key] = usage_account_counts.get(usage_account_key, 0) + 1
                    usage_account_stat_keys.setdefault(usage_account_key, set()).add(stats_key)
                    usage_account_runtime_keys.setdefault(usage_account_key, set()).add(account_key or runtime_key)
                capabilities = self._config.get_backend_capabilities(
                    model.backend,
                    model_name=model.model_name,
                    model_key=model.model_key,
                )
                probe_status = self._backend_status_snapshot(tier_name, account_key, model.backend, model.model_name)
                router_status = self._router.backend_runtime_status(
                    model.backend,
                    model.model_name,
                    tier_name=tier_name,
                    account=account_key,
                )
                router_meta = self._router.backend_runtime_meta(
                    model.backend,
                    model.model_name,
                    tier_name=tier_name,
                    account=account_key,
                )
                account_quota_key = f"account:{account_key}" if account_key else key
                exhausted = (
                    str(probe_status.get("status") or "").strip().lower() == "exhausted"
                    or self._router._quota.is_exhausted(model.backend, model.model_name)
                )
                admin_enabled = self._router.is_backend_enabled(model.backend, model.model_name, tier_name=tier_name, account=account_key)
                runtime_status = str(router_status or "")
                backend_running = self._router._concurrency.get_load(runtime_key) + active_backend_jobs.get(runtime_key, 0)
                state = self._runtime_backend_state(
                    admin_enabled=admin_enabled,
                    running=backend_running,
                    exhausted=exhausted,
                    probe_status=runtime_status,
                )
                active = self._active_backend(
                    admin_enabled=admin_enabled,
                    exhausted=exhausted,
                    probe_status=runtime_status,
                )
                if force_usage_refresh:
                    provider_usage = self._provider_usage.usage_for_model(model, force_refresh=True)
                    self._update_backend_state_meta(tier_name, account_key, model.backend, model.model_name, provider_usage=provider_usage)
                elif isinstance(probe_status.get("provider_usage"), dict):
                    provider_usage = dict(probe_status.get("provider_usage"))
                else:
                    provider_usage = self._provider_usage.usage_for_model(model, force_refresh=False)
                if usage_account_key:
                    usage_account_providers.setdefault(
                        usage_account_key,
                        resolved_quota_provider(model),
                    )
                    existing_usage = account_provider_usage.get(usage_account_key) or {}
                    existing_status = str(existing_usage.get("status") or "").strip().lower()
                    current_status = str((provider_usage or {}).get("status") or "").strip().lower()
                    if not existing_usage or (existing_status not in {"ok", "estimated"} and current_status in {"ok", "estimated"}):
                        account_provider_usage[usage_account_key] = dict(provider_usage or {})
                tier_rows.append({
                    "tier": tier_name,
                    "identity": runtime_key,
                    "backend": model.backend,
                    "provider": model.provider,
                    "account": account_key,
                    "usage_account": usage_account_key,
                    "model_name": model.model_name,
                    "model_key": model.model_key,
                    "provider_profile_models": self._config.get_provider_profile_models(model.provider),
                    "backend_type": model.backend_type,
                    "max_context_tokens": int(capabilities.get("max_context_tokens") or 0),
                    "reserved_completion_tokens": int(capabilities.get("reserved_completion_tokens") or 0),
                    "max_output_tokens": int(capabilities.get("max_output_tokens") or 0),
                    "weight": float(model.weight or 1.0),
                    "admin_state": "enabled" if admin_enabled else "disabled",
                    "enabled": admin_enabled,
                    "state": state,
                    "active": active,
                    "exhausted": exhausted,
                    "probe_status": self._normalize_backend_probe_state(
                        probe_status=runtime_status,
                        exhausted=exhausted,
                    ),
                    "probe_checked_at": probe_status.get("checked_at", ""),
                    "reset_at": exhausted_reset.get(account_quota_key, "") or exhausted_reset.get(runtime_key, ""),
                    "provider_usage": provider_usage,
                    "failure_count": int(router_meta.get("failure_count") or 0),
                    "failure_threshold": int(self._router._failure_threshold),
                    "last_error": str(router_meta.get("last_error") or ""),
                    "last_error_type": str(router_meta.get("last_error_type") or ""),
                    "last_error_at": str(router_meta.get("last_error_at") or ""),
                    "load": backend_running,
                    "running": backend_running,
                    "stats": stats_by_key.get(stats_key, {
                        "calls": 0,
                        "success_count": 0,
                        "fail_count": 0,
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "prompt_tokens_avg": 0,
                        "prompt_tokens_p50": 0,
                        "prompt_tokens_p95": 0,
                        "prompt_tokens_p99": 0,
                        "completion_tokens_avg": 0,
                        "completion_tokens_p50": 0,
                        "completion_tokens_p95": 0,
                        "completion_tokens_p99": 0,
                        "prompt_chars": 0,
                        "prompt_chars_avg": 0,
                        "prompt_chars_p50": 0,
                        "prompt_chars_p95": 0,
                        "prompt_chars_p99": 0,
                        "completion_chars": 0,
                        "completion_chars_avg": 0,
                        "completion_chars_p50": 0,
                        "completion_chars_p95": 0,
                        "completion_chars_p99": 0,
                        "latency_avg_ms": 0,
                        "latency_p50_ms": 0,
                        "latency_p90_ms": 0,
                        "latency_p95_ms": 0,
                        "latency_p99_ms": 0,
                        "fallback_count": 0,
                    }),
                })
            tiers[tier_name] = tier_rows

        configured_accounts = {account.account_id: account for account in self._config.get_accounts()}
        accounts = []
        for account_key in usage_account_counts:
            account = configured_accounts.get(account_key)
            provider = account.provider if account is not None else usage_account_providers.get(account_key, account_key)
            account_quota_key = f"account:{account_key}"
            account_stats = {
                "calls": 0,
                "success_count": 0,
                "fail_count": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
            for stats_key in sorted(usage_account_stat_keys.get(account_key, set())):
                backend_stats = stats_by_key.get(stats_key) or {}
                for field in account_stats:
                    account_stats[field] += int(backend_stats.get(field) or 0)
            running = 0
            max_concurrent_requests = 0
            min_request_interval_ms = 0
            requests_per_minute = 0
            for runtime_account_key in sorted(usage_account_runtime_keys.get(account_key, set())):
                running += self._router._concurrency.get_account_load(runtime_account_key)
                running += active_account_jobs.get(runtime_account_key, 0)
                max_concurrent_requests += self._router._concurrency.get_account_limit(runtime_account_key)
            if account is not None:
                min_request_interval_ms = account.min_request_interval_ms
                requests_per_minute = account.requests_per_minute
                if not max_concurrent_requests:
                    max_concurrent_requests = self._router._concurrency.get_account_limit(account_key)
            accounts.append({
                "account": account_key,
                "provider": provider,
                "running": running,
                "max_concurrent_requests": max_concurrent_requests,
                "min_request_interval_ms": min_request_interval_ms,
                "requests_per_minute": requests_per_minute,
                "backend_count": int(usage_account_counts.get(account_key, 0)),
                "exhausted": account_quota_key in exhausted_reset,
                "reset_at": exhausted_reset.get(account_quota_key, ""),
                "stats": account_stats,
                "provider_usage": account_provider_usage.get(account_key, {}),
            })

        return {
            "ok": True,
            "host": self.host,
            "port": self.port,
            "running": self._running,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._started_at_epoch)),
            "uptime_seconds": max(0.0, time.time() - self._started_at_epoch),
            "probe_running": probe_running,
            "debug": self._runtime_debug_snapshot(),
            "tier_enabled": self._config.is_enabled(),
            "jobs": self._job_summary(),
            "summary": {
                **stats_summary,
                "exhausted_count": len(exhausted_reset),
                "upshift_count": self._router.upshift_count(),
            },
            "tiers": tiers,
            "accounts": accounts,
            "recent_errors": recent_error_events,
            "exhausted_backends": self._router._quota.get_all_exhausted(),
        }

    # 用途：
    # - 修改 backend 自身的调度权重
    # 输入：
    # - tier_name/account/backend/model_name/weight: Backend identity 和新权重
    # 输出：
    # - 操作结果；非法 tier/backend 返回错误
    def _update_backend_weight(
        self,
        *,
        tier_name: str,
        account: str,
        backend: str,
        model_name: str,
        weight: float | int | str = 1.0,
    ) -> dict[str, Any]:
        normalized_tier = str(tier_name or "").strip()
        if normalized_tier not in self._config._config.get("llm_tiers", {}):
            return {"ok": False, "error": "unknown_tier", "tier_name": normalized_tier}
        normalized_account = str(account or "").strip()
        if not normalized_account:
            return {"ok": False, "error": "missing_account"}
        normalized_backend = str(backend or "").strip()
        normalized_model = str(model_name or "").strip()
        try:
            resolved_weight = int(round(float(weight)))
        except (TypeError, ValueError):
            resolved_weight = 1
        if resolved_weight <= 0:
            resolved_weight = 1
        raw_models = self._config._config.get("llm_tiers", {}).get(normalized_tier)
        if not isinstance(raw_models, list):
            return {"ok": False, "error": "tier_not_found", "tier_name": normalized_tier}
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                continue
            if str(raw_model.get("backend") or "").strip() != normalized_backend:
                continue
            if str(raw_model.get("account") or "").strip() != normalized_account:
                continue
            if str(raw_model.get("model_name") or "").strip() != normalized_model:
                continue
            raw_model["weight"] = resolved_weight
            return {
                "ok": True,
                "tier_name": normalized_tier,
                "account": normalized_account,
                "backend": normalized_backend,
                "model_name": normalized_model,
                "weight": resolved_weight,
            }
        return {
            "ok": False,
            "error": "backend_model_not_found",
            "tier_name": normalized_tier,
            "account": normalized_account,
            "backend": normalized_backend,
            "model_name": normalized_model,
        }

    # 用途：
    # - 修改 account 级最大并发数并同步 runtime 并发管理器
    # 输入：
    # - account/max_concurrent_requests: 账号标识和新最大并发数
    # 输出：
    # - 操作结果；成功后当前 server 后续 acquire 立即使用新上限
    def _update_account_concurrency(
        self,
        *,
        account: str,
        max_concurrent_requests: float | int | str = 1,
    ) -> dict[str, Any]:
        normalized_account = str(account or "").strip()
        raw_accounts = self._config._config.get("llm_accounts", {})
        if not normalized_account or not isinstance(raw_accounts, dict) or normalized_account not in raw_accounts:
            return {"ok": False, "error": "account_not_found", "account": normalized_account}
        try:
            resolved_limit = int(round(float(max_concurrent_requests)))
        except (TypeError, ValueError):
            resolved_limit = 1
        resolved_limit = max(1, resolved_limit)
        raw_account = raw_accounts.get(normalized_account)
        if not isinstance(raw_account, dict):
            return {"ok": False, "error": "account_not_found", "account": normalized_account}
        raw_account["max_concurrent_requests"] = resolved_limit
        self._router._concurrency.set_account_limit(normalized_account, resolved_limit)
        return {
            "ok": True,
            "account": normalized_account,
            "max_concurrent_requests": resolved_limit,
        }

    # 用途：
    # - 统一 runtime backend 运行状态名称，供 dashboard 直接映射图标
    # 输入：
    # - admin_enabled/running/exhausted/probe_status: 启用开关、当前并发、quota 与 probe 状态
    # 输出：
    # - disabled/running/probing/unreachable/exhausted；不会对外返回 ok
    def _runtime_backend_state(
        self,
        *,
        admin_enabled: bool,
        running: int,
        exhausted: bool,
        probe_status: str,
    ) -> str:
        if not admin_enabled:
            return "disabled"
        normalized_state = self._normalize_backend_probe_state(
            probe_status=probe_status,
            exhausted=exhausted,
        )
        if normalized_state in {"probing", "unreachable", "exhausted"}:
            return normalized_state
        if int(running or 0) > 0:
            return "running"
        if normalized_state == "running":
            return "running"
        return "unreachable"

    # 用途：
    # - 判断 backend 当前是否属于可调度池
    # 输入：
    # - admin_enabled/exhausted/probe_status: 启用属性和健康状态
    # 输出：
    # - True 表示该 backend 当前计入 Tier running/max 汇总和路由候选
    def _active_backend(
        self,
        *,
        admin_enabled: bool,
        exhausted: bool,
        probe_status: str,
    ) -> bool:
        if not admin_enabled:
            return False
        normalized_state = self._normalize_backend_probe_state(
            probe_status=probe_status,
            exhausted=exhausted,
        )
        return normalized_state == "running"

    # 用途：
    # - 统计 router concurrency 中真实占用 backend slot 的普通调用数
    # 输入：
    # - 无；读取当前 tier 配置和 router concurrency
    # 输出：
    # - backend slot 正在运行的普通调用数
    def _router_running_count(self) -> int:
        if not hasattr(self, "_config") or not hasattr(self, "_router"):
            return 0
        runtime_keys: set[str] = set()
        for tier_name in self._config._config.get("llm_tiers", {}):
            for model in self._config.get_tier_models(tier_name):
                account_key = str(model.account or "").strip()
                runtime_keys.add(self._backend_identity_key(tier_name, account_key, model.model_name))
        return sum(self._router._concurrency.get_load(runtime_key) for runtime_key in runtime_keys)

    # 用途：
    # - 统计绕过 router concurrency 的 direct job backend/account 运行数
    # 输入：
    # - 无；读取内存 job 表中的 runtime_key/account 绑定
    # 输出：
    # - (backend runtime key -> running count, account key -> running count)
    def _active_job_runtime_counts(self) -> tuple[dict[str, int], dict[str, int]]:
        backend_counts: dict[str, int] = {}
        account_counts: dict[str, int] = {}
        with self._lock:
            jobs = [dict(job) for job in self._jobs.values()]
        for job in jobs:
            if str(job.get("status") or "") != "running":
                continue
            runtime_key = str(job.get("runtime_key") or "").strip()
            if not runtime_key:
                continue
            account_key = str(job.get("account") or "").strip()
            backend_counts[runtime_key] = backend_counts.get(runtime_key, 0) + 1
            if account_key:
                account_counts[account_key] = account_counts.get(account_key, 0) + 1
        return backend_counts, account_counts

    # 用途：
    # - 将未完成 job 标记为等待 backend slot/重试的 pending 状态
    # 输入：
    # - job_id/status/client_request_id: job 标识、等待状态和可选 client request id
    # 输出：
    # - 无；清除 backend runtime 绑定，避免 pending job 被当作真实运行
    def _mark_job_pending(self, job_id: str, *, status: str = "pending", client_request_id: str = "") -> None:
        with self._lock:
            current = dict(self._jobs.get(job_id) or {})
            current["status"] = status
            if client_request_id:
                current["client_request_id"] = client_request_id
            current.pop("runtime_key", None)
            current.pop("tier", None)
            current.pop("account", None)
            current.pop("backend", None)
            current.pop("model_name", None)
            self._jobs[job_id] = current

    # 用途：
    # - 将 direct/escalation job 标记为正在占用指定 backend runtime identity
    # 输入：
    # - job_id/tier_name/account/backend/model_name: job 和 backend identity
    # 输出：
    # - 无；写入 runtime_key 供 runtime snapshot/backend table 计数
    def _mark_job_running_backend(
        self,
        job_id: str,
        *,
        tier_name: str,
        account: str,
        backend: str,
        model_name: str,
    ) -> None:
        runtime_key = self._backend_identity_key(tier_name, account, model_name)
        with self._lock:
            current = dict(self._jobs.get(job_id) or {})
            current.update({
                "status": "running",
                "runtime_key": runtime_key,
                "tier": tier_name,
                "account": account,
                "backend": backend,
                "model_name": model_name,
            })
            self._jobs[job_id] = current

    # 用途：
    # - 汇总当前 job 队列的在线状态，区分等待轮询和真实 backend 占用
    # 输入：
    # - 无；读取内存 job 表与 router concurrency
    # 输出：
    # - total/pending/running/done 计数；running 只表示真实 backend 占用
    def _job_summary(self) -> dict[str, int]:
        with self._lock:
            jobs = [dict(job) for job in self._jobs.values()]
        done = sum(1 for job in jobs if str(job.get("status") or "") == "done")
        direct_backend_counts, _direct_account_counts = self._active_job_runtime_counts()
        direct_running = sum(direct_backend_counts.values())
        running = self._router_running_count() + direct_running
        pending = max(0, len(jobs) - done - running)
        return {
            "total": len(jobs),
            "pending": pending,
            "running": running,
            "done": done,
        }

    # 用途：
    # - 计算仍会被 client 观察为 pending/running 的未完成在线 job 数
    # 输入：
    # - jobs: `_job_summary()` 返回值
    # 输出：
    # - pending + running；不包含历史 done job
    def _pending_job_count(self, jobs: dict[str, int]) -> int:
        return int(jobs.get("pending") or 0) + int(jobs.get("running") or 0)

    # Purpose: Stop probe timers and release the Tier HTTP listener.
    # Inputs: None.
    # Outputs: None after owned listener resources are closed.
    def stop(self) -> None:
        self._running = False
        if hasattr(self, "_exhausted_probe_timers"):
            with self._lock:
                timers = list(self._exhausted_probe_timers.values())
                self._exhausted_probe_timers.clear()
                self._exhausted_probe_due_epoch.clear()
            for timer in timers:
                timer.cancel()
        if self._http_server:
            http_server = self._http_server
            http_server.shutdown()
            http_server.server_close()
            self._http_server = None
        _log("stopped")

    # Purpose: Build the loopback Tier HTTP handler around this server's single business authority.
    # Inputs: None; captures this TierServer instance.
    # Outputs: BaseHTTPRequestHandler subclass.
    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "llm_tier/0.1"
            protocol_version = "HTTP/1.1"

            # Purpose: Initialize one HTTP connection with a bounded read/write timeout.
            # Inputs: Accepted client socket supplied by BaseHTTPRequestHandler.
            # Outputs: Initialized streams whose partial requests cannot hold a worker forever.
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(30.0)

            # Purpose: Serialize one Tier response with explicit status and no caching.
            # Inputs: JSON object and HTTP status.
            # Outputs: One complete HTTP response.
            def _send_json(self, data: dict[str, Any],
                           status: int = 200) -> None:
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:
                self._send_json({})

            # Purpose: Decode a bounded UTF-8 JSON object request body.
            # Inputs: Content-Length and request stream.
            # Outputs: JSON object or ValueError before any endpoint side effect.
            def _read_body(self) -> dict[str, Any]:
                try:
                    length = int(self.headers.get("Content-Length", 0))
                except ValueError as exc:
                    raise ValueError("Content-Length must be an integer") from exc
                if length < 0 or length > MAX_JSON_BODY_BYTES:
                    raise ValueError("JSON body exceeds configured limit")
                if length == 0:
                    return {}
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON body must be an object")
                return payload

            # Purpose: Suppress BaseHTTPRequestHandler access noise; Tier events use structured tracing.
            # Inputs: Standard access-log format and arguments.
            # Outputs: None.
            def log_message(self, fmt: str, *args: Any) -> None:
                return

            # ---- Routes ----

            # Purpose: Dispatch one Tier read request without serving Browser pages.
            # Inputs: Request path and query.
            # Outputs: One typed JSON response.
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    self._handle_health()
                elif parsed.path == "/runtime":
                    self._handle_runtime(parse_qs(parsed.query))
                elif parsed.path == "/recent-errors":
                    self._handle_recent_errors()
                elif parsed.path in ("/stats", "/llm-stats"):
                    params = parse_qs(parsed.query)
                    self._handle_stats(params)
                elif parsed.path == "/rag-stats":
                    params = parse_qs(parsed.query)
                    self._handle_rag_stats(params)
                elif parsed.path == "/runtime-summaries":
                    params = parse_qs(parsed.query)
                    self._handle_runtime_summaries(params)
                elif parsed.path == "/debug":
                    self._handle_debug()
                elif parsed.path == "/debug/trace":
                    params = parse_qs(parsed.query)
                    self._handle_debug_trace(params)
                elif parsed.path.startswith("/result/"):
                    job_id = parsed.path[len("/result/"):]
                    self._handle_result(job_id)
                else:
                    self._send_json({"ok": False, "error": "not_found"}, 404)

            # Purpose: Dispatch one Tier write request and surface malformed bodies as HTTP 400.
            # Inputs: Request path and bounded JSON body.
            # Outputs: One typed JSON response.
            def do_POST(self) -> None:
                try:
                    self._dispatch_post()
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    self._send_json({"ok": False, "error": "invalid_json_body", "message": str(exc)}, 400)

            # Purpose: Dispatch one validated Tier POST path to the existing authoritative handler.
            # Inputs: Current request path; body validation remains inside endpoint handlers.
            # Outputs: One endpoint response or a visible 404.
            def _dispatch_post(self) -> None:
                if self.path.startswith("/job/") and self.path.endswith("/cancel"):
                    job_id = self.path[len("/job/"):-len("/cancel")].strip("/")
                    self._handle_job_cancel(job_id)
                    return
                handlers = {
                    "/call": self._handle_call,
                    "/escalate": self._handle_escalate,
                    "/reset": self._handle_reset,
                    "/probe": self._handle_probe,
                    "/model-name": self._handle_model_name,
                    "/backend/weight": self._handle_backend_weight,
                    "/account/concurrency": self._handle_account_concurrency,
                    "/backend/enable": self._handle_backend_enable,
                    "/backend/disable": self._handle_backend_disable,
                    "/backend/probe": self._handle_backend_probe,
                    "/config/save": self._handle_save_config,
                    "/config/load": self._handle_load_config,
                    "/reload": self._handle_reload,
                    "/usage/reload": self._handle_usage_reload,
                    "/debug": self._handle_debug_update,
                }
                handler = handlers.get(self.path)
                if handler is None:
                    self._send_json({"ok": False, "error": "not_found"}, 404)
                    return
                handler()

            def _handle_health(self) -> None:
                tiers: dict[str, list[dict[str, Any]]] = {}
                active_backend_jobs, active_account_jobs = server_ref._active_job_runtime_counts()
                for tname in server_ref._config._config.get("llm_tiers", {}):
                    models = []
                    for m in server_ref._config.get_tier_models(tname):
                        account_key = str(m.account or "").strip()
                        backend_key = server_ref._backend_identity_key(tname, account_key, m.model_name)
                        admin_enabled = server_ref._router.is_backend_enabled(
                            m.backend,
                            m.model_name,
                            tier_name=tname,
                            account=account_key,
                        )
                        capabilities = server_ref._config.get_backend_capabilities(
                            m.backend,
                            model_name=m.model_name,
                            model_key=m.model_key,
                        )
                        probe_status = server_ref._backend_status_snapshot(tname, account_key, m.backend, m.model_name)
                        exhausted = (
                            str(probe_status.get("status") or "").strip().lower() == "exhausted"
                            or server_ref._router._quota.is_exhausted(m.backend, m.model_name)
                        )
                        runtime_status = str(probe_status.get("status") or "")
                        backend_running = server_ref._router._concurrency.get_load(backend_key) + active_backend_jobs.get(backend_key, 0)
                        state = server_ref._runtime_backend_state(
                            admin_enabled=admin_enabled,
                            running=backend_running,
                            exhausted=exhausted,
                            probe_status=runtime_status,
                        )
                        active = server_ref._active_backend(
                            admin_enabled=admin_enabled,
                            exhausted=exhausted,
                            probe_status=runtime_status,
                        )
                        models.append({
                            "backend": m.backend,
                            "provider": m.provider,
                            "account": account_key,
                            "model_name": m.model_name,
                            "model_key": m.model_key,
                            "provider_profile_models": server_ref._config.get_provider_profile_models(m.provider),
                            "backend_type": m.backend_type,
                            "max_context_tokens": int(capabilities.get("max_context_tokens") or 0),
                            "reserved_completion_tokens": int(capabilities.get("reserved_completion_tokens") or 0),
                            "max_output_tokens": int(capabilities.get("max_output_tokens") or 0),
                            "weight": float(m.weight or 1.0),
                            "exhausted": exhausted,
                            "admin_state": "enabled" if admin_enabled else "disabled",
                            "enabled": admin_enabled,
                            "active": active,
                            "probe_status": server_ref._normalize_backend_probe_state(
                                probe_status=runtime_status,
                                exhausted=exhausted,
                            ),
                            "state": state,
                            "probe_checked_at": probe_status.get("checked_at", ""),
                            "load": backend_running,
                            "running": backend_running,
                        })
                    tiers[tname] = models
                jobs = server_ref._job_summary()
                accounts = [
                    {
                        "account": account.account_id,
                        "provider": account.provider,
                        "running": (
                            server_ref._router._concurrency.get_account_load(account.account_id)
                            + active_account_jobs.get(account.account_id, 0)
                        ),
                        "max_concurrent_requests": server_ref._router._concurrency.get_account_limit(account.account_id),
                        "min_request_interval_ms": account.min_request_interval_ms,
                        "requests_per_minute": account.requests_per_minute,
                        "exhausted": server_ref._router._quota._exhausted.get(f"account:{account.account_id}", False),
                    }
                    for account in server_ref._config.get_accounts()
                ]
                self._send_json({
                    "ok": True,
                    "host": server_ref.host,
                    "port": server_ref.port,
                    "running": server_ref._running,
                    "jobs_pending": server_ref._pending_job_count(jobs),
                    "jobs": jobs,
                    "debug": server_ref._runtime_debug_snapshot(),
                    "tier_enabled": server_ref._config.is_enabled(),
                    "tiers": tiers,
                    "accounts": accounts,
                    "exhausted_backends": server_ref._router._quota.get_all_exhausted(),
                })

            # Purpose: Return stats only when the authoritative SQLite store is readable and writable.
            # Inputs: Optional HTTP query parameters.
            # Outputs: JSON stats response, or explicit 503 authority_store_error.
            def _handle_stats(self, params: dict[str, list[str]] | None = None) -> None:
                from stats.llm_stats import (
                    build_llm_stats_http_response,
                    llm_stats_query_from_http_params,
                )
                authority = server_ref._stats.authority_status()
                if not authority.get("ok"):
                    self._send_json(
                        {"ok": False, "error": "authority_store_error", "authority": authority},
                        status=503,
                    )
                    return
                query = llm_stats_query_from_http_params(params, default_limit=9999)
                try:
                    response = build_llm_stats_http_response(
                        collector=server_ref._stats,
                        query=query,
                        event_formatter=server_ref._stats_event_for_response,
                    )
                except Exception as exc:
                    server_ref._stats._record_read_failure(exc)
                    authority = server_ref._stats.authority_status()
                    self._send_json(
                        {"ok": False, "error": "authority_store_error", "authority": authority},
                        status=503,
                    )
                    return
                authority = server_ref._stats.authority_status()
                if not authority.get("ok"):
                    self._send_json(
                        {"ok": False, "error": "authority_store_error", "authority": authority},
                        status=503,
                    )
                    return
                response["authority"] = authority
                self._send_json(response)

            # 用途：
            # - 返回最近 LLM/backend 错误，供 tier.html 在首屏后异步加载
            # 输入：
            # - 无；读取 llm stats SQLite 中最近错误事件
            # 输出：
            # - `{ok, recent_errors}` JSON payload
            def _handle_recent_errors(self) -> None:
                self._send_json({
                    "ok": True,
                    "recent_errors": server_ref._runtime_recent_error_events(),
                })

            def _handle_rag_stats(self, params: dict[str, list[str]] | None = None) -> None:
                from stats.rag_stats import build_rag_grouped_stats, build_rag_task_stats

                resolved_params = params or {}
                workspace_root = _first_query_value(resolved_params, "workspace_root") or _first_query_value(
                    resolved_params,
                    "workspace",
                )
                project_name = _first_query_value(resolved_params, "project")
                task_id = _first_query_value(resolved_params, "task_id")
                started_at = _first_query_value(resolved_params, "started_at")
                group_by = _first_query_value(resolved_params, "group_by")
                if not workspace_root or not project_name or (not task_id and not group_by):
                    self._send_json({
                        "ok": False,
                        "error": "missing_required_params",
                        "required": ["workspace", "project", "task_id or group_by"],
                    }, status=400)
                    return
                if group_by:
                    self._send_json(
                        build_rag_grouped_stats(
                            workspace_root=workspace_root,
                            project_name=project_name,
                            group_by=group_by,
                            stage=_first_query_value(resolved_params, "stage"),
                            phase=_first_query_value(resolved_params, "phase"),
                            task_id_prefix=_first_query_value(resolved_params, "task_id_prefix"),
                            started_at=started_at,
                        )
                    )
                    return
                self._send_json(
                    build_rag_task_stats(
                        workspace_root=workspace_root,
                        project_name=project_name,
                        task_id=task_id,
                        started_at=started_at,
                    )
                )

            # 用途：
            # - 查询 runtime materialized summary 表，供 Dashboard 读取已完成 Stage / Phase / Task
            # 输入：
            # - params: workspace、level、stage、phase、task_id 查询参数
            # 输出：
            # - JSON summary payload 列表
            def _handle_runtime_summaries(self, params: dict[str, list[str]] | None = None) -> None:
                from framework.summary.runtime_summary import build_runtime_summary_http_response

                resolved_params = params or {}
                workspace_root = _resolve_workspace_root_for_api(
                    _first_query_value(resolved_params, "workspace_root")
                    or _first_query_value(resolved_params, "workspace")
                )
                level = _first_query_value(resolved_params, "level")
                if not workspace_root or not level:
                    self._send_json({
                        "ok": False,
                        "error": "missing_required_params",
                        "required": ["workspace", "level"],
                    }, status=400)
                    return
                payload = build_runtime_summary_http_response(
                    workspace_root=workspace_root,
                    level=level,
                    stage=_first_query_value(resolved_params, "stage"),
                    phase=_first_query_value(resolved_params, "phase"),
                    task_id=_first_query_value(resolved_params, "task_id"),
                )
                self._send_json(payload, 200 if payload.get("ok") else 400)

            # 用途：
            # - 返回当前 tier runtime snapshot，并可按显式参数强制刷新 provider usage 或跳过 stats
            # 输入：
            # - params: GET query 参数；refresh_usage=1/true/yes 时忽略 usage cache；include_stats=0 时跳过 SQLite stats
            # 输出：
            # - JSON runtime payload
            def _handle_runtime(self, params: dict[str, list[str]] | None = None) -> None:
                refresh_usage = _first_query_value(params or {}, "refresh_usage").lower() in {
                    "1",
                    "true",
                    "yes",
                }
                include_stats_value = _first_query_value(params or {}, "include_stats").lower()
                light_value = _first_query_value(params or {}, "light").lower()
                include_stats = include_stats_value not in {"0", "false", "no"} and light_value not in {"1", "true", "yes"}
                self._send_json(server_ref._build_runtime_snapshot(
                    force_usage_refresh=refresh_usage,
                    include_stats=include_stats,
                ))

            # 用途：
            # - 返回当前 runtime debug trace 配置
            # 输入：
            # - 无；读取 server 内存态 debug state
            # 输出：
            # - JSON debug snapshot
            def _handle_debug(self) -> None:
                self._send_json({"ok": True, "debug": server_ref._runtime_debug_snapshot()})

            # 用途：
            # - 返回 trace JSONL 文件尾部事件
            # 输入：
            # - params: URL query 参数，支持 tail
            # 输出：
            # - JSON trace tail payload
            def _handle_debug_trace(self, params: dict[str, list[str]] | None = None) -> None:
                limit = 100
                if params and "tail" in params:
                    try:
                        limit = int(params["tail"][0])
                    except ValueError:
                        limit = 100
                self._send_json(server_ref._read_trace_tail(limit))

            # 用途：
            # - 根据外部 POST payload 更新 runtime debug trace 配置
            # 输入：
            # - HTTP JSON body
            # 输出：
            # - 更新后的 JSON debug snapshot
            def _handle_debug_update(self) -> None:
                result = server_ref._update_runtime_debug(self._read_body())
                self._send_json(result, 200 if result.get("ok") else 400)

            # 用途：
            # - 返回异步 job 当前状态或完成结果，并在 debug trace 中记录 poll 状态
            # 输入：
            # - job_id: /result/{job_id} 中的 job 标识
            # 输出：
            # - running/done/not_found JSON payload
            def _handle_result(self, job_id: str) -> None:
                with server_ref._lock:
                    job = server_ref._jobs.get(job_id)
                if job is None:
                    server_ref._trace("poll", "debug", "poll.result", {"job_id": job_id, "status": "not_found"})
                    self._send_json({"ok": False, "error": "job_not_found"}, 404)
                    return
                job_status = str(job.get("status") or "")
                if job_status != "done":
                    server_ref._trace(
                        "poll",
                        "debug",
                        "poll.result",
                        {
                            "job_id": job_id,
                            "client_request_id": str(job.get("client_request_id") or ""),
                            "status": job_status,
                        },
                    )
                    self._send_json({"ok": True, "status": "running", "job_status": job_status})
                    return
                result = job.get("result") or {}
                server_ref._trace(
                    "poll",
                    "debug",
                    "poll.result",
                    {
                        "job_id": job_id,
                        "client_request_id": str(job.get("client_request_id") or ""),
                        "status": "done",
                        "ok": bool(result.get("ok")),
                        "backend": str(result.get("backend") or ""),
                        "model_name": str(result.get("model_name") or ""),
                        "error_code": int(result.get("error_code") or 0),
                    },
                )
                self._send_json({
                    "ok": True,
                    "status": "done",
                    "result": result,
                })

            def _handle_call(self) -> None:
                data = self._read_body()
                role_name = data.get("role_name")
                prompt = data.get("prompt")
                prompt_path = data.get("prompt_path")
                if not isinstance(role_name, str) or not role_name.strip():
                    self._send_json(
                        {"ok": False, "error": "invalid_request", "field": "role_name"},
                        400,
                    )
                    return
                if prompt is None and prompt_path is None:
                    self._send_json(
                        {"ok": False, "error": "invalid_request", "field": "prompt"},
                        400,
                    )
                    return
                if prompt is not None and not isinstance(prompt, str):
                    self._send_json(
                        {"ok": False, "error": "invalid_request", "field": "prompt"},
                        400,
                    )
                    return
                if prompt_path is not None and not isinstance(prompt_path, str):
                    self._send_json(
                        {"ok": False, "error": "invalid_request", "field": "prompt_path"},
                        400,
                    )
                    return
                try:
                    job_id = server_ref._submit_job(data)
                except OverflowError:
                    self._send_json({"ok": False, "error": "queue_full"}, 429)
                    return
                self._send_json({"ok": True, "job_id": job_id})

            # Purpose: Cancel one accepted Tier job through its authoritative in-memory state.
            # Inputs: Job identifier encoded in the request path.
            # Outputs: Typed cancelled, already-terminal, or not-found response.
            def _handle_job_cancel(self, job_id: str) -> None:
                self._read_body()
                result = server_ref._cancel_job(job_id)
                error = str(result.get("error") or "")
                status = 404 if error == "job_not_found" else 200
                self._send_json(result, status)

            def _handle_escalate(self) -> None:
                data = self._read_body()
                if "prompt" not in data:
                    self._send_json(
                        {"ok": False, "error": "missing prompt"},
                        400,
                    )
                    return
                job_id = server_ref._submit_escalate_job(data)
                self._send_json({"ok": True, "job_id": job_id})

            def _handle_reset(self) -> None:
                data = self._read_body()
                tn = str(data.get("tier_name") or "").strip()
                reset_keys = server_ref._reset_exhausted_runtime_state(tn)
                self._send_json({
                    "ok": True,
                    "probe_started": False,
                    "reset_runtime_backends": reset_keys,
                })

            def _handle_probe(self) -> None:
                started = server_ref._start_backend_probe()
                self._send_json({"ok": True, "probe_started": started})

            def _handle_model_name(self) -> None:
                data = self._read_body()
                result = server_ref._update_runtime_model_name(
                    tier_name=str(data.get("tier_name") or ""),
                    account=str(data.get("account") or ""),
                    backend=str(data.get("backend") or ""),
                    old_model_name=str(data.get("old_model_name") or ""),
                    new_model_name=str(data.get("model_name") or data.get("new_model_name") or ""),
                    new_model_key=str(data.get("model_key") or data.get("new_model_key") or ""),
                )
                self._send_json(result, 200 if result.get("ok") else 400)

            # Purpose: Validate and update one Backend weight with traceable typed failure evidence.
            # Inputs: Tier, account, Backend, model, and weight from a bounded JSON object.
            # Outputs: Update result; failed validation includes a request id and no sensitive input echo.
            def _handle_backend_weight(self) -> None:
                data = self._read_body()
                result = server_ref._update_backend_weight(
                    tier_name=str(data.get("tier_name") or data.get("tier") or ""),
                    account=str(data.get("account") or ""),
                    backend=str(data.get("backend") or ""),
                    model_name=str(data.get("model_name") or ""),
                    weight=data.get("weight", 1.0),
                )
                if not result.get("ok"):
                    result = dict(result)
                    result.setdefault("request_id", uuid.uuid4().hex)
                self._send_json(result, 200 if result.get("ok") else 400)

            def _handle_account_concurrency(self) -> None:
                data = self._read_body()
                result = server_ref._update_account_concurrency(
                    account=str(data.get("account") or data.get("account_id") or ""),
                    max_concurrent_requests=data.get("max_concurrent_requests", 1),
                )
                self._send_json(result, 200 if result.get("ok") else 400)

            def _handle_backend_enable(self) -> None:
                data = self._read_body()
                result = server_ref._update_backend_enabled(
                    tier_name=str(data.get("tier_name") or data.get("tier") or ""),
                    account=str(data.get("account") or ""),
                    backend=str(data.get("backend") or ""),
                    model_name=str(data.get("model_name") or ""),
                    enabled=True,
                )
                self._send_json(result, 200 if result.get("ok") else 400)

            def _handle_backend_disable(self) -> None:
                data = self._read_body()
                result = server_ref._update_backend_enabled(
                    tier_name=str(data.get("tier_name") or data.get("tier") or ""),
                    account=str(data.get("account") or ""),
                    backend=str(data.get("backend") or ""),
                    model_name=str(data.get("model_name") or ""),
                    enabled=False,
                )
                self._send_json(result, 200 if result.get("ok") else 400)

            def _handle_backend_probe(self) -> None:
                data = self._read_body()
                result = server_ref._probe_single_backend(
                    tier_name=str(data.get("tier_name") or data.get("tier") or ""),
                    account=str(data.get("account") or ""),
                    backend=str(data.get("backend") or ""),
                    model_name=str(data.get("model_name") or ""),
                )
                self._send_json(result, 200 if result.get("ok") else 400)

            # Purpose: Persist the current runtime config only for the declared empty-object request Contract.
            # Inputs: Bounded JSON object body; any field is an unsupported config payload.
            # Outputs: Save result, or sanitized HTTP 400 with a request id before any persistence side effect.
            def _handle_save_config(self) -> None:
                data = self._read_body()
                if data:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "invalid_request_body",
                            "message": "/config/save accepts only an empty JSON object",
                            "request_id": uuid.uuid4().hex,
                        },
                        400,
                    )
                    return
                result = server_ref._save_runtime_config()
                self._send_json(result, 200 if result.get("ok") else 400)

            def _handle_load_config(self) -> None:
                result = server_ref._load_runtime_config()
                self._send_json(result, 200 if result.get("ok") else 400)

            def _handle_reload(self) -> None:
                result = server_ref._load_runtime_config()
                if result.get("ok"):
                    _log("config reloaded")
                self._send_json(result, 200 if result.get("ok") else 400)

            # 用途：
            # - 重新读取 provider usage cookie/key 文件并刷新 runtime usage，不重建 router
            # 输入：
            # - 无；使用当前配置中的 usage_cookie_file 等凭据文件
            # 输出：
            # - 刷新后的 runtime snapshot
            def _handle_usage_reload(self) -> None:
                result = server_ref._reload_provider_usage()
                if result.get("ok"):
                    _log("provider usage reloaded")
                self._send_json(result, 200 if result.get("ok") else 400)

        return Handler

    # =========================================================================
    # Job 管理
    # =========================================================================

    # Purpose: Atomically accept or deduplicate one bounded Tier call job.
    # Inputs: Validated /call JSON payload.
    # Outputs: New or existing job ID; raises OverflowError when the live queue is full.
    def _submit_job(self, data: dict[str, Any]) -> str:
        client_request_id = str((data.get("metadata") if isinstance(data.get("metadata"), dict) else {}).get("client_request_id") or "")
        config_payload = json.dumps(self._config._config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        config_snapshot_id = hashlib.sha256(config_payload.encode("utf-8")).hexdigest()
        with self._lock:
            if client_request_id:
                for existing_job_id, existing_job in self._jobs.items():
                    if str(existing_job.get("client_request_id") or "") == client_request_id:
                        return existing_job_id
            live_jobs = sum(1 for job in self._jobs.values() if str(job.get("status") or "") != "done")
            tier_settings = self._config._config.get("llm_tier")
            max_pending_jobs = int(tier_settings.get("max_pending_jobs") or 0) if isinstance(tier_settings, dict) else 0
            if max_pending_jobs > 0 and live_jobs >= max_pending_jobs:
                raise OverflowError("queue_full")
            job_id = str(uuid.uuid4())[:12]
            self._jobs[job_id] = {
                "status": "pending",
                "result": None,
                "client_request_id": client_request_id,
                "config_snapshot_id": config_snapshot_id,
            }
        self._trace(
            "job",
            "info",
            "job.submitted",
            {
                "job_id": job_id,
                "client_request_id": client_request_id,
                "role_name": str(data.get("role_name") or ""),
                "project_name": str(data.get("project_name") or "default"),
                "stage_name": str(data.get("stage_name") or ""),
                "phase_name": str(data.get("phase_name") or ""),
                "task_id": str(data.get("task_id") or ""),
                "task_key": str(data.get("task_key") or ""),
                "prompt_chars": len(str(data.get("prompt") or "")),
                "prompt_path": str(data.get("prompt_path") or ""),
            },
        )
        t = threading.Thread(target=self._run_job,
                             args=(job_id, data), daemon=True)
        t.start()
        return job_id

    # Purpose: Commit cancellation as a terminal Tier job state without deleting audit history.
    # Inputs: Existing job ID.
    # Outputs: Typed cancellation result or a not-found response.
    def _cancel_job(self, job_id: str) -> dict[str, Any]:
        normalized_job_id = str(job_id or "").strip()
        with self._lock:
            current = dict(self._jobs.get(normalized_job_id) or {})
            if not current:
                return {"ok": False, "error": "job_not_found"}
            if str(current.get("status") or "") == "done":
                result = dict(current.get("result") or {})
                return {"ok": True, "status": "cancelled" if result.get("error_message") == "cancelled" else "done"}
            cancelled_result = {
                "ok": False,
                "content": "",
                "backend": "",
                "account": "",
                "model_name": "",
                "backend_type": "",
                "tier": "",
                "tier_priority": 0,
                "latency_ms": 0,
                "token_usage": {},
                "is_fallback": False,
                "fallback_count": 0,
                "raw_response": {},
                "error_code": 1008,
                "error_message": "cancelled",
                "artifact_paths": {},
            }
            current.update({"status": "done", "result": cancelled_result, "cancel_requested": True})
            self._jobs[normalized_job_id] = current
        return {"ok": True, "status": "cancelled", "job_id": normalized_job_id}

    # 用途：
    # - 执行普通 LLM 调用 job，解析 file/content 模式 prompt，调用 router，写 stats 和 file 模式 artifacts
    # 输入：
    # - job_id/data: 当前 job 标识和 /call JSON payload
    # 输出：
    # - 无；最终结果写回 `_jobs[job_id]`
    def _run_job(self, job_id: str, data: dict[str, Any]) -> None:
        client_request_id = str((data.get("metadata") if isinstance(data.get("metadata"), dict) else {}).get("client_request_id") or "")
        self._mark_job_pending(job_id, client_request_id=client_request_id)
        job_started_at = time.time()
        self._trace("job", "info", "job.running", {"job_id": job_id, "client_request_id": client_request_id})

        try:
            req = TierCallRequest(
                role_name=str(data.get("role_name", "")),
                prompt=_resolve_request_prompt(str(data.get("prompt", "")), str(data.get("prompt_path", ""))),
                project_name=str(data.get("project_name", "default")),
                stage_name=str(data.get("stage_name", "")),
                phase_name=str(data.get("phase_name", "")),
                task_id=str(data.get("task_id", "")),
                task_key=str(data.get("task_key", "")),
                temperature=float(data.get("temperature", 0.0)),
                timeout_seconds=data.get("timeout_seconds"),
                metadata=dict(data.get("metadata") or {}) if isinstance(data.get("metadata"), dict) else {},
                prompt_path=str(data.get("prompt_path", "")),
                response_path=str(data.get("response_path", "")),
                raw_response_path=str(data.get("raw_response_path", "")),
                error_response_path=str(data.get("error_response_path", "")),
            )
            request_metadata = dict(req.metadata or {})
            self._trace(
                "job",
                "debug",
                "job.prompt.loaded",
                {
                    "job_id": job_id,
                    "client_request_id": str(request_metadata.get("client_request_id") or ""),
                    "role_name": req.role_name,
                    "project_name": req.project_name,
                    "stage_name": req.stage_name,
                    "phase_name": req.phase_name,
                    "task_id": req.task_id,
                    "task_key": req.task_key,
                    "prompt_chars": len(str(req.prompt or "")),
                    "prompt_path": req.prompt_path,
                    "response_path": req.response_path,
                    "raw_response_path": req.raw_response_path,
                    "error_response_path": req.error_response_path,
                },
            )

            self._trace(
                "job",
                "debug",
                "router.call.start",
                {
                    "job_id": job_id,
                    "client_request_id": str(request_metadata.get("client_request_id") or ""),
                    "role_name": req.role_name,
                    "project_name": req.project_name,
                    "stage_name": req.stage_name,
                    "phase_name": req.phase_name,
                    "task_id": req.task_id,
                    "task_key": req.task_key,
                    "prompt_chars": len(str(req.prompt or "")),
                },
            )
            result, stats_event = self._router_call_with_busy_retry(
                req=req,
                job_id=job_id,
                request_metadata=request_metadata,
            )
            if not isinstance(result, TierCallResult) or not isinstance(stats_event, dict):
                raise TypeError("invalid malformed router result")
            result.error_message = redact_sensitive_text(result.error_message)
            result.raw_response = redact_sensitive_value(result.raw_response)
            self._trace(
                "job",
                "debug",
                "router.call.finish",
                {
                    "job_id": job_id,
                    "client_request_id": client_request_id,
                    "ok": result.ok,
                    "backend": result.backend,
                    "account": result.account,
                    "model_name": result.model_name,
                    "tier": result.tier,
                    "latency_ms": result.latency_ms,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                },
            )

            try:
                self._write_call_stats_event(self._stats_event_for_request(stats_event, req, result, job_id=job_id))
            except Exception as stats_exc:
                self._trace(
                    "stats",
                    "error",
                    "stats.call.write_failed",
                    {
                        "job_id": job_id,
                        "client_request_id": client_request_id,
                        "error_type": type(stats_exc).__name__,
                        "error_message": redact_sensitive_text(stats_exc),
                        "business_result_ok": bool(result.ok),
                    },
                )
            public_artifact_paths, raw_response_written = _write_tier_call_artifacts(req, result)
            result.artifact_paths.update(public_artifact_paths)
            if result.artifact_paths:
                self._trace(
                    "job",
                    "debug",
                    "job.artifacts_written",
                    {"job_id": job_id, "artifact_paths": dict(result.artifact_paths)},
                )
            if result.backend and result.model_name:
                backend_error_message = str(result.error_message or "").strip()
                status_tier = str(result.tier or "").strip()
                status_model = next(
                    (
                        model for model in self._config.get_tier_models(status_tier)
                        if model.backend == result.backend and model.model_name == result.model_name
                    ),
                    None,
                )
                status_account = str(result.account or (status_model.account if status_model is not None else "")).strip()
                if result.ok:
                    self._set_backend_status(status_tier, status_account, result.backend, result.model_name, "running")
                    self._sync_backend_meta_from_router(status_tier, status_account, result.backend, result.model_name)
                elif QuotaManager.is_quota_error(backend_error_message):
                    self._set_backend_status(status_tier, status_account, result.backend, result.model_name, "exhausted")
                    self._update_backend_state_meta(
                        status_tier,
                        status_account,
                        result.backend,
                        result.model_name,
                        last_error=backend_error_message,
                        last_error_type="quota",
                        last_error_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    )
                else:
                    self._sync_backend_meta_from_router(status_tier, status_account, result.backend, result.model_name)
                    status_snapshot = self._backend_status_snapshot(status_tier, status_account, result.backend, result.model_name)
                    self._update_backend_state_meta(
                        status_tier,
                        status_account,
                        result.backend,
                        result.model_name,
                        last_error=backend_error_message or str(status_snapshot.get("last_error") or ""),
                        last_error_type=(
                            "call_failed"
                            if backend_error_message and not str(status_snapshot.get("last_error_type") or "").strip()
                            else str(status_snapshot.get("last_error_type") or "")
                        ),
                        last_error_at=(
                            datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                            if backend_error_message and not str(status_snapshot.get("last_error_at") or "").strip()
                            else str(status_snapshot.get("last_error_at") or "")
                        ),
                    )

            job_result = {
                "ok": result.ok,
                "content": "" if result.artifact_paths.get("response_path") else result.content,
                "backend": result.backend,
                "account": result.account,
                "model_name": result.model_name,
                "backend_type": result.backend_type,
                "tier": result.tier,
                "tier_priority": result.tier_priority,
                "latency_ms": result.latency_ms,
                "token_usage": result.token_usage,
                "is_fallback": result.is_fallback,
                "fallback_count": result.fallback_count,
                "raw_response": {} if raw_response_written else result.raw_response,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "artifact_paths": result.artifact_paths,
            }

        except Exception as exc:
            safe_exception_message = redact_sensitive_text(exc)
            self._trace("error", "error", "job.error", {"job_id": job_id, "client_request_id": client_request_id, "error_message": safe_exception_message})
            fallback_error_path = str(data.get("error_response_path") or "").strip()
            if not fallback_error_path:
                response_path = str(data.get("response_path") or "").strip()
                if response_path:
                    path = Path(response_path)
                    fallback_error_path = str(path.with_suffix(".error.json")) if path.suffix else f"{response_path}.error.json"
            artifact_paths: dict[str, str] = {}
            written_error_path = _write_tier_text_file(
                fallback_error_path,
                json.dumps(
                    {
                        "success": False,
                        "error_type": "tier_server_error",
                        "error_code": 1999,
                        "message": safe_exception_message,
                        "backend": "",
                        "model_name": "",
                        "tier": "",
                        "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "raw_response": {},
                        "debug_paths": {
                            "prompt_path": str(data.get("prompt_path") or ""),
                            "response_path": str(data.get("response_path") or ""),
                            "raw_response_path": str(data.get("raw_response_path") or ""),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
            )
            if written_error_path:
                artifact_paths["error_response_path"] = written_error_path
            job_result = {
                "ok": False,
                "content": "",
                "backend": "",
                "account": "",
                "model_name": "",
                "backend_type": "",
                "tier": "",
                "tier_priority": 0,
                "latency_ms": 0,
                "token_usage": {},
                "is_fallback": False,
                "fallback_count": 0,
                "raw_response": {},
                "error_code": 1999,
                "error_message": safe_exception_message,
                "artifact_paths": artifact_paths,
            }

        with self._lock:
            current_job = dict(self._jobs.get(job_id) or {})
            if bool(current_job.get("cancel_requested")):
                return
            current_job.update({"status": "done", "result": job_result, "client_request_id": client_request_id})
            self._jobs[job_id] = current_job
        self._trace(
            "job",
            "info",
            "job.done",
            {
                "job_id": job_id,
                "client_request_id": client_request_id,
                "ok": bool(job_result.get("ok")),
                "elapsed_ms": (time.time() - job_started_at) * 1000,
                "backend": str(job_result.get("backend") or ""),
                "model_name": str(job_result.get("model_name") or ""),
                "error_code": int(job_result.get("error_code") or 0),
                "error_message": str(job_result.get("error_message") or ""),
            },
        )

    # =========================================================================
    # Escalation Job 管理（跨 tier 扫荡）
    # =========================================================================

    # 用途：
    # - 提交跨 tier escalation job，并在后台线程异步执行
    # 输入：
    # - data: /escalate JSON payload
    # 输出：
    # - job_id，供 client 轮询 /result/{job_id}
    def _submit_escalate_job(self, data: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())[:12]
        with self._lock:
            self._jobs[job_id] = {"status": "pending", "result": None}
        self._trace("escalation", "info", "escalation.submitted", {"job_id": job_id, "prompt_chars": len(str(data.get("prompt") or ""))})
        t = threading.Thread(target=self._run_escalate_job,
                             args=(job_id, data), daemon=True)
        t.start()
        return job_id

    # 用途：
    # - 按 tier_priority 逐个 backend 执行 escalation 调用，直到成功或全部失败
    # 输入：
    # - job_id/data: escalation job 标识和请求 payload
    # 输出：
    # - 无；最终结果与 fallback_trace 写回 `_jobs[job_id]`
    def _run_escalate_job(self, job_id: str, data: dict[str, Any]) -> None:
        self._mark_job_pending(job_id)
        self._trace("escalation", "info", "escalation.running", {"job_id": job_id})

        prompt = str(data.get("prompt", ""))
        project_name = str(data.get("project_name", "default"))
        tier_priority = list(data.get("tier_priority", ["Senior", "Junior", "Worker", "Associate", "Engineer", "Executor"]))
        temperature = float(data.get("temperature", 0.1))
        stage_name = str(data.get("stage_name") or "").strip()
        phase_name = str(data.get("phase_name") or "").strip()
        task_id = str(data.get("task_id") or "").strip()
        task_key = str(data.get("task_key") or "").strip()

        fallback_trace: list[dict[str, Any]] = []
        last_error = ""
        result: TierCallResult | None = None

        try:
            for tier_name in tier_priority:
                models = self._config.get_tier_models(tier_name)
                for model in models:
                    self._mark_job_pending(job_id)
                    if self._router._quota.is_exhausted(model.backend, model.model_name):
                        fallback_trace.append({
                            "tier": tier_name, "backend": model.backend,
                            "model": model.model_name, "status": "unavailable",
                        })
                        continue

                    try:
                        from llm_tier.backends import get_backend_client
                        creds = self._get_cred(
                            model.backend,
                            model.provider,
                            model.model_name,
                            model.model_key,
                            model.account,
                        )
                        client_name = backend_client_name(model)
                        client = get_backend_client(client_name, **creds)
                        if client is None:
                            fallback_trace.append({
                                "tier": tier_name, "backend": model.backend,
                                "model": model.model_name, "status": "no_client",
                            })
                            continue

                        start_ts = time.time()
                        self._mark_job_running_backend(
                            job_id,
                            tier_name=tier_name,
                            account=str(model.account or "").strip(),
                            backend=model.backend,
                            model_name=model.model_name,
                        )
                        self._trace(
                            "backend",
                            "info",
                            "backend.call.start",
                            {
                                "job_id": job_id,
                                "tier": tier_name,
                                "backend": model.backend,
                                "model_name": model.model_name,
                                "model_key": model.model_key,
                                "prompt_chars": len(prompt),
                                "timeout_seconds": int(model.timeout_seconds or 600),
                            },
                        )
                        call_result = client.call(
                            model_name=backend_call_model_name(model),
                            prompt=prompt,
                            temperature=temperature,
                            timeout_seconds=model.timeout_seconds or 600,
                            metadata={"project_name": project_name},
                        )
                        latency_ms = (time.time() - start_ts) * 1000
                        self._trace(
                            "backend",
                            "info",
                            "backend.call.finish",
                            {
                                "job_id": job_id,
                                "tier": tier_name,
                                "backend": model.backend,
                                "model_name": model.model_name,
                                "ok": True,
                                "latency_ms": latency_ms,
                            },
                        )

                        fallback_trace.append({
                            "tier": tier_name, "backend": model.backend,
                            "model": model.model_name, "status": "success",
                            "latency_ms": latency_ms,
                        })

                        result = TierCallResult(
                            ok=True,
                            content=call_result.get("content", ""),
                            backend=model.backend,
                            model_name=model.model_name,
                            backend_type=model.backend_type,
                            tier=tier_name,
                            tier_priority=0,
                            latency_ms=latency_ms,
                            token_usage=call_result.get("token_usage", {}),
                            account=model.account,
                        )

                        stats_event = {
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "tier": tier_name, "backend": model.backend,
                            "account": model.account,
                            "backend_type": model.backend_type,
                            "model": model.model_name, "ok": True,
                            "latency_ms": latency_ms,
                            "prompt_tokens": result.token_usage.get("prompt_tokens", 0),
                            "completion_tokens": result.token_usage.get("completion_tokens", 0),
                            "total_tokens": result.token_usage.get("total_tokens", 0),
                            "is_fallback": len(fallback_trace) > 1,
                            "fallback_count": len(fallback_trace) - 1,
                        }
                        stats_event.update({
                            "project": project_name,
                            "stage_name": stage_name,
                            "phase_name": phase_name,
                            "task_id": task_id,
                            "task_key": task_key,
                            "role": "escalation",
                            "prompt_name": "",
                            "prompt_kind": "escalation",
                            "prompt_chars": len(prompt),
                            "completion_chars": len(str(result.content or "")),
                        })
                        self._stats.write(stats_event)
                        break

                    except QuotaExhaustedError:
                        self._mark_job_pending(job_id)
                        fallback_trace.append({
                            "tier": tier_name, "backend": model.backend,
                            "model": model.model_name, "status": "unavailable",
                        })
                        continue
                    except BackendCallError as e:
                        self._mark_job_pending(job_id)
                        self._trace(
                            "backend",
                            "warn",
                            "backend.call.error",
                            {
                                "job_id": job_id,
                                "tier": tier_name,
                                "backend": model.backend,
                                "model_name": model.model_name,
                                "error_type": "backend",
                                "error_message": str(e),
                            },
                        )
                        fallback_trace.append({
                            "tier": tier_name, "backend": model.backend,
                            "model": model.model_name, "status": "error",
                            "error": str(e),
                        })
                        last_error = str(e)
                        continue
                    except Exception as e:
                        self._mark_job_pending(job_id)
                        self._trace(
                            "backend",
                            "error",
                            "backend.call.error",
                            {
                                "job_id": job_id,
                                "tier": tier_name,
                                "backend": model.backend,
                                "model_name": model.model_name,
                                "error_type": "unexpected",
                                "error_message": str(e),
                            },
                        )
                        fallback_trace.append({
                            "tier": tier_name, "backend": model.backend,
                            "model": model.model_name, "status": "error",
                            "error": str(e),
                        })
                        last_error = str(e)
                        continue

                if result is not None:
                    break

            if result is None:
                result = TierCallResult(
                    ok=False, content="", backend="", model_name="",
                    backend_type="", tier="", tier_priority=0,
                    latency_ms=0, token_usage={},
                    error_code=1005,
                    error_message=last_error or "all_tiers_unavailable",
                )

        except Exception as exc:
            result = TierCallResult(
                ok=False, content="", backend="", model_name="",
                backend_type="", tier="", tier_priority=0,
                latency_ms=0, token_usage={},
                error_code=1999, error_message=str(exc),
            )

        job_result = {
            "ok": result.ok,
            "content": result.content,
            "backend": result.backend,
            "account": result.account,
            "model_name": result.model_name,
            "backend_type": result.backend_type,
            "tier": result.tier,
            "tier_priority": result.tier_priority,
            "latency_ms": result.latency_ms,
            "token_usage": result.token_usage,
            "is_fallback": result.is_fallback,
            "fallback_count": result.fallback_count,
            "raw_response": result.raw_response,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "falback_trace": fallback_trace,
        }

        with self._lock:
            self._jobs[job_id] = {"status": "done", "result": job_result}
        self._trace(
            "escalation",
            "info",
            "escalation.done",
            {
                "job_id": job_id,
                "ok": bool(job_result.get("ok")),
                "backend": str(job_result.get("backend") or ""),
                "model_name": str(job_result.get("model_name") or ""),
                "error_code": int(job_result.get("error_code") or 0),
            },
        )

    def _get_cred(
        self,
        backend: str,
        provider: str,
        model_name: str = "",
        model_key: str = "",
        account: str = "",
    ) -> dict[str, Any]:
        return self._config.get_backend_credentials(
            backend,
            provider=provider,
            model_name=model_name,
            model_key=model_key,
            account=account,
        )

    # =========================================================================
    # 内嵌模式便捷方法
    # =========================================================================

    def call(self, req: TierCallRequest) -> TierCallResult:
        result, stats_event = self._router.call(
            role_name=req.role_name,
            prompt=req.prompt,
            temperature=req.temperature,
            timeout_seconds=req.timeout_seconds,
            metadata={
                "stage_name": req.stage_name,
                "phase_name": req.phase_name,
                "task_id": req.task_id,
                "task_key": req.task_key,
                "project_name": req.project_name,
                **req.metadata,
            },
        )
        self._write_call_stats_event(self._stats_event_for_request(stats_event, req, result))
        return result

    def get_stats(self, query: TierStatsQuery | None = None) -> list[dict[str, Any]]:
        rows = self._stats.get_stats(query or TierStatsQuery())
        return [r.__dict__ for r in rows]

    def get_summary(self) -> dict[str, Any]:
        return self._stats.get_summary()

    # 用途：
    # - embedded 调用方重置 quota exhausted 与 runtime backend 状态
    # 输入：
    # - tier_name: 可选 Tier 名称；为空时重置全部 Tier
    # 输出：
    # - 无；重置后 backend 可重新参与 router 选择
    def reset_exhausted(self, tier_name: str = "") -> None:
        self._reset_exhausted_runtime_state(tier_name)

    # 用途：
    # - 在不重启 embedded TierServer 调用方的情况下重新读取配置并重建 router
    # 输入：
    # - 无；读取当前 TierConfig 的 settings_path
    # 输出：
    # - reload 是否成功
    def reload_config(self) -> bool:
        ok = self._config.reload()
        if ok:
            self._router = LLMRouter(self._config, state_dir=self._stats_dir, trace_hook=self._trace)
            self._load_runtime_config_state()
            self._start_backend_probe()
        return ok
