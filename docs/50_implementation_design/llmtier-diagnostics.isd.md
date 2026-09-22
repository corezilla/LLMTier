# LLMTier Diagnostics ISD

> 参考：[模块设计](../40_module_design/llmtier-diagnostics-design.md)

本文规定 diagnostics 模块的 SQLite Schema 和类实现细节。

## 1. SQLite Schema

### 1.1 diagnostic_snapshots

```sql
CREATE TABLE diagnostic_snapshots (
    id              TEXT PRIMARY KEY,        -- "snap_{uuid}"
    request_id      TEXT NOT NULL,           -- 普通列（非 FK）
    captured_at     TEXT NOT NULL,           -- ISO 8601 时间戳

    upstream_url    TEXT NOT NULL,           -- 已脱敏（移除 query string）
    backend_model   TEXT,
    http_status     INTEGER,
    latency_ms      REAL,
    error_summary   TEXT,                    -- UTF-8 安全截断 256 字节

    model           TEXT,
    deployment_id   TEXT,

    snapshot_type   TEXT DEFAULT 'upstream'  -- 'upstream' | 'error'
);

CREATE INDEX idx_snapshots_request_id ON diagnostic_snapshots(request_id);
CREATE INDEX idx_snapshots_captured_at ON diagnostic_snapshots(captured_at);
```

### 1.2 diagnostic_injections

```sql
CREATE TABLE diagnostic_injections (
    id              TEXT PRIMARY KEY,
    deployment_id   TEXT NOT NULL,
    injection_type  TEXT NOT NULL,

    fault_status    INTEGER,
    fault_body      TEXT,
    delay_ms        INTEGER,
    retry_after_sec INTEGER,
    stream_terminate_after_events INTEGER,
    malformed_after_events INTEGER,
    malformed_event_type TEXT,
    config_json     TEXT NOT NULL,

    enabled         INTEGER NOT NULL DEFAULT 0,

    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,

    UNIQUE(deployment_id, injection_type),
    FOREIGN KEY (deployment_id) REFERENCES deployments(id) ON DELETE CASCADE
);
```

### 1.3 data_plane_stats

```sql
CREATE TABLE data_plane_stats (
    id              TEXT PRIMARY KEY,        -- "stat_{deployment_id}_{model}_{stat_hour}"，NULL 值用 "_global_" 替代
    deployment_id   TEXT,
    model           TEXT,
    stat_hour       TEXT NOT NULL,           -- ISO hour YYYY-MM-DDTHH

    request_count   INTEGER NOT NULL DEFAULT 0,
    error_4xx_count INTEGER NOT NULL DEFAULT 0,
    error_5xx_count INTEGER NOT NULL DEFAULT 0,

    latency_p50_ms  REAL,
    latency_p95_ms  REAL,
    latency_min_ms  REAL,
    latency_max_ms  REAL,
    latency_sum_ms  REAL NOT NULL DEFAULT 0,

    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX idx_stats_deployment_model ON data_plane_stats(deployment_id, model, stat_hour);
CREATE INDEX idx_stats_stat_hour ON data_plane_stats(stat_hour);
```

### 1.4 trace_events

```sql
CREATE TABLE trace_events (
    id              TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL,

    stage           TEXT NOT NULL,           -- 见 TraceStage 常量
    stage_timestamp TEXT NOT NULL,
    detail          TEXT,                    -- JSON

    correlation_id  TEXT,

    created_at      TEXT NOT NULL
);

CREATE INDEX idx_trace_request_id ON trace_events(request_id);
CREATE INDEX idx_trace_correlation_id ON trace_events(correlation_id);
```

## 2. 常量定义

```python
class TraceStage:
    RECEIVED         = "received"
    VALIDATED        = "validated"
    ROUTED           = "routed"
    UPSTREAM_STARTED = "upstream_started"
    UPSTREAM_ENDED   = "upstream_ended"
    COMPLETED        = "completed"
    ERROR            = "error"
    ABORTED          = "aborted"


class InjectionType:
    FAULT_502        = "fault_502"
    FAULT_503        = "fault_503"
    DELAY            = "delay"
    RATE_LIMIT       = "rate_limit"
    STREAM_TERMINATE = "stream_terminate"
    MALFORMED_EVENT  = "malformed_event"
```

## 3. DiagnosticService 实现

```python
class DiagnosticService:
    MAX_CACHE_ENTRIES = 100_000

    def __init__(self, store: Store, logs: OperationalLog, audit: AuditLog):
        self.store = store
        self.logs = logs
        self.audit = audit
        self._stats_cache: dict[str, list[float]] = {}
        self._stats_lock = threading.Lock()
        self._last_cleanup_ts: float = 0

    # ---- 私有辅助方法 ----

    def _stats_cache_key(self, deployment_id, model, stat_hour):
        d = deployment_id or "_global_"
        m = model or "_global_"
        return f"{d}:{m}:{stat_hour}"

    def _enforce_cache_limit(self):
        if len(self._stats_cache) > self.MAX_CACHE_ENTRIES:
            excess = len(self._stats_cache) - int(self.MAX_CACHE_ENTRIES * 0.9)
            keys_to_remove = list(self._stats_cache.keys())[:excess]
            for k in keys_to_remove:
                del self._stats_cache[k]

    def _truncate_summary(self, text: str, max_bytes: int = 256) -> str:
        if len(text.encode("utf-8")) <= max_bytes:
            return text
        result = text
        while len(result.encode("utf-8")) > max_bytes:
            result = result[:-1]
        return result

    def _sanitize_url(self, url: str) -> str:
        idx = url.find("?")
        return url[:idx] if idx != -1 else url

    def _cleanup_if_needed(self):
        import time
        now = time.time()
        if now - self._last_cleanup_ts > 86400:
            self.cleanup_old_records()
            self._last_cleanup_ts = now

    def _current_stat_hour(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")

    # ---- 公共 API ----
    # 见 llmtier-diagnostics-design.md §4
```

## 4. migration 文件

文件名：`migrations/002_diagnostics.sql`
