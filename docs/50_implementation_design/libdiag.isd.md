<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M006 libdiag 实现规格设计（ISD）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `libdiag-isd` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Document Owner | LLMTier |
| Last Modified Date | `2026-09-23` |
| Template ID | `design.implementation` |
| Template Version | `0.3.0` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 实现目标与输入基线

<a id="isd-scope"></a>

### 1.1 实现对象

- **模块 ID / 名称**：M006 / `libdiag`
- **直属父对象 / 父设计**：LLMTier 软件系统 / `llmtier-system-design`（§3.2 登记）
- **模块设计 Document ID / 版本 / 路径 / 摘要**：`libdiag` / `0.1.0-draft.1` / `docs/40_module_design/libdiag-design.md` / §2 F-DIAG-SWITCH/TRACE/SNAPSHOT/STATS/INJECT/TRACES/STREAM/CLEANUP、§8 RULE-DIAG-SWITCH/TRUNC/PCTL/INJECT
- **需求与 Constraint ID**：`C-OBS-1`（默认关零开销）、`C-OBS-2`（fail-open）、`C-OBS-3`（不记 Secret/正文）、`C-OBS-4`（注入标注）；机制 `R-OBS-01`、`R-OBS-06`
- **实现范围 / 非目标**：实现 `DiagnosticsService`（开关/注入/trace/快照/统计/流包装/清理）与观测表 DDL；**非目标**：查询呈现与路由（M005）、HTTP（M001）、推理决策（M003）
- **ISD 默认落位或项目批准路径**：`docs/50_implementation_design/libdiag.isd.md`

### 1.2.1 `HO-DIAG-01` · 开关

- **上游信息项 / 规则 ID**：`F-DIAG-SWITCH` / `RULE-DIAG-SWITCH`
- **固定来源 / 版本 / 锚点 / 摘要**：`libdiag` / `0.1.0-draft.1` / `#2.1`、`#8.1`
- **ISD 细化内容 / 章节**：开关读写与短路 → §5.1.1
- **唯一权威位置**：行为在模块 §8.1；本层管实现
- **实现自由度**：存储实现
- **原 V/Case 及本地验证位置**：`VRC-DIAG-001` → §9.1

### 1.2.2 `HO-DIAG-02` · 记录（trace/快照/统计）

- **上游信息项 / 规则 ID**：`F-DIAG-TRACE`、`F-DIAG-SNAPSHOT`、`F-DIAG-STATS`
- **固定来源 / 版本 / 锚点 / 摘要**：`libdiag` / `0.1.0-draft.1` / `#2.2`–`#2.4`
- **ISD 细化内容 / 章节**：记录原语、脱敏截断、分桶/百分位 → §5.1.2–5.1.4
- **唯一权威位置**：行为在模块 §2.2–2.4；本层管实现
- **实现自由度**：存储/聚合实现
- **原 V/Case 及本地验证位置**：`VRC-DIAG-002/003` → §9.1

### 1.2.3 `HO-DIAG-03` · trace 时间窗

- **上游信息项 / 规则 ID**：`F-DIAG-TRACES`（review G-1）
- **固定来源 / 版本 / 锚点 / 摘要**：`libdiag` / `0.1.0-draft.1` / `#2.5.1`
- **ISD 细化内容 / 章节**：时间窗聚合 + 分页 → §5.1.5
- **唯一权威位置**：行为在模块 §2.5.1；本层管实现
- **实现自由度**：分页实现
- **原 V/Case 及本地验证位置**：`VRC-DIAG-004` → §9.1

### 1.2.4 `HO-DIAG-04` · 注入与流包装

- **上游信息项 / 规则 ID**：`F-DIAG-INJECT`、`F-DIAG-STREAM` / `RULE-DIAG-INJECT`
- **固定来源 / 版本 / 锚点 / 摘要**：`libdiag` / `0.1.0-draft.1` / `#2.5`、`#2.6`、`#8.4`
- **ISD 细化内容 / 章节**：注入校验/优先级/单条 enabled、流包装 → §5.1.6–5.1.7
- **唯一权威位置**：行为在模块 §8.4；本层管实现
- **实现自由度**：包装实现
- **原 V/Case 及本地验证位置**：`VRC-DIAG-004` → §9.1

### 1.2.5 `HO-DIAG-05` · 观测表 DDL

- **上游信息项 / 规则 ID**：`R-OBS-06`
- **固定来源 / 版本 / 锚点 / 摘要**：机制 `M-OBS` §14.4 `R-OBS-06`；表契约见 M005/M006
- **ISD 细化内容 / 章节**：`002_observability.sql` → §4.4/§7.2
- **唯一权威位置**：表契约在本层；执行由 M007 `migrate`
- **实现自由度**：DDL 组织
- **原 V/Case 及本地验证位置**：`VRC-DIAG-002` → §9.1

