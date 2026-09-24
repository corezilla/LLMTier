"""DiagnosticsService — the libdiag (M006) composition point.

`diagnostics.py` is kept (rather than removed) because this is where the
feature modules combine: one Store + logs behind the stable ISD method surface
consumed by M001 (HTTP API), M003 (inference) and M005 (observability).

Feature modules:
  settings.py    switches / set_switches
  traces.py      record_trace / trace / traces
  snapshots.py   capture_snapshot / snapshots_page   (uses settings)
  stats.py       record_latency / stats              (uses settings)
  injections.py  set_injections / injections / enabled_injection / enabled_stream_injection
  stream.py      stream_wrapper                      (uses injections)
  retention.py   cleanup
"""
from __future__ import annotations

from typing import Iterable

from util.store import Store

from .injections import InjectionDiagnostics
from .retention import cleanup as _cleanup
from .settings import SettingsDiagnostics
from .snapshots import SnapshotDiagnostics
from .stats import StatsDiagnostics
from .stream import stream_wrapper as _stream_wrapper
from .traces import TraceDiagnostics


class DiagnosticsService:
    """LT-OBS 可观测性服务：trace / 快照 / 统计 / 注入开关（组合点）。

    所有 record_* 均 fail-open：观测失败不得影响 Data Plane 可用性。
    """

    def __init__(self, store: Store, logs=None):
        self.store = store
        self.logs = logs
        self._settings = SettingsDiagnostics(store)
        self._traces = TraceDiagnostics(store, self._warn)
        self._snapshots = SnapshotDiagnostics(store, self._settings, self._warn)
        self._stats = StatsDiagnostics(store, self._settings, self._warn)
        self._injections = InjectionDiagnostics(store)

    def _warn(self, message: str) -> None:
        try:
            if self.logs:
                self.logs.record("warning", "diagnostics", "capture_failed", message)
        except Exception:
            pass

    # ------------------------------------------------------------ 开关
    def switches(self) -> dict[str, bool]:
        return self._settings.switches()

    def set_switches(self, snapshots_enabled: bool | None = None, stats_enabled: bool | None = None, conn=None) -> dict[str, bool]:
        return self._settings.set_switches(snapshots_enabled, stats_enabled, conn)

    # ------------------------------------------------------------ trace（LT-OBS-6）
    def record_trace(self, request_id: str, stage: str, detail: dict | None = None, correlation_id: str | None = None) -> None:
        self._traces.record_trace(request_id, stage, detail, correlation_id)

    def trace(self, request_id: str) -> dict:
        return self._traces.trace(request_id)

    def traces(self, since: str | None = None, until: str | None = None, deployment_id: str | None = None,
               model: str | None = None, limit: int = 50, cursor: str | None = None) -> dict:
        return self._traces.traces(since, until, deployment_id, model, limit, cursor)

    # ------------------------------------------------------------ 快照（LT-OBS-1）
    def capture_snapshot(self, request_id: str, deployment_id: str | None, model: str | None, upstream_url: str,
                         backend_model: str | None, http_status: int | None, latency_ms: float | None, error_summary: str | None) -> str | None:
        return self._snapshots.capture_snapshot(request_id, deployment_id, model, upstream_url, backend_model, http_status, latency_ms, error_summary)

    def snapshots_page(self, since: str | None, until: str | None, deployment_id: str | None, model: str | None,
                       limit: int = 50, cursor: str | None = None) -> dict:
        return self._snapshots.snapshots_page(since, until, deployment_id, model, limit, cursor)

    # ------------------------------------------------------------ 统计（LT-OBS-2）
    def record_latency(self, deployment_id: str | None, model: str | None, status_code: int | None, latency_ms: float | None) -> None:
        self._stats.record_latency(deployment_id, model, status_code, latency_ms)

    def stats(self, since: str, until: str, deployment_id: str | None = None, model: str | None = None) -> dict:
        return self._stats.stats(since, until, deployment_id, model)

    # ------------------------------------------------------------ 注入（LT-OBS-5）
    def set_injections(self, deployment_id: str, actor_items: list[dict], conn=None) -> list[dict]:
        return self._injections.set_injections(deployment_id, actor_items, conn)

    def injections(self, deployment_id: str) -> list[dict]:
        return self._injections.injections(deployment_id)

    def enabled_injection(self, deployment_id: str) -> dict | None:
        return self._injections.enabled_injection(deployment_id)

    def enabled_stream_injection(self, deployment_id: str) -> dict | None:
        return self._injections.enabled_stream_injection(deployment_id)

    # ------------------------------------------------------------ 流包装
    def stream_wrapper(self, deployment_id: str, base_stream: Iterable[bytes]) -> Iterable[bytes]:
        return _stream_wrapper(self._injections, deployment_id, base_stream)

    # ------------------------------------------------------------ 保留期
    def cleanup(self, days: int = 7) -> int:
        return _cleanup(self.store, self._warn, days)
