from __future__ import annotations

from collections import defaultdict, deque
import threading
import time
from typing import Any


# 用途：
# - 按 backend identity 记录运行数，并按 account identity 控制最大并发、调用间隔和每分钟请求数
# 输入：
# - account_config: `account_key -> concurrency config` 映射
# 输出：
# - acquire/release/get_load/get_account_load 可查询的线程安全计数器
class BackendConcurrencyManager:
    # 用途：
    # - 初始化 account 并发配置与 backend/account 计数器
    # 输入：
    # - account_config: `account_key -> max_concurrent_requests/min_request_interval_ms/requests_per_minute` 等配置
    # 输出：
    # - 无；构建可复用并发管理器
    def __init__(self, account_config: dict[str, dict[str, Any]] | None = None) -> None:
        self._account_config: dict[str, dict[str, Any]] = account_config or {}
        self._backend_counters: dict[str, int] = defaultdict(int)
        self._account_counters: dict[str, int] = defaultdict(int)
        self._account_next_available_at: dict[str, float] = defaultdict(float)
        self._account_request_starts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    # 用途：
    # - 尝试占用一个 backend identity 的运行计数和一个 account identity 的并发槽位
    # 输入：
    # - backend_key/account_key: runtime backend identity 和账号 identity
    # 输出：
    # - (True, "") 表示占用成功；False 时返回 busy 原因
    def acquire(self, backend_key: str, account_key: str) -> tuple[bool, str]:
        normalized_account = str(account_key or "").strip()
        with self._lock:
            cfg = self._account_config.get(normalized_account, {})
            max_conc = int(cfg.get("max_concurrent_requests", 1))
            current = self._account_counters.get(normalized_account, 0)
            if current >= max_conc:
                return False, "account_concurrency_full"
            now = time.time()
            next_available_at = float(self._account_next_available_at.get(normalized_account) or 0.0)
            if now < next_available_at:
                return False, "account_interval_wait"
            requests_per_minute = max(0, int(cfg.get("requests_per_minute") or 0))
            starts = self._account_request_starts[normalized_account]
            while starts and now - starts[0] >= 60.0:
                starts.popleft()
            if requests_per_minute > 0 and len(starts) >= requests_per_minute:
                return False, "account_rate_limit_wait"
            interval_ms = max(0, int(cfg.get("min_request_interval_ms") or 0))
            self._backend_counters[backend_key] = self._backend_counters.get(backend_key, 0) + 1
            self._account_counters[normalized_account] = current + 1
            starts.append(now)
            if interval_ms > 0:
                self._account_next_available_at[normalized_account] = now + (interval_ms / 1000.0)
            return True, ""

    # 用途：
    # - 释放一个 backend identity 的运行计数和一个 account identity 的并发槽位
    # 输入：
    # - backend_key/account_key: runtime backend identity 和账号 identity
    # 输出：
    # - 无；计数不会降到 0 以下
    def release(self, backend_key: str, account_key: str) -> None:
        normalized_account = str(account_key or "").strip()
        with self._lock:
            current = self._backend_counters.get(backend_key, 0)
            if current > 0:
                self._backend_counters[backend_key] = current - 1
            account_current = self._account_counters.get(normalized_account, 0)
            if account_current > 0:
                self._account_counters[normalized_account] = account_current - 1

    # 用途：
    # - 查询 backend identity 当前运行中的请求数
    # 输入：
    # - backend_key: runtime backend identity
    # 输出：
    # - 当前并发计数
    def get_load(self, backend_key: str) -> int:
        with self._lock:
            return self._backend_counters.get(backend_key, 0)

    # 用途：
    # - 查询 account identity 当前运行中的请求数
    # 输入：
    # - account_key: account identity
    # 输出：
    # - 当前 account 并发计数
    def get_account_load(self, account_key: str) -> int:
        normalized_account = str(account_key or "").strip()
        with self._lock:
            return self._account_counters.get(normalized_account, 0)

    # 用途：
    # - 查询 account identity 的最大并发数
    # 输入：
    # - account_key: account identity
    # 输出：
    # - 当前 account 并发上限
    def get_account_limit(self, account_key: str) -> int:
        normalized_account = str(account_key or "").strip()
        with self._lock:
            cfg = self._account_config.get(normalized_account, {})
            return max(1, int(cfg.get("max_concurrent_requests") or 1))

    # 用途：
    # - 计算 account 因调用间隔或每分钟限流需要等待多久后再重试
    # 输入：
    # - account_key/fallback_seconds: account identity 和无法精确计算时的默认退避秒数
    # 输出：
    # - 非负等待秒数；没有限流窗口时返回 fallback_seconds
    def retry_after_seconds(self, account_key: str, fallback_seconds: float = 0.5) -> float:
        normalized_account = str(account_key or "").strip()
        try:
            fallback = max(0.0, float(fallback_seconds))
        except (TypeError, ValueError):
            fallback = 0.5
        with self._lock:
            now = time.time()
            retry_after = 0.0
            next_available_at = float(self._account_next_available_at.get(normalized_account) or 0.0)
            if now < next_available_at:
                retry_after = max(retry_after, next_available_at - now)

            cfg = self._account_config.get(normalized_account, {})
            requests_per_minute = max(0, int(cfg.get("requests_per_minute") or 0))
            starts = self._account_request_starts[normalized_account]
            while starts and now - starts[0] >= 60.0:
                starts.popleft()
            if requests_per_minute > 0 and len(starts) >= requests_per_minute and starts:
                retry_after = max(retry_after, 60.0 - (now - starts[0]))

            if retry_after > 0:
                return max(0.0, retry_after)
        return fallback

    # 用途：
    # - 在线更新 account identity 的最大并发数
    # 输入：
    # - account_key/max_concurrent_requests: account identity 和新的最大并发数
    # 输出：
    # - 无；当前运行计数不变，后续 acquire 使用新上限
    def set_account_limit(self, account_key: str, max_concurrent_requests: int) -> None:
        resolved_limit = max(1, int(max_concurrent_requests or 1))
        normalized_account = str(account_key or "").strip()
        with self._lock:
            current = dict(self._account_config.get(normalized_account) or {})
            current["max_concurrent_requests"] = resolved_limit
            self._account_config[normalized_account] = current