## 2. 既有实现差异（条件章节）

<a id="isd-current-target"></a>

### 2.1 适用性

- **适用性**：`not_applicable`
- **依据**：greenfield/设计先行——前瞻设计，不存在需修改的既有实现
- **Tailoring / 范围决定引用**：`std-tailoring`（设计先行）

## 3. 文件、内部组件与调用关系

<a id="isd-structure"></a>

```text
diagnostics.py
 └─ class DiagnosticsService(store, logs=None)
      ├─ switches()/set_switches(...)                 # 全局开关
      ├─ record_trace(request_id, stage, detail?, correlation_id?)
      ├─ trace(request_id) -> view
      ├─ traces(since?, until?, deployment_id?, model?, limit?, cursor?) -> page
      ├─ capture_snapshot(request_id, ..., error_summary) -> snap_id|None
      ├─ snapshots_page(since, until, ...) -> page
      ├─ record_latency(deployment_id, model, status, latency_ms)
      ├─ stats(since, until, deployment_id?, model?) -> view
      ├─ set_injections(deployment_id, items)/injections(did)
      ├─ enabled_injection(did)/enabled_stream_injection(did) -> dict|None
      ├─ stream_wrapper(did, base_stream) -> Iterable[bytes]
      └─ cleanup(days=7) -> int
migrations/002_observability.sql    # 观测 6 表 DDL
```

### 3.1 `diagnostics.py` · `DiagnosticsService`

- **职责及调用者**：观测底层读写原语；caller=M003/M001（写）、M005（查）
- **类型 / 函数**：见上图
- **可见性**：private
- **调用与类型依赖**：依赖 `Store`（M007）、`logs`（可选，warning）；不 import 业务模块
- **构建目标 / 生成源 / 输出**：无独立构建目标；随包
- **实现状态**：PLANNED

### 3.2 `migrations/002_observability.sql` · 观测 DDL

- **职责及调用者**：建 6 张观测表；由 M007 `migrate()` 执行
- **类型 / 函数**：SQL 脚本
- **可见性**：private（数据文件，随包）
- **调用与类型依赖**：——
- **构建目标 / 生成源 / 输出**：随包
- **实现状态**：PLANNED

## 4. 内部数据与所有权

<a id="isd-data"></a>

纯软件实现：无原生 ABI（Python/JSON/SQLite）。

### 4.1 `diagnostic_settings`

- **类型 / 字段**：`singleton` PK CHECK=1；`snapshots_enabled` INTEGER DEFAULT 0；`stats_enabled` INTEGER DEFAULT 0
- **单位 / 初值 / 范围 / 不变量**：单行；0/1
- **逻辑编码与原生 ABI 适用性**：N/A
- **创建 / 修改者**：`set_switches`
- **Owner / 借用期限 / 释放者**：持久
- **公共类型 authority**：本 ISD §4.1
- **持久化与敏感性**：persistent

### 4.2 `diagnostic_snapshots`

- **类型 / 字段**：`id` PK；`request_id`；`captured_at`；`upstream_url`；`backend_model`；`http_status`；`latency_ms`；`error_summary`；`model`；`deployment_id`；`snapshot_type` DEFAULT 'upstream'
- **单位 / 初值 / 范围 / 不变量**：`upstream_url` 去 query；`error_summary` ≤256B
- **逻辑编码与原生 ABI 适用性**：N/A
- **创建 / 修改者**：`capture_snapshot`
- **Owner / 借用期限 / 释放者**：持久（7 天清理）
- **公共类型 authority**：本 ISD §4.2
- **持久化与敏感性**：persistent；**禁记** Secret/正文

### 4.3 `diagnostic_injections`

- **类型 / 字段**：`id` PK；`deployment_id`；`injection_type`；`fault_status`；`fault_body`；`delay_ms`；`retry_after_sec`；`stream_terminate_after_events`；`malformed_after_events`；`malformed_event_type`；`enabled` DEFAULT 0；`updated_at`；UNIQUE(deployment_id,injection_type)
- **单位 / 初值 / 范围 / 不变量**：`injection_type` 白名单；参数范围见 §6.4
- **逻辑编码与原生 ABI 适用性**：N/A
- **创建 / 修改者**：`set_injections`
- **Owner / 借用期限 / 释放者**：持久
- **公共类型 authority**：本 ISD §4.3
- **持久化与敏感性**：persistent

### 4.4 `trace_events`

