# LLMTier Diagnostics 模块实现设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry）

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-diagnostics-isd` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `design.definition` |
| Template Version | `1.0.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |

## 1. 实现范围

本文规定 `diagnostics` 模块的实现细节：
- 新增模块 `diagnostics.py`（`DiagnosticService`）
- 新增 4 张数据库表（`diagnostic_snapshots`、`diagnostic_injections`、`data_plane_stats`、`trace_events`）
- 管理面路由注册
- 与 `app.py`、`responses.py`、`usage.py`、`health.py` 的集成点

**不包含：**
- `sse.py` 改造（Phase 5b 单独实施）
- `health.py` readyz 逻辑调整（LT-OBS-4 文档任务）
- 需求文档修改（LT-OBS-3 文档任务）

## 2. 目标文件结构

```text
src/llmtier_v03/
  diagnostics.py          # DiagnosticService + 数据结构 + 路由注册
  migrations/
    002_diagnostics.sql   # 新增 4 张表的 migration
```

## 3. SQLite Schema

### 3.1 `diagnostic_snapshots`

```sql
CREATE TABLE diagnostic_snapshots (
    id              TEXT PRIMARY KEY,        -- "snap_{uuid}"
    request_id      TEXT NOT NULL,           -- 普通列（非 FK）
    captured_at     TEXT NOT NULL,           -- ISO 8601 时间戳

    upstream_url    TEXT NOT NULL,
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

### 3.2 `diagnostic_injections`

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

### 3.3 `data_plane_stats`

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

### 3.4 `trace_events`

```sql
CREATE TABLE trace_events (
    id              TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL,

    stage           TEXT NOT NULL,           -- 见 STAGE 常量
    stage_timestamp TEXT NOT NULL,
    detail          TEXT,                    -- JSON

    correlation_id  TEXT,

    created_at      TEXT NOT NULL
);

CREATE INDEX idx_trace_request_id ON trace_events(request_id);
CREATE INDEX idx_trace_correlation_id ON trace_events(correlation_id);
```

### 3.5 operational_logs 模块注册

`diagnostic_injections` 表 INSERT/TRIGGER 时，写入 `operational_logs`（module=`diagnostics`）。

## 4. 类与数据结构

### 4.1 常量

```python
# trace_events.stage 取值
class TraceStage:
    RECEIVED        = "received"
    VALIDATED       = "validated"
    ROUTED          = "routed"
    UPSTREAM_STARTED = "upstream_started"
    UPSTREAM_ENDED  = "upstream_ended"
    COMPLETED       = "completed"
    ERROR           = "error"
    ABORTED         = "aborted"

# injection_type 取值
class InjectionType:
    FAULT_502       = "fault_502"
    FAULT_503       = "fault_503"
    DELAY           = "delay"
    RATE_LIMIT      = "rate_limit"
    STREAM_TERMINATE = "stream_terminate"
    MALFORMED_EVENT = "malformed_event"
