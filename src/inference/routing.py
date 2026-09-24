from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from collections import defaultdict
from contextlib import contextmanager

from http_api.errors import ApiError
from management.registry import Candidate, Registry


class Router:
    def __init__(self, registry: Registry):
        self.registry = registry
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._inflight: dict[str, int] = defaultdict(int)
        self._provider_inflight: dict[str, int] = defaultdict(int)
        self._provider_dispatches: dict[str, deque[float]] = defaultdict(deque)
        self._provider_last_dispatch: dict[str, float] = defaultdict(float)
        self._queues: dict[str, deque[str]] = defaultdict(deque)

    def _limit(self, candidate: Candidate) -> int:
        profile = self.registry.store.one("SELECT max_in_flight FROM deployment_runtime_profiles WHERE deployment_id=?", (candidate.deployment_id,))
        return int(profile["max_in_flight"]) if profile else 1

    def _provider_profile(self, provider_id: str):
        return self.registry.store.one("SELECT * FROM provider_usage_profiles WHERE provider_id=?", (provider_id,))

    def _provider_ready_in(self, provider_id: str, now_value: float) -> float:
        profile = self._provider_profile(provider_id)
        if profile is None:
            return 0.0
        delay = max(0.0, float(profile["min_request_interval_ms"]) / 1000 - (now_value - self._provider_last_dispatch[provider_id]))
        rpm = int(profile["requests_per_minute"])
        history = self._provider_dispatches[provider_id]
        while history and now_value - history[0] >= 60:
            history.popleft()
        if rpm > 0 and len(history) >= rpm:
            delay = max(delay, 60 - (now_value - history[0]))
        return delay

    def snapshot(self) -> dict[str, object]:
        """Return a read-only, point-in-time view of gateway concurrency."""
        profiles = self.registry.store.all(
            "SELECT deployment_id,max_in_flight FROM deployment_runtime_profiles ORDER BY deployment_id"
        )
        with self._condition:
            deployments = {
                row["deployment_id"]: {
                    "running": int(self._inflight[row["deployment_id"]]),
                    "max_concurrent": int(row["max_in_flight"]),
                }
                for row in profiles
            }
            queues = {level_id: len(queue) for level_id, queue in self._queues.items() if queue}
            providers = {
                row["provider_id"]: {
                    "running": int(self._provider_inflight[row["provider_id"]]),
                    "max_concurrent": int(row["max_concurrent_requests"]),
                    "min_request_interval_ms": int(row["min_request_interval_ms"]),
                    "requests_per_minute": int(row["requests_per_minute"]),
                }
                for row in self.registry.store.all("SELECT provider_id,max_concurrent_requests,min_request_interval_ms,requests_per_minute FROM provider_usage_profiles ORDER BY provider_id")
            }
        return {"deployments": deployments, "providers": providers, "queues": queues}

    @contextmanager
    def admit(self, level_id: str):
        candidates = self.registry.candidates(level_id)
        if not candidates:
            raise ApiError(404, "model_not_found", "No enabled backend is configured for this model")
        ticket, deadline = uuid.uuid4().hex, time.monotonic() + 30
        with self._condition:
            if len(self._queues[level_id]) >= 32:
                raise ApiError(429, "rate_limit_exceeded", "Service-level queue is full", retryable=True, headers={"Retry-After": "30"})
            self._queues[level_id].append(ticket)
            try:
                while True:
                    candidates = self.registry.candidates(level_id)
                    healthy = [c for c in candidates if c.health == "healthy"]
                    if not healthy: raise ApiError(503, "model_unavailable", "All configured backends are unhealthy", retryable=True)
                    now_value = time.monotonic()
                    capacity = []
                    waits = []
                    for candidate_item in healthy:
                        profile = self._provider_profile(candidate_item.provider_id)
                        provider_limit = int(profile["max_concurrent_requests"]) if profile else 1
                        wait = self._provider_ready_in(candidate_item.provider_id, now_value)
                        if self._inflight[candidate_item.deployment_id] < self._limit(candidate_item) and self._provider_inflight[candidate_item.provider_id] < provider_limit and wait <= 0:
                            capacity.append(candidate_item)
                        elif wait > 0:
                            waits.append(wait)
                    available = capacity
                    if self._queues[level_id][0] == ticket and available:
                        candidate = min(available, key=lambda c: (self._inflight[c.deployment_id], c.ordinal))
                        self._queues[level_id].popleft(); self._inflight[candidate.deployment_id] += 1
                        self._provider_inflight[candidate.provider_id] += 1
                        self._provider_last_dispatch[candidate.provider_id] = now_value
                        self._provider_dispatches[candidate.provider_id].append(now_value)
                        self._condition.notify_all(); break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0: raise ApiError(429, "rate_limit_exceeded", "Service-level queue wait timed out", retryable=True, headers={"Retry-After": "1"})
                    self._condition.wait(min([remaining, *waits]) if waits else remaining)
            except Exception:
                if ticket in self._queues[level_id]: self._queues[level_id].remove(ticket); self._condition.notify_all()
                raise
        try:
            yield candidate
        finally:
            with self._condition:
                self._inflight[candidate.deployment_id] -= 1
                self._provider_inflight[candidate.provider_id] -= 1
                self._condition.notify_all()