- **类型 / 字段**：`id` PK；`request_id`；`stage`；`stage_timestamp`；`detail`；`correlation_id`；`created_at`
- **单位 / 初值 / 范围 / 不变量**：同 request 有序（按 `stage_timestamp,id`）
- **逻辑编码与原生 ABI 适用性**：N/A
- **创建 / 修改者**：`record_trace`
- **Owner / 借用期限 / 释放者**：持久（7 天清理）
- **公共类型 authority**：本 ISD §4.4
- **持久化与敏感性**：persistent；脱敏

### 4.5 `data_plane_stats` / `data_plane_latency_samples`

- **类型 / 字段**：`data_plane_stats(stat_hour, deployment_id, model, status, request_count, error_count, updated_at, PK(stat_hour,deployment_id,model,status))`；`data_plane_latency_samples(stat_hour, deployment_id, model, latency_ms, created_at)`
- **单位 / 初值 / 范围 / 不变量**：小时桶；可丢（非账本）
- **逻辑编码与原生 ABI 适用性**：N/A
- **创建 / 修改者**：`record_latency`
- **Owner / 借用期限 / 释放者**：持久（聚合）；样本由清理
- **公共类型 authority**：本 ISD §4.5
- **持久化与敏感性**：persistent；非权威

## 5. 函数与接口实现规格

<a id="isd-functions"></a>

### 5.1.1 `FUNC-DIAG-SWITCH` · `switches` / `set_switches`

- **文件 / symbol / 可见性**：`diagnostics.py` / `DiagnosticsService.switches/set_switches` / private
- **原成员 ID 或私有来源**：`F-DIAG-SWITCH`、`RULE-DIAG-SWITCH`
- **完整签名与 caller**：`switches() -> dict[str,bool]`；`set_switches(snapshots_enabled: bool|None=None, stats_enabled: bool|None=None) -> dict[str,bool]`；caller=M005
- **输入参数 / 数据结构 authority**：可选开关；None=保持
- **输入约束 / 校验顺序 / 失败映射**：部分更新；DB 错 → `sqlite3.Error`
- **成功输出 / 数据结构 / 后置条件**：`{snapshots_enabled, stats_enabled}`
- **错误输出 / 触发条件 / 优先级**：`sqlite3.Error`
- **副作用 / 执行上下文 / 幂等性**：写 `diagnostic_settings`；幂等（同值）
- **输入输出 ownership 与寿命**：状态持久
- **不可改变的规则 / Constraint ID**：默认关；关闭零写入
- **实现自由度**：存储实现
- **Thread-safe / reentrant**：经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：creates new（写）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-001`

### 5.1.2 `FUNC-DIAG-TRACE` · `record_trace` / `trace`

- **文件 / symbol / 可见性**：`diagnostics.py` / `record_trace`、`trace` / private
- **原成员 ID 或私有来源**：`F-DIAG-TRACE`
- **完整签名与 caller**：`record_trace(request_id, stage, detail=None, correlation_id=None) -> None`；`trace(request_id) -> dict`；caller=M001/M003（写）、M005（查）
- **输入参数 / 数据结构 authority**：`stage`（标识）；`detail`（JSON）；`correlation_id` 可空
- **输入约束 / 校验顺序 / 失败映射**：写失败 → 捕获记 warning（fail-open）
- **成功输出 / 数据结构 / 后置条件**：`trace` 返回 `{request_id, correlation_id?, stages[], snapshot?, usage?}`
- **错误输出 / 触发条件 / 优先级**：无记录 → 404 `not_found`
- **副作用 / 执行上下文 / 幂等性**：追加行；不幂等
- **输入输出 ownership 与寿命**：持久（7 天）
- **不可改变的规则 / Constraint ID**：同 request 有序；fail-open（C-OBS-2）
- **实现自由度**：查询实现
- **Thread-safe / reentrant**：经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：creates new（写）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-002/003`

### 5.1.3 `FUNC-DIAG-SNAPSHOT` · `capture_snapshot` / `snapshots_page`