```

### 4.2 DiagnosticService

```python
class DiagnosticService:
    # LRU 缓存上限
    MAX_CACHE_ENTRIES = 100_000

    def __init__(self, store: Store, logs: OperationalLog, audit: AuditLog):
        self.store = store
        self.logs = logs
        self.audit = audit
        # (deployment_id, model, stat_hour) -> list[float] (latencies)
        self._stats_cache: dict[str, list[float]] = {}
        self._stats_lock = threading.Lock()
        self._last_cleanup_ts: float = 0  # 上次 TTL cleanup 时间戳

    # ---- 私有辅助方法 ----

    def _stats_cache_key(self, deployment_id: str | None, model: str | None, stat_hour: str) -> str:
        """生成缓存 key，NULL 值用 '_global_' 替代"""
        d = deployment_id or "_global_"
        m = model or "_global_"
        return f"{d}:{m}:{stat_hour}"

    def _enforce_cache_limit(self) -> None:
        """LRU 淘汰：超过 MAX_CACHE_ENTRIES 时删除最旧条目（按 key 顺序，简单淘汰）"""
        if len(self._stats_cache) > self.MAX_CACHE_ENTRIES:
            # 按插入顺序淘汰前 10% 最旧的条目
            excess = len(self._stats_cache) - int(self.MAX_CACHE_ENTRIES * 0.9)
            keys_to_remove = list(self._stats_cache.keys())[:excess]
            for k in keys_to_remove:
                del self._stats_cache[k]

    def _truncate_summary(self, text: str, max_bytes: int = 256) -> str:
        """UTF-8 安全字节截断（避免截断在多字节字符中间）"""
        if len(text.encode("utf-8")) <= max_bytes:
            return text
        # 从后向前找到不超过 max_bytes 的最长前缀
        result = text
        while len(result.encode("utf-8")) > max_bytes:
            result = result[:-1]
        return result

    def _sanitize_url(self, url: str) -> str:
        """移除 URL 中的 query string（provider API key 不在 query string，但做防御性处理）"""
        # 移除 ? 后的所有内容
        idx = url.find("?")
        return url[:idx] if idx != -1 else url

    def _cleanup_if_needed(self) -> None:
        """应用内定时 TTL cleanup：上次清理后超过 24 小时则清理 7 天前旧数据"""
        import time
        now = time.time()
        if now - self._last_cleanup_ts > 86400:  # 24 小时
            self.cleanup_old_records()
            self._last_cleanup_ts = now

    # LT-OBS-1: 快照
    def capture_snapshot(self, request_id: str, upstream_url: str,
                         backend_model: str | None, http_status: int,
                         latency_ms: float, error_summary: str | None,
                         model: str | None, deployment_id: str | None,
                         snapshot_type: str = "upstream") -> str:
        """写入 diagnostic_snapshots，返回 snapshot_id"""
        # URL 脱敏 + 错误摘要截断
        safe_url = self._sanitize_url(upstream_url)
        safe_summary = self._truncate_summary(error_summary) if error_summary else None

    def list_snapshots(self, since: str | None, until: str | None,
                       deployment_id: str | None, model: str | None,
                       limit: int, cursor: str | None) -> dict:
        """分页查询快照"""

    # LT-OBS-2: 统计
    def record_latency(self, deployment_id: str | None, model: str | None,
                       http_status: int, latency_ms: float) -> None:
        """每次请求完成后调用，追加到内存缓存，自动 LRU 淘汰"""
        self._cleanup_if_needed()
        key = self._stats_cache_key(deployment_id, model, self._current_stat_hour())
        with self._stats_lock:
            if key not in self._stats_cache:
                self._stats_cache[key] = []
            self._stats_cache[key].append(latency_ms)
            self._enforce_cache_limit()

    def _current_stat_hour(self) -> str:
        """返回当前小时的 ISO hour 字符串（YYYY-MM-DDTHH）"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")

    def get_stats(self, since: str | None, until: str | None,
                  deployment_id: str | None, model: str | None) -> dict:
        """查询统计数据（内存缓存 + data_plane_stats 表合并）"""

    # LT-OBS-5: 注入配置
    def get_injections(self, deployment_id: str) -> list[dict]:
        """获取某 deployment 所有注入配置"""

    def upsert_injections(self, deployment_id: str,
                          injections: list[dict]) -> None:
        """批量 upsert 注入配置（部分更新）"""

    def get_enabled_injections(self, deployment_id: str) -> list[dict]:
        """获取某 deployment 所有 enabled=True 的注入配置（可能多个同时生效）"""

    # LT-OBS-6: trace
    def record_trace(self, request_id: str, stage: str,
                     detail: dict | None, correlation_id: str | None) -> None:
        """写入 trace_events"""

    def get_trace(self, request_id: str) -> dict:
        """查询某 request_id 的完整 trace"""

    # TTL cleanup
    def cleanup_old_records(self) -> int:
        """删除 7 天前的 snapshots 和 trace_events，返回删除条数"""
```

### 4.3 DiagnosticInjection 数据类

```python
@dataclass
class DiagnosticInjection:
    id: str
    deployment_id: str
    injection_type: str
    enabled: bool
    fault_status: int | None = None
    fault_body: str | None = None
    delay_ms: int | None = None
    retry_after_sec: int | None = None
    stream_terminate_after_events: int | None = None
    malformed_after_events: int | None = None
    malformed_event_type: str | None = None
    config_json: str = "{}"
    created_at: str = ""
    updated_at: str = ""
```

### 4.4 DiagnosticSnapshot 数据类

```python
@dataclass
class DiagnosticSnapshot:
    id: str
    request_id: str
    captured_at: str
    upstream_url: str
    backend_model: str | None
    http_status: int | None
    latency_ms: float | None
    error_summary: str | None
    model: str | None
    deployment_id: str | None
    snapshot_type: str = "upstream"
```

## 5. 路由注册

在 `Application.__init__` 中：

```python
self.diagnostics = DiagnosticService(self.store, self.logs, self.audit)
```

在 `Handler._dispatch()` 中新增路由：

```python
elif path.startswith("/tier/admin/v1/diagnostics/"):
    self._diag_dispatch(path, query)
elif path == "/tier/admin/v1/trace" and self.path_parts[3]:
    # /tier/admin/v1/trace/{request_id}
    self._trace_view(self.path_parts[3])
elif path.startswith("/tier/admin/v1/deployments/") and path.endswith("/diagnostics"):
    # /tier/admin/v1/deployments/{id}/diagnostics
    deployment_id = self.path_parts[3]
    self._injection_view(deployment_id, query)
```

**路由处理函数：**

| 路由 | 函数 |
|---|---|
| `GET /tier/admin/v1/diagnostics/snapshots` | `_diag_snapshots_view()` |
| `GET /tier/admin/v1/diagnostics/stats` | `_diag_stats_view()` |
| `GET /tier/admin/v1/deployments/{id}/diagnostics` | `_injection_view(deployment_id, query)` |
| `PATCH /tier/admin/v1/deployments/{id}/diagnostics` | `_injection_view(deployment_id, query)` |
| `GET /tier/admin/v1/trace/{request_id}` | `_trace_view(request_id)` |

## 6. 集成点

### 6.1 BaseHandler._run() — trace received

```python
# 在 Handler._run() 的 try: self._dispatch() 之前
correlation_id = self.headers.get("X-Correlation-ID") or self.headers.get("traceparent")
app.diagnostics.record_trace(
    request_id=self.request_id,
    stage=TraceStage.RECEIVED,
    detail={
        "content_type": self.headers.get("Content-Type"),
        "content_length": self.headers.get("Content-Length"),
    },
    correlation_id=correlation_id,
)
```

### 6.2 ResponsesService.create() — trace validated

```python
# 在请求校验完成后
app.diagnostics.record_trace(
    request_id=request_id,
    stage=TraceStage.VALIDATED,
    detail={"model": model, "valid": True},
    correlation_id=correlation_id,
)
```

### 6.3 Router.admit() — trace routed

```python
# 在成功选中 candidate 后
app.diagnostics.record_trace(
    request_id=request_id,
    stage=TraceStage.ROUTED,
    detail={
        "deployment_id": candidate.deployment.id,
        "provider_id": candidate.deployment.provider_id,
    },
    correlation_id=correlation_id,
)
```

### 6.4 adapter.complete() 前后 — trace upstream_started / snapshot

```python
# 在 adapter.complete() 调用前
app.diagnostics.record_trace(
    request_id=request_id,
    stage=TraceStage.UPSTREAM_STARTED,
    detail=None,
    correlation_id=correlation_id,
)

# 在 adapter.complete() 返回后（无论成功/失败）
try:
    result = adapter.complete(...)
    # ... 处理 result ...
    app.diagnostics.capture_snapshot(
        request_id=request_id,
        upstream_url=upstream_url,
        backend_model=result.model,
        http_status=200,
        latency_ms=latency_ms,
        error_summary=None,
        model=model,
        deployment_id=deployment_id,
    )
    app.diagnostics.record_trace(
        request_id=request_id,
        stage=TraceStage.UPSTREAM_ENDED,
        detail={"snapshot_id": snapshot_id, "http_status": 200},
        correlation_id=correlation_id,
    )
except Exception as e:
    app.diagnostics.capture_snapshot(
        request_id=request_id,
        upstream_url=upstream_url,
        backend_model=None,
        http_status=getattr(e, 'status', 500),
        latency_ms=latency_ms,
        error_summary=app.diagnostics._truncate_summary(str(e)),
        model=model,
        deployment_id=deployment_id,
        snapshot_type="error",
    )
    app.diagnostics.record_trace(
        request_id=request_id,
        stage=TraceStage.ERROR,
        detail={"error": str(e)[:256]},
        correlation_id=correlation_id,
    )
```

### 6.5 SSE 流结束后 — trace completed/aborted

```python
# 在 SSE 流正常结束时
app.diagnostics.record_trace(
    request_id=request_id,
    stage=TraceStage.COMPLETED,
    detail={"reason": "stream_end"},
    correlation_id=correlation_id,
)

# 在 SSE 流异常终止时
app.diagnostics.record_trace(
    request_id=request_id,
    stage=TraceStage.ABORTED,
    detail={"reason": "client_disconnect" or error_reason},
    correlation_id=correlation_id,
)
```

### 6.6 统计记录 — record_latency

```python
# 在请求完成后（无论是成功还是错误）
app.diagnostics.record_latency(
    deployment_id=deployment_id,
    model=model,
    http_status=http_status,
    latency_ms=latency_ms,
)
```

### 6.7 注入检查 — get_enabled_injection

```python
# 在 Router.admit() 成功后、adapter.complete() 调用前
injections = app.diagnostics.get_enabled_injections(deployment_id)
for injection in injections:
    # 根据 injection.type 处理注入
    if injection.injection_type == InjectionType.DELAY:
        time.sleep(injection.delay_ms / 1000)
    elif injection.injection_type == InjectionType.FAULT_502:
        return error_response(injection.fault_status, injection.fault_body)
    # ... 其他类型
    # 注意：多个注入同时生效时，按 injections 列表顺序处理
```

## 7. 错误处理策略

| 场景 | 策略 |
|---|---|
| `capture_snapshot` 写入失败 | 记录 warning 到 `operational_logs`，不抛异常，不阻塞推理 |
| `record_latency` 缓存满 | 记录 warning，丢弃最旧条目，继续运行 |
| `record_trace` 写入失败 | 记录 warning，继续运行（trace 丢失不影响业务） |
| `DiagnosticService` 初始化失败 | 记录 error，继续运行（fail-open，Data Plane 不受影响） |
| 磁盘空间不足 | 停止快照写入，记录 error，不阻塞推理 |

## 8. 实现检查清单

- [ ] `migrations/002_diagnostics.sql` 创建 4 张表
- [ ] `diagnostics.py` 实现 `DiagnosticService` 类
- [ ] `logs.py` 的 `MODULE_KEYS` 注册 `'diagnostics'`
- [ ] `app.py` 创建 `DiagnosticService` 实例并注册路由
- [ ] `BaseHandler._run()` 集成 trace received + correlation_id 提取
- [ ] `responses.py` 集成 trace validated/routed/upstream_started/upstream_ended/completed + snapshot + record_latency
- [ ] `router.py` 或 `responses.py` 集成注入检查（Phase 5a）
- [ ] `admin.py` 或独立路由实现 5 个管理面接口
- [ ] TTL cleanup job（每日或每小时执行）
- [ ] 单元测试覆盖核心方法
- [ ] B-class 系统测试覆盖管理面接口

## 9. 尚未确定事项

1. **SSE 注入（Phase 5b）**：`SSEmitter.put()` 改造方案 A 还是 B？
2. **stats 内存缓存持久化**：进程重启后缓存丢失，是否可接受？（R-6 已说明 stats 仅参考，对账以 usage 账本为准）
3. **TTL cleanup 是否写入 operational_logs**：建议记录一条 `info` 级别日志（module=`diagnostics`）

## 10. 参考

- [可观测性子系统系统设计](../20_system_design/llmtier-observability-subsystem-design-v0.1.md)
- `src/llmtier_v03/store.py` — Store 实现参考
- `src/llmtier_v03/logs.py` — OperationalLog 参考
- `src/llmtier_v03/audit.py` — AuditLog 参考
- `src/llmtier_v03/usage.py` — UsageRecorder 参考（理解事务模式）
