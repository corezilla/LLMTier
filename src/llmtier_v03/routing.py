from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from collections import defaultdict
from contextlib import contextmanager

from .errors import ApiError
from .registry import Candidate, Registry


class Router:
    def __init__(self, registry: Registry):
        self.registry = registry
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._inflight: dict[str, int] = defaultdict(int)
        self._queues: dict[str, deque[str]] = defaultdict(deque)

    def _limit(self, candidate: Candidate) -> int:
        profile = self.registry.store.one("SELECT max_in_flight FROM deployment_runtime_profiles WHERE deployment_id=?", (candidate.deployment_id,))
        return int(profile["max_in_flight"]) if profile else 1

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
        return {"deployments": deployments, "queues": queues}

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
                    available = [c for c in healthy if self._inflight[c.deployment_id] < self._limit(c)]
                    if self._queues[level_id][0] == ticket and available:
                        candidate = min(available, key=lambda c: (self._inflight[c.deployment_id], c.ordinal))
                        self._queues[level_id].popleft(); self._inflight[candidate.deployment_id] += 1; self._condition.notify_all(); break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0: raise ApiError(429, "rate_limit_exceeded", "Service-level queue wait timed out", retryable=True, headers={"Retry-After": "1"})
                    self._condition.wait(remaining)
            except Exception:
                if ticket in self._queues[level_id]: self._queues[level_id].remove(ticket); self._condition.notify_all()
                raise
        try:
            yield candidate
        finally:
            with self._condition:
                self._inflight[candidate.deployment_id] -= 1
                self._condition.notify_all()