- **文件 / symbol / 可见性**：`diagnostics.py` / `capture_snapshot`、`snapshots_page` / private
- **原成员 ID 或私有来源**：`F-DIAG-SNAPSHOT`、`RULE-DIAG-TRUNC`
- **完整签名与 caller**：`capture_snapshot(request_id, deployment_id, model, upstream_url, backend_model, http_status, latency_ms, error_summary) -> str|None`；`snapshots_page(since, until, deployment_id, model, limit=50, cursor=None) -> dict`
- **输入参数 / 数据结构 authority**：快照字段；`snapshots_page` 过滤条件
- **输入约束 / 校验顺序 / 失败映射**：开关关闭 → 直接返回 `None`；`upstream_url` 去 query；`error_summary[:256]`；写失败 → warning + `None`
- **成功输出 / 数据结构 / 后置条件**：`snapshot_id`；`{items, next_cursor, has_more}`
- **错误输出 / 触发条件 / 优先级**：写失败不抛；分页 cursor 实现错误 → `sqlite3.Error`
- **副作用 / 执行上下文 / 幂等性**：追加；不幂等
- **输入输出 ownership 与寿命**：持久（7 天）
- **不可改变的规则 / Constraint ID**：脱敏去 query、截断 256、关开关零写入
- **实现自由度**：分页实现
- **Thread-safe / reentrant**：经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：creates new（写）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-002`

### 5.1.4 `FUNC-DIAG-STATS` · `record_latency` / `stats`

- **文件 / symbol / 可见性**：`diagnostics.py` / `record_latency`、`stats`、`_percentile`、`hour_of` / private
- **原成员 ID 或私有来源**：`F-DIAG-STATS`、`RULE-DIAG-PCTL`
- **完整签名与 caller**：`record_latency(deployment_id, model, status_code, latency_ms) -> None`；`stats(since, until, deployment_id=None, model=None) -> dict`；caller=M003（写）、M005（读）
- **输入参数 / 数据结构 authority**：事实字段；查询条件
- **输入约束 / 校验顺序 / 失败映射**：开关关闭 → 短路；缓存满 → LRU 淘汰
- **成功输出 / 数据结构 / 后置条件**：`{request_count, error_count, status_breakdown, error_4xx_count, error_5xx_count, p50, p95, min, max, avg}`
- **错误输出 / 触发条件 / 优先级**：失败 → warning（fail-open）
- **副作用 / 执行上下文 / 幂等性**：聚合更新；并发累积
- **输入输出 ownership 与寿命**：内存/持久；非账本
- **不可改变的规则 / Constraint ID**：`status_breakdown` per-status；可丢、非账本
- **实现自由度**：缓存结构
- **Thread-safe / reentrant**：内部有界缓存；经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：creates new（持久化）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-002`

### 5.1.5 `FUNC-DIAG-TRACES` · `traces`

- **文件 / symbol / 可见性**：`diagnostics.py` / `DiagnosticsService.traces` / private
- **原成员 ID 或私有来源**：`F-DIAG-TRACES`（G-1）
- **完整签名与 caller**：`traces(since=None, until=None, deployment_id=None, model=None, limit=50, cursor=None) -> dict`；caller=M005
- **输入参数 / 数据结构 authority**：时间窗 + 过滤 + 分页
- **输入约束 / 校验顺序 / 失败映射**：`limit` 夹到 `[1,500]`；cursor 基于 `(min_ts, request_id)`
- **成功输出 / 数据结构 / 后置条件**：`{items:[TraceView], next_cursor, has_more}`
- **错误输出 / 触发条件 / 优先级**：无匹配 → 空 items
- **副作用 / 执行上下文 / 幂等性**：只读
- **输入输出 ownership 与寿命**：行由调用方持有
- **不可改变的规则 / Constraint ID**：去重 request；稳定分页
- **实现自由度**：查询实现
- **Thread-safe / reentrant**：经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：joins existing
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-004`

### 5.1.6 `FUNC-DIAG-INJECT` · `set_injections` / `injections` / enabled

- **文件 / symbol / 可见性**：`diagnostics.py` / `set_injections`、`injections`、`enabled_injection`、`enabled_stream_injection`、`_validate` / private
- **原成员 ID 或私有来源**：`F-DIAG-INJECT`、`RULE-DIAG-INJECT`
- **完整签名与 caller**：`set_injections(deployment_id, items) -> list`；`injections(did) -> list`；`enabled_injection(did) -> dict|None`；`enabled_stream_injection(did) -> dict|None`；caller=M005（写）、M003（读）
- **输入参数 / 数据结构 authority**：注入项列表
- **输入约束 / 校验顺序 / 失败映射**：白名单/参数范围；非法 → `ApiError(400, "invalid_injection")`；未知 deployment → 404
- **成功输出 / 数据结构 / 后置条件**：注入项列表；**单条** enabled（多启用项优先 `fault_502→fault_503→rate_limit→delay`）
- **错误输出 / 触发条件 / 优先级**：400/404
- **副作用 / 执行上下文 / 幂等性**：部分更新 upsert
- **输入输出 ownership 与寿命**：持久
- **不可改变的规则 / Constraint ID**：白名单；单条 enabled；优先级确定
- **实现自由度**：校验实现
- **Thread-safe / reentrant**：经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：creates new（写）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-004`

### 5.1.7 `FUNC-DIAG-STREAM` · `stream_wrapper`

- **文件 / symbol / 可见性**：`diagnostics.py` / `DiagnosticsService.stream_wrapper` / private
- **原成员 ID 或私有来源**：`F-DIAG-STREAM`
- **完整签名与 caller**：`stream_wrapper(deployment_id, base_stream) -> Iterable[bytes]`；caller=M001
- **输入参数 / 数据结构 authority**：SSE 字节流
- **输入约束 / 校验顺序 / 失败映射**：无注入 → 透传；命中 `stream_terminate`/`malformed_event` → 截断/畸形
- **成功输出 / 数据结构 / 后置条件**：包装后的字节流
- **错误输出 / 触发条件 / 优先级**：——
- **副作用 / 执行上下文 / 幂等性**：流式包装；不修改无注入流
- **输入输出 ownership 与寿命**：请求级流
- **不可改变的规则 / Constraint ID**：命中确定性；无注入透传
- **实现自由度**：包装实现
- **Thread-safe / reentrant**：yes（无共享）
- **Nested-call policy**：allowed
- **Transaction participation**：none
- **Blocking / timeout / cancellation**：随 base_stream
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-004`（`LT-OPEN-05`）

### 5.1.8 `FUNC-DIAG-CLEANUP` · `cleanup`

- **文件 / symbol / 可见性**：`diagnostics.py` / `DiagnosticsService.cleanup` / private
- **原成员 ID 或私有来源**：`F-DIAG-CLEANUP`
- **完整签名与 caller**：`cleanup(days:int=7) -> int`；caller=启动/M005
- **输入参数 / 数据结构 authority**：`days`
- **输入约束 / 校验顺序 / 失败映射**：失败不阻塞启动（调用方 try/except）
- **成功输出 / 数据结构 / 后置条件**：删除 7 天前快照/trace，返回删除数
- **错误输出 / 触发条件 / 优先级**：`sqlite3.Error`
- **副作用 / 执行上下文 / 幂等性**：删除过期；幂等
- **输入输出 ownership 与寿命**：删除持久行
- **不可改变的规则 / Constraint ID**：保留 7 天
- **实现自由度**：删除实现
- **Thread-safe / reentrant**：经线程内连接
- **Nested-call policy**：allowed
- **Transaction participation**：creates new（写）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-DIAG-002`

### 5.2 错误传播矩阵

#### 5.2.1 `E-DIAG-WRITE` · 记录写入失败

- **底层异常 / 失败事实**：Store 写失败
- **模块是否处理及处理函数**：recover（`_warn` 记录后继续）
- **Typed 异常与原生异常所有权**：内部捕获，不抛到推理路径
- **宿主 / public payload 或状态码**：——
- **日志级别 / 脱敏 / 关联字段**：warning（module=diagnostics）
- **是否可重试及前提**：尽力而为
- **状态与副作用影响 / 验证项**：不改推理结果（C-OBS-2）；`VRC-DIAG-003`

#### 5.2.2 `E-DIAG-INJECT-INVALID` · 注入非法

- **底层异常 / 失败事实**：非法类型/参数
- **模块是否处理及处理函数**：reject（`_validate`）
- **Typed 异常与原生异常所有权**：`DiagnosticsService` 抛 `ApiError(400)`；M005/M001 映射
- **宿主 / public payload 或状态码**：400 `invalid_injection`
- **日志级别 / 脱敏 / 关联字段**：——
- **是否可重试及前提**：修参数后重试
- **状态与副作用影响 / 验证项**：不落库；`VRC-DIAG-004`

#### 5.2.3 `E-DIAG-QUERY` · 查询失败

- **底层异常 / 失败事实**：存储不可读
- **模块是否处理及处理函数**：propagate
- **Typed 异常与原生异常所有权**：原生 `sqlite3.Error`；M005/M001 映射
- **宿主 / public payload 或状态码**：503（不伪装空结果）
- **日志级别 / 脱敏 / 关联字段**：warning
- **是否可重试及前提**：稍后重试
- **状态与副作用影响 / 验证项**：`VRC-DIAG-002`

## 6. 关键流程与算法

<a id="isd-algorithms"></a>

### 6.1 `P-DIAG-RECORD` · 记录

- **触发与执行者**：M003/M001；调用线程
- **入口函数及数据**：`record_trace`/`capture_snapshot`/`record_latency`
- **步骤 / 算法 / 复杂度**：开关判定（关→短路）→ 脱敏/截断/分桶 → 写 Store；O(1)/O(len)
- **判断事实来源**：`switches()`；字段
- **成功可见点**：行/聚合更新
- **失败、取消与清理**：`_warn` 后继续
- **代表输入与中间值**：`upstream_url=?token=x` → 去 query
- **规则 / 接口 / 验证引用**：`RULE-DIAG-SWITCH/TRUNC`；`VRC-DIAG-002/003`

### 6.2 `P-DIAG-INJECT` · 注入判定

- **触发与执行者**：M003 请求路径 / M001 流；调用线程
- **入口函数及数据**：`enabled_injection`/`enabled_stream_injection`/`stream_wrapper`
- **步骤 / 算法 / 复杂度**：查 enabled → 按优先级取**单条** → 命中动作（fault/delay/rate_limit/流截断/畸形）；O(items)
- **判断事实来源**：`diagnostic_injections`（enabled）
- **成功可见点**：注入生效
- **失败、取消与清理**：无注入透传
- **代表输入与中间值**：`delay_ms=2000` → sleep 2s
- **规则 / 接口 / 验证引用**：`RULE-DIAG-INJECT`；`VRC-DIAG-004`

### 6.3 `P-DIAG-PCTL` · 百分位

- **触发与执行者**：`stats`；调用线程
- **入口函数及数据**：`record_latency`/`stats`/`_percentile`/`hour_of`
- **步骤 / 算法 / 复杂度**：小时桶聚合 → 排序求 P50/P95；O(n log n)
- **判断事实来源**：样本集合
- **成功可见点**：统计视图
- **失败、取消与清理**：缓存淘汰
- **代表输入与中间值**：样本 → P50/P95
- **规则 / 接口 / 验证引用**：`RULE-DIAG-PCTL`；`VRC-DIAG-002`

## 7. 并发、失败、持久化与安全生命周期

<a id="isd-lifecycle"></a>

### 7.1 并发、交错与失败收口

#### 7.1.1 `CF-DIAG-STATS` · 统计缓存并发

- **参与线程 / 回调 / 事务**：多请求线程
- **已产生或可能产生的副作用**：缓存更新
- **检测事实 / 期限**：缓存上限
- **状态 / 错误 / 结果已知性**：——
- **保留 / 释放责任**：内部 LRU
- **允许的 query / replay / takeover / retry**：——
- **验证项**：`VRC-DIAG-002`

#### 7.1.2 `CF-DIAG-INIT` · 初始化失败

- **参与线程 / 回调 / 事务**：启动
- **已产生或可能产生的副作用**：无
- **检测事实 / 期限**：构造异常
- **状态 / 错误 / 结果已知性**：已知失败
- **保留 / 释放责任**：宿主降级运行
- **允许的 query / replay / takeover / retry**：重启
- **验证项**：`VRC-DIAG-003`

<a id="isd-persistence"></a>

### 7.2 持久化、恢复与 schema 演进

#### 7.2.1.1 `PF-DIAG` · 观测表事务

- **原规则 / 事务**：单条/单批 INSERT/UPDATE
- **原子范围 / 事务外副作用**：单事务内；无事务外副作用
- **开始 / 提交 / 回滚函数**：`Store.transaction`
- **持久提交点 / 对外响应点**：commit
- **响应丢失后的权威核对**：无（观测非权威）
- **恢复入口 / 判定记录 / 重复恢复条件**：无
- **验证项**：`VRC-DIAG-002`

#### 7.2.2 Schema 演进策略决定

- **Schema authority / 当前版本事实来源**：`002_observability.sql` 由 M007 schema initialization 管理；本层提供 DDL 内容
- **允许的升级模式**：随 M007（仅初始化）
- **明确不接受的迁移模式**：无本层独立迁移（无增量升级 / 无 downgrade / 无自动修复）
- **兼容边界**：随 M007
- **失败后的系统状态与责任方**：随 M007 拒绝启动

#### 7.2.3 库状态分支矩阵

不适用（观测表随 M007 schema 初始化；状态分支见 `util.isd.md` §7.2.3）。

<a id="isd-security"></a>

### 7.3 安全、权限与可观测性

#### 7.3.1.1 `SEC-DIAG-SWITCH` · 默认关 + fail-open

- **原规则**：模块 §1.1.1/§1.1.2（C-OBS-1/2）
- **可信输入 / 敏感字段 / 检查对象**：开关状态
- **检查函数 / 时点**：`switches()` 在每次记录前
- **拒绝 / 宿主交付出口**：关闭 → 短路；失败 → warning
- **脱敏 / 禁止输出**：本层记录只存脱敏字段
- **日志 / 指标 / trace 口径及触发**：本层即观测；warning 走 `logs`
- **验证项**：`VRC-DIAG-001/003`

#### 7.3.2.1 `LSS-DIAG-DB` · 观测表安全

- **适用对象 / 路径 / Owner**：观测 6 表（经 M007）
- **文件与目录权限 / umask**：由 M007
- **Symlink / hardlink / 路径替换策略**：由 M007
- **备份 / 恢复 / 敏感数据静态保护**：**禁记** Secret/凭据/正文；`upstream_url` 去 query、`error_summary` 截断
- **删除 / 擦除 / 保留期限**：7 天清理（`cleanup`）
- **磁盘耗尽 / 只读文件系统行为**：写失败 → warning（fail-open）
- **检查时点 / 判定 / 拒绝或降级出口**：写入前脱敏；失败降级
- **验证项**：`VRC-DIAG-002`

## 8. 资源、构建与宿主接入

<a id="isd-resources"></a>

### 8.1 配置实现（条件项）

- **适用性 / 固定 authority**：applicable（保留期/上限为常量）
- **配置 key / 来源 / 优先级**：`cleanup(days=7)`（调用方传，默认 7）；`limit` 夹值（快照 500、traces 500、stats 无分页）为固定常量
- **类型 / 单位 / 默认值 / 范围 / 字段约束**：`days` 正整数 ≥1
- **读取 / 解析 / 校验 symbol**：`cleanup`
- **生效点 / reload / 原子性 / 在途操作**：启动时清理；无 reload
- **缺失 / 非法 / 部分更新的错误出口**：失败不阻塞启动
- **敏感值存储 / 日志脱敏**：无敏感配置
- **验证项**：`VRC-DIAG-002`

### 8.2.1 `RB-DIAG-BUILD` · 构建与装配

- **目标文件 / 产物 / 构建目标**：`diagnostics.py` + `002_observability.sql`；无独立库
- **工具链 / 语言 / 依赖版本**：Python 3.14；标准库 + `Store`
- **宿主接入 / 初始化 / 退出次序**：宿主装配构造 `DiagnosticsService(store, logs)`；启动调 `cleanup(7)`（fail-open）
- **环境 / 数据规模 / 冷热条件**：单库；保留 7 天
- **峰值构成 / 上限 / 共享额度**：统计内存缓存上限 + LRU；快照/traces 500/页
- **分段预算 / 总期限 / 计时点**：清理为启动期；无总期限
- **超限、部分启动与清理出口**：缓存淘汰；清理失败静默
- **构建或运行命令及前置条件**：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`

## 9. 验证规格与实现任务

<a id="isd-verification"></a>

### 9.1.1 `VRC-DIAG-001` · 开关

- **Rule / 成员**：`F-DIAG-SWITCH`、`RULE-DIAG-SWITCH`
- **V / Case / Vector**：v1 默认关；v2 开/关切换；v3 关闭零写入；v4 部分更新
- **输入 / 故障 / 环境**：开关切换；隔离库
- **独立 Oracle / Expected**：默认 `{False,False}`；关闭时无新行
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit/v03`；隔离库
- **Run ID / Status**：NOT_RUN

### 9.1.2 `VRC-DIAG-002` · 记录与查询

- **Rule / 成员**：`F-DIAG-TRACE/SNAPSHOT/STATS/CLEANUP`、`RULE-DIAG-TRUNC/PCTL`
- **V / Case / Vector**：v1 trace/快照/统计；v2 URL 去 query；v3 summary 截断；v4 百分位；v5 清理 7 天
- **输入 / 故障 / 环境**：一次调用；隔离库
- **独立 Oracle / Expected**：字段/脱敏/百分位正确；7 天前删除
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit/v03`；隔离库
- **Run ID / Status**：NOT_RUN

### 9.1.3 `VRC-DIAG-003` · fail-open

- **Rule / 成员**：`RULE-OBS-FAILOPEN`
- **V / Case / Vector**：v1 写入失败；v2 初始化失败
- **输入 / 故障 / 环境**：库写失败/构造异常
- **独立 Oracle / Expected**：推理结果不变；降级运行
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit/v03`
- **Run ID / Status**：NOT_RUN

### 9.1.4 `VRC-DIAG-004` · 注入与 traces

- **Rule / 成员**：`F-DIAG-INJECT/STREAM/TRACES`、`RULE-DIAG-INJECT`
- **V / Case / Vector**：v1 四类注入；v2 流截断/畸形；v3 非法类型；v4 多 enabled 单条优先级；v5 traces 时间窗/分页
- **输入 / 故障 / 环境**：注入配置；隔离库
- **独立 Oracle / Expected**：400；命中确定性；单条优先级；去重 request
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit/v03`；隔离库
- **Run ID / Status**：NOT_RUN

**运行命令**：全量 `PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q`

<a id="isd-tasks"></a>

### 9.2.1 `TASK-DIAG-TABLES` · 观测表与开关

- **顺序 / 前置项**：1 / —
- **文件 / symbol / 构建目标**：`002_observability.sql`、`diagnostics.py` `switches/set_switches`
- **不可改变的规则**：默认关；6 表结构
- **实施动作**：建表 + 开关读写
- **完成检查**：`VRC-DIAG-001/002`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

### 9.2.2 `TASK-DIAG-RECORD` · 记录与查询

- **顺序 / 前置项**：2 / `TASK-DIAG-TABLES`
- **文件 / symbol / 构建目标**：`diagnostics.py` `record_trace/trace/traces/capture_snapshot/snapshots_page/record_latency/stats`
- **不可改变的规则**：脱敏/截断、fail-open
- **实施动作**：实现记录与查询原语
- **完成检查**：`VRC-DIAG-002/003/004`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

### 9.2.3 `TASK-DIAG-INJECT` · 注入与流

- **顺序 / 前置项**：3 / `TASK-DIAG-TABLES`
- **文件 / symbol / 构建目标**：`diagnostics.py` `set_injections/enabled_*/stream_wrapper`
- **不可改变的规则**：白名单、单条 enabled、命中确定性
- **实施动作**：实现注入配置与流包装
- **完成检查**：`VRC-DIAG-004`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

## 10. 映射、复核与未决项

<a id="isd-mapping"></a>

### 10.1.1 `MAP-DIAG` · 映射

- **模块 / 原成员 ID**：M006 / `F-DIAG-SWITCH`、`F-DIAG-TRACE`、`F-DIAG-SNAPSHOT`、`F-DIAG-STATS`、`F-DIAG-INJECT`、`F-DIAG-TRACES`、`F-DIAG-STREAM`、`F-DIAG-CLEANUP`
- **唯一来源 / 版本 / selector / hash**：`libdiag` / `0.1.0-draft.1`
- **提供或消费 / backend**：提供 / SQLite
- **实际位置或 Planned 计划位置**：`src/llmtier_v03/diagnostics.py` `DiagnosticsService`
- **验证项**：`VRC-DIAG-001..004`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

### 10.2.1 `SC-DIAG` · 状态一致性复核

- **上游承接状态 / 固定来源**：模块 `libdiag` §15.ISD 声明 `separate`
- **本层派生状态 / 事实依据**：无实际实现/Run；全部 `PLANNED`/`NOT_RUN`
- **§2 Current / Target**：N/A（greenfield）
- **§3 / §5 文件与函数状态**：PLANNED
- **§9 任务 / Actual / Verdict / Run**：PLANNED / NOT_RUN / NOT_RUN / NOT_RUN
- **§10 汇总状态**：PLANNED
- **差异解释 / Owner / 收敛动作**：none

### 10.3.1 `RISK-DIAG-1` · 统计可丢

- **既有台账引用 / 具体缺口 / 反例**：`libdiag` §15.1
- **风险等级 / 判定依据**：Low；统计非账本
- **Owner**：LLMTier
- **最晚关闭阶段 / 截止 Gate**：——
- **阻断范围**：`F-DIAG-STATS`
- **分析 / 决策引用**：`libdiag` §15.1
- **所需输入 / 下一步选择判据**：——
- **解决动作 / 完成条件**：明示非账本语义
- **状态**：Open

### 10.3.2 `OPEN-DIAG-1` · 流注入实现门禁

- **既有台账引用 / 具体缺口 / 反例**：`LT-OPEN-05`
- **风险等级 / 判定依据**：Medium；流注入需改造流式输出
- **Owner**：LLMTier
- **最晚关闭阶段 / 截止 Gate**：实现门禁
- **阻断范围**：`F-DIAG-STREAM`
- **分析 / 决策引用**：机制 M-OBS
- **所需输入 / 下一步选择判据**：确认 `stream_wrapper` 集成方案
- **解决动作 / 完成条件**：集成并提供向量
- **状态**：Open

### 10.4 Metadata 与 coverage 交付检查

metadata 必须包含：`design_object_id=M006`、`implementation_view_of_document_id=libdiag`、`volume_of_document_id=null`；模块设计 `implementation_specification.mode=separate/document_id=libdiag-isd`。

`coverage_mapping` 恰好覆盖十项：`scope`(#isd-scope)、`structure`(#isd-structure)、`data`(#isd-data)、`functions`(#isd-functions)、`algorithms`(#isd-algorithms)、`lifecycle`(#isd-lifecycle)、`resources`(#isd-resources)、`security`(#isd-security)、`persistence`(#isd-persistence)、`verification`(#isd-verification)。

交付前运行 `validate-design <完整设计目录> --check-isd-delivery --json`。
