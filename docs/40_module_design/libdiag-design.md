<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M006 libdiag 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `libdiag` |
| Document Version | `0.1.0-draft.6` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-23` |
| Last Modified Date | `2026-09-23` |
| Template ID | `design.definition` |
| Template Version | `2.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/40_module_design/libdiag-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 单元摘要：为什么存在

| 项目 | 内容 |
|---|---|
| 模块编号 / 正式英文名称 | **M006** / `libdiag` |
| 直属父对象编号 / 名称 | LLMTier 软件系统（本项目无子系统）|
| 父设计 Document ID / 登记位置 | `llmtier-system-design` / 系统设计 §3.2（唯一登记表）|
| 上级系统 / 父单元 | LLMTier 软件系统 |
| 解决的问题 | 调试开关、注入配置、观测记录（上游快照/数据面统计/单请求 trace）的**底层读写**需要一个被多方共用的基础库，避免 M003 与 M005 各自实现一套 |
| 提供的能力 | 开关/注入/快照/trace/统计的存储与查询原语；流注入包装；过期清理；脱敏/截断；全部 fail-open |
| 主要使用者 | **M005 Observability**（查询/呈现/切换）；M003 Inference（记录）；M001（透传写入）|
| 不负责 | 查询与呈现（M005）；HTTP 传输（M001）；推理决策（M003）；页面（M002）|

### 1.1 继承的上级约束与落实方式

#### 1.1.1 `C-OBS-1` · 默认关闭、关闭零开销
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：全部记录原语
- **继承预算或行为保证**：开关关 → 短路不写
- **可自行选择 / 不可改变**：存储可自选；默认关不可变
- **本地落实 / 内部再分配**：I1 开关；§8
- **验证方法与结果 / 证据**：`VRC-DIAG-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.2 `C-OBS-2` · fail-open
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：全部记录/查询
- **继承预算或行为保证**：失败不抛到推理路径
- **可自行选择 / 不可改变**：捕获实现可自选；fail-open 不可变
- **本地落实 / 内部再分配**：I2–I7；§10
- **验证方法与结果 / 证据**：`VRC-DIAG-003`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.3 `C-OBS-3` · 不记录 Secret/凭据/完整正文
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：快照/统计/trace/注入
- **继承预算或行为保证**：只存脱敏字段
- **可自行选择 / 不可改变**：脱敏实现可自选；禁记不可变
- **本地落实 / 内部再分配**：I3/I4 截断；§11
- **验证方法与结果 / 证据**：`VRC-DIAG-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.4 `C-OBS-5` · 能力提供者
- **上级基线与决定状态**：系统设计 §3.2；已采用
- **适用条件**：全部观测能力
- **继承预算或行为保证**：libdiag 提供能力，Observability 呈现
- **可自行选择 / 不可改变**：—（职责边界）
- **本地落实 / 内部再分配**：§5.1、§5.3
- **验证方法与结果 / 证据**：`VRC-DIAG-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M005 一致

## 2. 需求、功能与验收条件

### 2.1 `F-DIAG-SWITCH` · 开关读写
- **上级需求 / Constraint ID**：`C-OBS-1`；机制 M-OBS CAP-OBS-3
- **调用方**：M005
- **输入与前提**：部分更新（`None` 保持）
- **行为**：读写 `snapshots_enabled`/`stats_enabled`（单行表）
- **输出**：开关状态
- **错误与边界**：fail-open
- **验收条件**：关闭时记录短路且零写入

### 2.2 `F-DIAG-TRACE` · trace 记录与查询
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-6
- **调用方**：M001/M003 写；M005 读
- **输入与前提**：`(request_id, stage, detail?, correlation_id?)`
- **行为**：追加 trace 行；按 request_id 聚合 stages + 关联 usage
- **输出**：trace 视图
- **错误与边界**：写失败记 warning；无记录返回空 stages
- **验收条件**：同 request 有序

### 2.3 `F-DIAG-SNAPSHOT` · 快照记录与分页
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-1
- **调用方**：M003 写；M005 读
- **输入与前提**：`(request_id, deployment_id, model, upstream_url, http_status, latency_ms, error_summary)`
- **行为**：写脱敏快照；条件分页查询
- **输出**：快照视图
- **错误与边界**：写失败返回空串、记 warning
- **验收条件**：`upstream_url` 去 query；`error_summary` ≤256B

### 2.4 `F-DIAG-STATS` · 统计聚合与查询
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-2；契约 §5.3（口径）
- **调用方**：M003 写；M005 读
- **输入与前提**：`(deployment_id, model, status_code, latency_ms)`
- **行为**：按小时桶 + 内存聚合（**per-status 计数**）；查询计数 + `status_breakdown{status:count}` + P50/P95/min/max/avg
- **输出**：`{request_count, error_count, status_breakdown:{"200":n,"503":m,"429":k,"upstream_error":x}, latency_p50_ms, latency_p95_ms, latency_min_ms, latency_max_ms, latency_sum_ms}`
- **错误与边界**：缓存满 LRU 淘汰
- **验收条件**：`status_breakdown` 按 HTTP status 分列；可丢、非账本

### 2.5 `F-DIAG-INJECT` · 注入配置读写
- **上级需求 / Constraint ID**：`C-OBS-4`；机制 M-OBS CAP-OBS-5
- **调用方**：M005 写；M003 读
- **输入与前提**：注入项列表（部分更新）
- **行为**：白名单与参数范围校验；按 deployment 持久化；查 enabled——**多启用项仍存储，暴露"下一步要触发的一条"**，优先级 `fault_502 → fault_503 → rate_limit → delay`（流阶段 `stream_terminate → malformed_event`）
- **输出**：注入项列表 / **单条** enabled 项（`enabled_injection` / `enabled_stream_injection`）
- **错误与边界**：非法 → `ApiError(400)`
- **验收条件**：白名单/范围；`UNIQUE(deployment_id, type)`；多 enabled 时返回确定单条

### 2.5.1 `F-DIAG-TRACES` · trace 时间窗查询（G-1）
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-6；Piko 缺口 G-1
- **调用方**：M005 读
- **输入与前提**：`since/until/deployment_id/model/limit/cursor`
- **行为**：按时间窗聚合 `trace_events`（去重 request_id）、快照 join 过滤 deployment/model、与 snapshots 对称分页
- **输出**：`{items:[TraceView], next_cursor, has_more}`
- **错误与边界**：无匹配 → 空 items
- **验收条件**：时间窗/分页稳定。**当前状态：Planned（未实现，见 review G-1）**

### 2.6 `F-DIAG-STREAM` · 流注入包装
- **上级需求 / Constraint ID**：机制 M-OBS（流注入，`LT-OPEN-05`）
- **调用方**：M001（SSE 输出）
- **输入与前提**：`deployment_id`、基础字节流
- **行为**：按 `stream_terminate`/`malformed_event` 在指定事件数后截断/畸形化
- **输出**：包装后的字节流
- **错误与边界**：无注入时透传
- **验收条件**：命中时确定性截断/畸形

### 2.7 `F-DIAG-CLEANUP` · 过期清理
- **上级需求 / Constraint ID**：机制 M-OBS `LT-OPEN-04`
- **调用方**：启动/M005
- **输入与前提**：`days`
- **行为**：删除过期快照/trace
- **输出**：删除数
- **错误与边界**：失败不阻塞启动
- **验收条件**：7 天前删除

## 3. UI、CLI、服务端点或设备操作面

**N/A — 本模块没有直接操作面。** 它是基础层能力库，由 M005/M003/M001 在进程内调用；对外端点由 M001 暴露。Tailoring 依据：系统设计 §3.2 规定 libdiag 提供底层读写、由 Observability 呈现。

## 4. 外部边界与依赖

#### 4.1 `DEP-M005` · Observability（主要消费）
- **角色 / 运行位置 / Owner**：消费方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：`DiagnosticsService.switches/set_switches/snapshots_page/stats/trace/set_injections/injections`
- **契约 authority / 版本 / selector**：本文 §9
- **同步方式 / timeout / 生命周期**：同步；查询请求级
- **不可用或失败影响 / 责任出口**：fail-open

#### 4.2 `DEP-M003/M001` · 记录写入方
- **角色 / 运行位置 / Owner**：消费方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：`record_trace/capture_snapshot/record_latency/get_enabled_injections/stream_wrapper`
- **契约 authority / 版本 / selector**：本文 §9；机制 M-OBS §14.4 `R-OBS-03/04`
- **同步方式 / timeout / 生命周期**：同步、尽力而为
- **不可用或失败影响 / 责任出口**：记 warning，不改推理

#### 4.3 `DEP-M007` · util（存储）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：`Store.one/all/transaction/connection`
- **本模块提供**：—
- **契约 authority / 版本 / selector**：机制 M-OBS §14.4 `R-OBS-06`
- **同步方式 / timeout / 生命周期**：同步
- **不可用或失败影响 / 责任出口**：记录失败 → warning

#### 4.4 `DEP-M008` · log（warning）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：脱敏日志写入（`_warn`）
- **本模块提供**：—
- **契约 authority / 版本 / selector**：M008 §9
- **同步方式 / timeout / 生命周期**：同步、尽力而为
- **不可用或失败影响 / 责任出口**：静默

## 5. 内部结构与实现位置

### 5.1 内部组成

#### 5.1.0 `I0` · 门面组合
- **职责与非职责**：组合各功能模块为 `DiagnosticsService` 稳定方法面；不含功能逻辑
- **输入、处理与输出**：门面调用 → 委托到对应功能模块；`_warn` 统一 fail-open 告警
- **协作对象**：I1–I8（全部）
- **文件 / symbol / 实现状态**：`diagnostics.py` `DiagnosticsService`；Implemented
- **拆分依据与替代方案代价**：功能各自成文件，门面是唯一组合点（供 M001/M003/M005 消费）

#### 5.1.1 `I1` · 开关存储
- **职责与非职责**：读写 `diagnostic_settings` 单行；不做记录
- **输入、处理与输出**：部分更新 → 状态
- **协作对象**：I2–I6（开关判定）
- **文件 / symbol / 实现状态**：`settings.py` `switches/set_switches`；Implemented
- **拆分依据与替代方案代价**：开关是共用状态，集中一处

#### 5.1.2 `I2` · trace 记录
- **职责与非职责**：`trace_events` 追加与按 request 聚合；不做快照/统计
- **输入、处理与输出**：`(request_id, stage, detail, correlation_id)` → 行/视图
- **协作对象**：I1（开关）、M007
- **文件 / symbol / 实现状态**：`traces.py` `record_trace/trace`；Implemented
- **拆分依据与替代方案代价**：trace 与快照分表，粒度不同

#### 5.1.3 `I3` · 快照记录
- **职责与非职责**：`diagnostic_snapshots` 写入与分页；脱敏/截断
- **输入、处理与输出**：快照字段 → 行
- **协作对象**：I1、M007
- **文件 / symbol / 实现状态**：`snapshots.py` `capture_snapshot/snapshots_page`；Implemented
- **拆分依据与替代方案代价**：快照带外部证据（URL/status/latency）

#### 5.1.4 `I4` · 统计聚合
- **职责与非职责**：小时桶 + 内存缓存 + 百分位；可丢
- **输入、处理与输出**：`(deployment_id, model, status_code, latency_ms)` → 聚合
- **协作对象**：I1
- **文件 / symbol / 实现状态**：`stats.py` `record_latency/stats`、`common.py` `percentile/hour_of`；Implemented
- **拆分依据与替代方案代价**：内存聚合避免每请求写库

#### 5.1.5 `I5` · 注入配置
- **职责与非职责**：白名单/范围校验、按 deployment 持久化、查 enabled
- **输入、处理与输出**：注入项 → 规范化行 / enabled 项
- **协作对象**：I6、M007
- **文件 / symbol / 实现状态**：`injections.py` `set_injections/injections/enabled_injection/enabled_stream_injection`；Implemented
- **拆分依据与替代方案代价**：注入类型固定 6 种

#### 5.1.6 `I6` · 流注入包装
- **职责与非职责**：按 stream 注入截断/畸形；不改变无注入流
- **输入、处理与输出**：`(deployment_id, base_stream)` → 字节流
- **协作对象**：I5、M001
- **文件 / symbol / 实现状态**：`stream.py` `stream_wrapper`；Implemented
- **拆分依据与替代方案代价**：流注入需在传输层包装（`LT-OPEN-05`）

#### 5.1.7 `I7` · 过期清理
- **职责与非职责**：删除过期快照/trace/统计；不删注入/开关
- **输入、处理与输出**：`days` → 删除数
- **协作对象**：M007
- **文件 / symbol / 实现状态**：`retention.py` `cleanup`；Implemented
- **拆分依据与替代方案代价**：保留期 7 天

#### 5.1.8 `I8` · 共享 helper
- **职责与非职责**：纯函数（时间/分位）；无状态、不触库
- **输入、处理与输出**：时间戳/分位输入 → 值
- **协作对象**：I2–I4、I7
- **文件 / symbol / 实现状态**：`common.py` `now/hour_of/iso/percentile`；Implemented
- **拆分依据与替代方案代价**：跨功能共用，集中避免重复实现

### 5.2 内部调用过程

#### 5.2.1 `CALL-DIAG-RECORD` · 一次记录（trace/快照/统计）
- **入口与调用上下文**：M003/M001 请求路径
- **调用链**：`record_trace`/`capture_snapshot`/`record_latency` → 开关判定（I1）→ 写 `Store`
- **逐步传递的数据**：`(request_id, stage, detail…)` → 行
- **返回、异常与清理**：失败捕获 → `_warn`，不抛
- **对应流程 / 接口 / 验证**：§7 P-DIAG-RECORD / `VRC-DIAG-002/003`

#### 5.2.2 `CALL-DIAG-INJECT` · 一次注入包装
- **入口与调用上下文**：M001 SSE 输出
- **调用链**：`stream_wrapper(deployment_id, base)` → `enabled_stream_injection` → 逐块判定截断/畸形
- **逐步传递的数据**：字节块 → 字节块
- **返回、异常与清理**：无注入时透传
- **对应流程 / 接口 / 验证**：§7 P-DIAG-STREAM / `VRC-DIAG-004`

### 5.3 文件间接口契约

> 采用**接口固定格式**（功能 / 输入 / 输出 / 返回值 / 统计 · 日志 / 数据库）。覆盖**跨模块文件**与**模块内文件 ↔ 文件**调用；逐方法细节见 §9.2，数据结构见 §9.1。

#### 5.3.1 `IF-DIAG-01` · `src/http_api/app.py` → `src/libdiag/diagnostics.py`（查询/开关/注入）
- **功能**：M005 诊断路由经门面做查询、开关切换与注入配置读写。
- **输入**：
  - `switches()` / `set_switches(snapshots_enabled?, stats_enabled?)`｜开关
  - `snapshots_page(...)` / `stats(...)` / `trace(...)` / `traces(...)` / `injections(...)` / `set_injections(...)`｜查询 / 写配置
- **输出**：`SwitchState` / `SnapshotPage` / `StatsView` / `TraceView` / `InjectionView[]`（§9.1）。
- **返回值**：见 §9.2；`400`/`404` 由门面透传。
- **统计 · 日志**：无。
- **数据库**：见 §9.2 各接口（查询只读；`set_switches`/`set_injections` 写）。

#### 5.3.2 `IF-DIAG-02` · `src/inference/responses.py` → `src/libdiag/diagnostics.py`（记录）
- **功能**：推理路径经门面记录 trace / 快照 / 统计。
- **输入**：`record_trace(...)` / `capture_snapshot(...)` / `record_latency(...)`（逐参数见 §9.2）。
- **输出**：无 / `snap_id`。
- **返回值**：`None` / `snap_id` / `null`；**fail-open 不抛**。
- **统计 · 日志**：写失败记 warning（`capture_failed`）。
- **数据库**：见 §9.2（`INSERT trace_events`/`diagnostic_snapshots`；`UPSERT data_plane_stats`）。

#### 5.3.3 `IF-DIAG-03` · `src/http_api/app.py` → `src/libdiag/diagnostics.py`（流注入）
- **功能**：M001 SSE 输出经 `stream_wrapper` 包装。
- **输入**：`stream_wrapper(deployment_id, base_stream)`。
- **输出**：`Iterable[bytes]`。
- **返回值**：生成器（透传 / 截断 / 畸形）。
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_injections`。

#### 5.3.4 `IF-DIAG-INT` · 模块内文件间接口（门面 ↔ 功能 ↔ helper）
- **功能**：门面组合各功能；功能间仅少量正交依赖。
- **输入**：
  - `diagnostics.py`（门面）→ `settings` / `traces` / `snapshots` / `stats` / `injections` / `retention` / `stream`
  - `snapshots.py` · `stats.py` → `settings.py`：`switches()`
  - `stream.py` → `injections.py`：`enabled_stream_injection()`
  - `settings` / `traces` / `snapshots` / `stats` / `retention.py` → `common.py`：`now` / `hour_of` / `iso` / `percentile`
- **输出**：功能返回值原样透传。
- **返回值**：`ApiError` / `sqlite3.Error` 冒泡到门面。
- **统计 · 日志**：门面 `_warn` 统一 fail-open。
- **数据库**：各功能自持；门面不直连。

### 5.4 服务提供方式（条件适用）

- **运行载体与入口**：N/A + 依据 —— 嵌入式库，无独立 server
- **并发/线程模型**：N/A + 依据 —— 使用调用方线程；统计聚合内部有锁
- **初始化、Ready、生效与停止**：随 `Application` 构造；`cleanup(7)` 启动时调用
- **宿主装配、失败和资源回收责任**：由 M001/启动装配；失败 fail-open

### 5.5 依赖方向

- **允许方向**：{M001, M003, M005} → M006 → {M007, M008}
- **禁止方向与原因**：M006 不得调用 M005/M003（能力库不回调业务）；不直连 HTTP
- **循环/越层检查**：feature 模块只 import `store`/`http_api.errors`；门面 `diagnostics.py` 组合各 feature；均不 import `app`/`responses`
- **变更影响**：记录签名变更影响 M001/M003 集成点

## 6. 数据模型、状态与 ownership

> 采用**数据结构固定格式**（定义 / 字段 / 不变量 / 来源）。持久表 authority = `util/migrations/002_observability.sql`（由 M007 `migrate()` 执行）。

#### 6.1 `diagnostic_settings`
- **定义**：诊断全局开关的单行状态。
- **字段**：
  - `singleton`：`int` PK｜恒 `1`｜单行哨兵
  - `snapshots_enabled`：`int`｜`0`/`1`，默认 `0`｜快照开关
  - `stats_enabled`：`int`｜`0`/`1`，默认 `0`｜统计开关
- **不变量**：恒单行（`singleton=1`）；两开关独立。
- **来源**：`util/migrations/002_observability.sql`

#### 6.2 `diagnostic_snapshots`
- **定义**：上游调用快照（脱敏，保留 7 天）。
- **字段**：
  - `id`：`TEXT` PK｜`snap_*`｜快照 ID
  - `request_id`：`TEXT`｜非空｜请求标识
  - `captured_at`：`TEXT`｜RFC3339 ms｜捕获时间
  - `upstream_url`：`TEXT`｜去 query｜上游 URL
  - `backend_model`：`TEXT?`｜非空或 `null`｜上游模型
  - `http_status`：`INTEGER?`｜100–599｜HTTP 状态
  - `latency_ms`：`REAL?`｜≥0｜延迟
  - `error_summary`：`TEXT?`｜≤256 字节｜错误摘要
  - `model`：`TEXT?`｜非空或 `null`｜tier 名
  - `deployment_id`：`TEXT?`｜非空或 `null`｜部署 ID
  - `snapshot_type`：`TEXT`｜`upstream`/`error`，默认 `upstream`｜类型
- **不变量**：`upstream ⇒ http_status` 非空；`error ⇒ http_status` 空；`upstream_url` 去 query；`error_summary` ≤256B。
- **来源**：`util/migrations/002_observability.sql`

#### 6.3 `data_plane_stats`
- **定义**：小时桶 × deployment × model × status 的请求/错误计数（可丢，非账本）。
- **字段**：
  - `stat_hour`：`TEXT` PK 之一｜`YYYY-MM-DDTHH`｜小时桶
  - `deployment_id`：`TEXT` PK 之一｜非空或 `null`｜部署 ID
  - `model`：`TEXT` PK 之一｜非空或 `null`｜tier 名
  - `status`：`TEXT` PK 之一｜状态码或 `upstream_error`｜状态
  - `request_count`：`INTEGER`｜≥0，默认 `0`｜请求计数
  - `error_count`：`INTEGER`｜≥0，默认 `0`｜错误计数
  - `updated_at`：`TEXT`｜RFC3339 ms｜更新时间
- **不变量**：PK `(stat_hour,deployment_id,model,status)`；累加 upsert；可丢。
- **来源**：`util/migrations/002_observability.sql`

#### 6.4 `data_plane_latency_samples`
- **定义**：延迟样本（用于分位）。
- **字段**：
  - `stat_hour`：`TEXT`｜`YYYY-MM-DDTHH`｜小时桶
  - `deployment_id`：`TEXT?`｜非空或 `null`｜部署 ID
  - `model`：`TEXT?`｜非空或 `null`｜tier 名
  - `latency_ms`：`REAL` NOT NULL｜≥0｜延迟
  - `created_at`：`TEXT`｜RFC3339 ms｜写入时间
- **不变量**：只追加；可丢。
- **来源**：`util/migrations/002_observability.sql`

#### 6.5 `diagnostic_injections`
- **定义**：按 deployment 的故障注入配置。
- **字段**：
  - `id`：`TEXT` PK｜`inj_*`｜注入 ID
  - `deployment_id`：`TEXT`｜非空｜部署 ID
  - `injection_type`：`TEXT`｜6 种之一｜注入类型
  - `enabled`：`INTEGER`｜`0`/`1`，默认 `0`｜启用标志
  - `fault_status`：`INTEGER?`｜`502`/`503`｜故障状态
  - `fault_body`：`TEXT?`｜≤512 字节｜故障正文
  - `delay_ms`：`INTEGER?`｜0–60000｜延迟
  - `retry_after_sec`：`INTEGER?`｜0–300｜`Retry-After`
  - `stream_terminate_after_events`：`INTEGER?`｜1–10000｜截断点
  - `malformed_after_events`：`INTEGER?`｜0–10000｜畸形点
  - `malformed_event_type`：`TEXT?`｜`invalid_json`/`unknown_event_type`｜畸形类型
  - `updated_at`：`TEXT`｜RFC3339 ms｜更新时间
- **不变量**：`UNIQUE(deployment_id,injection_type)`；6 种类型白名单；各类型配置字段范围见上。
- **来源**：`util/migrations/002_observability.sql`

#### 6.6 `trace_events`
- **定义**：请求 trace 阶段事件（保留 7 天）。
- **字段**：
  - `id`：`TEXT` PK｜`tev_*`｜事件 ID
  - `request_id`：`TEXT`｜非空｜请求标识
  - `stage`：`TEXT`｜∈ §9.1.2 集合｜阶段名
  - `stage_timestamp`：`TEXT`｜RFC3339 ms｜阶段时间
  - `detail`：`TEXT?`｜JSON（脱敏）｜阶段上下文
  - `correlation_id`：`TEXT?`｜非空或 `null`｜关联标识
  - `created_at`：`TEXT`｜RFC3339 ms｜写入时间
- **不变量**：只追加；同 request 按 `stage_timestamp` 有序；保留 7 天。
- **来源**：`util/migrations/002_observability.sql`

## 7. 主流程与数据流

**内部流程正文**：记录路径由 M003/M001 调用记录原语：先判开关（I1），关闭即短路；开启则写 `Store`（trace/snapshot）或更新内存聚合（stats），失败捕获后 `_warn`。流注入路径由 M001 用 `stream_wrapper` 包装 SSE 字节流，按 enabled 注入截断/畸形。清理在启动时按 7 天删除。

#### 7.1 `P-DIAG-RECORD` · 记录
- **触发/适用条件**：推理路径各阶段
- **图与正文位置**：§5.2.1；机制 M-OBS §6
- **正常出口**：行写入 / 聚合更新
- **异常出口**：`_warn`（不阻断）

#### 7.2 `P-DIAG-STREAM` · 流注入
- **触发/适用条件**：SSE 输出且有 stream 注入
- **图与正文位置**：§5.2.2
- **正常出口**：截断/畸形字节流
- **异常出口**：无注入 → 透传

## 8. 关键算法与业务规则

#### 8.1 `RULE-DIAG-SWITCH` · 开关短路
- **输入前提 / 适用条件**：任意记录
- **算法 / 规则 / 选择依据**：`snapshots_enabled`/`stats_enabled` 关 → 直接返回，不写
- **结果 / 不变量 / 边界**：关闭零写入（C-OBS-1）
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：存储可自选；短路不可变
- **具体输入推演 / 验证项**：关→无新行；`VRC-DIAG-001`

#### 8.2 `RULE-DIAG-TRUNC` · 脱敏与截断
- **输入前提 / 适用条件**：快照写入
- **算法 / 规则 / 选择依据**：`upstream_url` 去 query；`error_summary` 截断 256B（UTF-8 安全）
- **结果 / 不变量 / 边界**：只存脱敏字段（C-OBS-3）
- **复杂度 / 资源限制**：O(len)
- **允许替换范围 / 不可改变保证**：实现可自选；禁记不可变
- **具体输入推演 / 验证项**：`?key=` 被移除；`VRC-DIAG-002`

#### 8.3 `RULE-DIAG-PCTL` · 百分位与分桶
- **输入前提 / 适用条件**：统计查询
- **算法 / 规则 / 选择依据**：按 `hour_of` 分桶；`_percentile(sorted_values, p)` 计算 P50/P95
- **结果 / 不变量 / 边界**：口径与负载写入一致
- **复杂度 / 资源限制**：O(n log n) 排序
- **允许替换范围 / 不可改变保证**：实现可自选；口径不可变
- **具体输入推演 / 验证项**：给定样本 P50/P95 正确；`VRC-DIAG-002`

#### 8.4 `RULE-DIAG-INJECT` · 注入校验与判定
- **输入前提 / 适用条件**：注入写入 / 流包装
- **算法 / 规则 / 选择依据**：`injection_type` 白名单；各 type 参数范围；`stream_terminate_after_events`/`malformed_after_events` 计数触发
- **结果 / 不变量 / 边界**：非法 → 400；命中确定性
- **复杂度 / 资源限制**：O(items)/O(chunks)
- **允许替换范围 / 不可改变保证**：实现可自选；白名单/确定触发不可变
- **具体输入推演 / 验证项**：`delay_ms=2000` 生效；`VRC-DIAG-004`

## 9. 接口与机器契约

对外无端点；以下为**供其他模块（M001/M003/M005）做设计、实现与测试用例**的接口契约。

**固定格式约定**（数据结构与接口分开描述，避免复用类型被逐接口重复）：

- **数据结构**固定 4 段：`定义` / `字段`（逐字段一行：`` `名称` ``：`` `类型` ``｜必填性｜范围·枚举｜说明）/ `不变量` / `来源`。
- **接口**固定 6 段：`功能` / `输入`（逐参数一行：`` `名称: 类型` ``｜必填·默认｜范围｜说明）/ `输出`（数据结构 ID）/ `返回值`（每条件一行）/ `统计 · 日志` / `数据库`。
- 时间一律 RFC3339（UTC，毫秒）；`?` 表示可空。

### 9.1 共享数据结构

#### 9.1.1 `SwitchState`
- **定义**：全局诊断开关状态；供记录前判定与 M005 呈现。
- **字段**：
  - `snapshots_enabled`：`bool`｜必填｜`false`/`true`（默认 `false`）｜快照记录总开关
  - `stats_enabled`：`bool`｜必填｜`false`/`true`（默认 `false`）｜统计记录总开关
- **不变量**：两字段互相独立；恒取自 `diagnostic_settings` 单行（`singleton=1`）。
- **来源**：`src/libdiag/settings.py`（定义并产出）

#### 9.1.2 `TraceStage`
- **定义**：单个 trace 阶段。
- **字段**：
  - `stage`：`str`｜必填｜∈ {`received`,`validated`,`routed`,`upstream_started`,`upstream_ended`,`completed`,`aborted`}｜阶段名（≤64；调用方约定，代码不强制）
  - `timestamp`：`str`｜必填｜RFC3339 ms｜阶段发生时间
  - `detail`：`object?`｜可空｜任意 JSON（脱敏后）｜阶段附加上下文
- **不变量**：`stages` 内按 `timestamp` 升序。
- **来源**：`src/libdiag/traces.py`（定义并产出）

#### 9.1.3 `UsageView`
- **定义**：某请求的用量视图（只读账本 head）。
- **字段**：
  - `record_version`：`int`｜必填｜≥1｜账本版本号
  - `is_final`：`bool`｜必填｜`false`/`true`｜是否终态
  - `model`：`str`｜必填｜非空｜tier 名
  - `input_tokens`：`int?`｜可空｜≥0｜输入 token
  - `output_tokens`：`int?`｜可空｜≥0｜输出 token
  - `total_tokens`：`int?`｜可空｜≥0｜合计 token
  - `measurement_status`：`str`｜必填｜`measured`/`unknown`｜测量状态
  - `source`：`str`｜必填｜非空｜来源（`provider`/`injected`/`unavailable`…）
- **不变量**：`measurement_status=measured` ⇒ 三个 token 字段非空；`unknown` ⇒ 全空（**不补零**）。
- **来源**：`src/libdiag/traces.py`（定义并产出）

#### 9.1.4 `TraceView`
- **定义**：单请求的完整 trace 视图。
- **字段**：
  - `request_id`：`str`｜必填｜非空｜请求标识
  - `correlation_id`：`str?`｜可空｜非空或 `null`｜外部关联标识（`X-Correlation-ID`/`traceparent`）
  - `stages`：`TraceStage[]`｜必填｜长度 ≥1｜阶段序列（§9.1.2）
  - `snapshot`：`SnapshotView?`｜可空｜—｜该请求最近一条快照（§9.1.6）
  - `usage`：`UsageView?`｜可空｜—｜该请求用量（§9.1.3）
- **不变量**：`stages` 非空；`snapshot`/`usage` 允许为 `null`。
- **来源**：`src/libdiag/traces.py`（定义并产出）

#### 9.1.5 `TracePage`
- **定义**：trace 时间线分页。
- **字段**：
  - `items`：`TraceView[]`｜必填｜长度 ≤ `limit`｜页内 trace
  - `next_cursor`：`str?`｜可空｜`first_ts|request_id`｜下一页游标
  - `has_more`：`bool`｜必填｜`false`/`true`｜是否还有下一页
- **不变量**：`has_more=false` ⇒ `next_cursor=null`。
- **来源**：`src/libdiag/traces.py`（定义并产出）

#### 9.1.6 `SnapshotView`
- **定义**：一次上游调用的快照视图。
- **字段**：
  - `id`：`str`｜必填｜`snap_*`｜快照 ID
  - `request_id`：`str`｜必填｜非空｜请求标识
  - `captured_at`：`str`｜必填｜RFC3339 ms｜捕获时间
  - `upstream_url`：`str`｜必填｜去 query｜上游 URL
  - `backend_model`：`str?`｜可空｜非空或 `null`｜上游模型名
  - `http_status`：`int?`｜可空｜100–599｜HTTP 状态（error 类快照为空）
  - `latency_ms`：`float?`｜可空｜≥0｜端到端延迟
  - `error_summary`：`str?`｜可空｜≤256 字节｜错误摘要（脱敏）
  - `model`：`str?`｜可空｜非空或 `null`｜tier 名
  - `deployment_id`：`str?`｜可空｜非空或 `null`｜部署 ID
  - `snapshot_type`：`str`｜必填｜`upstream`/`error`｜快照类型
- **不变量**：`snapshot_type=upstream` ⇒ `http_status` 非空；`=error` ⇒ `http_status` 空。
- **来源**：`src/libdiag/snapshots.py`（定义并产出）

#### 9.1.7 `SnapshotPage`
- **定义**：快照分页。
- **字段**：
  - `items`：`SnapshotView[]`｜必填｜长度 ≤ `limit`｜页内快照
  - `next_cursor`：`str?`｜可空｜末条 `id`｜下一页游标
  - `has_more`：`bool`｜必填｜`false`/`true`｜是否还有下一页
- **不变量**：`has_more=false` ⇒ `next_cursor=null`。
- **来源**：`src/libdiag/snapshots.py`（定义并产出）

#### 9.1.8 `StatsWindow`
- **定义**：单（小时桶 × deployment × model）聚合。
- **字段**：
  - `stat_hour`：`str`｜必填｜`YYYY-MM-DDTHH`（UTC）｜小时桶
  - `deployment_id`：`str?`｜可空｜非空或 `null`｜部署 ID
  - `model`：`str?`｜可空｜非空或 `null`｜tier 名
  - `status_breakdown`：`object<str,int>`｜必填｜键为状态码或 `upstream_error`｜各状态计数
  - `error_4xx_count`：`int`｜必填｜≥0｜4xx 计数（由 breakdown 派生）
  - `error_5xx_count`：`int`｜必填｜≥0｜5xx + `upstream_error` 计数（派生）
  - `request_count`：`int`｜必填｜≥0｜总请求数
  - `error_count`：`int`｜必填｜≥0｜总错误数
  - `latency_p50_ms`/`latency_p95_ms`/`latency_min_ms`/`latency_max_ms`：`float?`｜可空｜≥0｜延迟分位/极值
  - `latency_sum_ms`：`float`｜必填｜≥0｜延迟和（无样本为 `0`）
- **不变量**：`error_4xx_count`/`error_5xx_count` 与 `status_breakdown` 一致；无延迟样本 ⇒ 百分位 `null`、`latency_sum_ms=0`。
- **来源**：`src/libdiag/stats.py`（定义并产出）

#### 9.1.9 `StatsView`
- **定义**：统计视图。
- **字段**：
  - `windows`：`StatsWindow[]`｜必填｜可为 `[]`｜聚合桶列表（§9.1.8）
- **不变量**：按 `stat_hour` 升序。
- **来源**：`src/libdiag/stats.py`（定义并产出）

#### 9.1.10 `EnabledInjection`
- **定义**：当前命中且启用的注入（`diagnostic_injections` 行）。
- **字段**：
  - `id`：`str`｜必填｜`inj_*`｜注入 ID
  - `deployment_id`：`str`｜必填｜非空｜部署 ID
  - `injection_type`：`str`｜必填｜6 种之一｜注入类型
  - `fault_status`：`int?`｜可空｜`502`/`503`｜故障状态码（`fault_*`）
  - `fault_body`：`str?`｜可空｜≤512 字节｜故障正文（`fault_*`）
  - `delay_ms`：`int?`｜可空｜0–60000｜延迟（`delay`）
  - `retry_after_sec`：`int?`｜可空｜0–300｜`Retry-After`（`rate_limit`）
  - `stream_terminate_after_events`：`int?`｜可空｜1–10000｜截断点（`stream_terminate`）
  - `malformed_after_events`：`int?`｜可空｜0–10000｜畸形点（`malformed_event`）
  - `malformed_event_type`：`str?`｜可空｜`invalid_json`/`unknown_event_type`｜畸形类型
  - `enabled`：`int`｜必填｜恒 `1`｜启用标志
  - `updated_at`：`str`｜必填｜RFC3339 ms｜更新时间
- **不变量**：仅对应类型的配置字段非空，其余为 `null`；查询只返回 `enabled=1`。
- **来源**：`src/libdiag/injections.py`（定义并产出）

#### 9.1.11 `InjectionView`
- **定义**：一条注入配置视图（含 `config`）。
- **字段**：
  - `id`：`str`｜必填｜`inj_*`｜注入 ID
  - `deployment_id`：`str`｜必填｜非空｜部署 ID
  - `type`：`str`｜必填｜6 种之一｜注入类型
  - `config`：`object`｜必填｜按类型（见 §9.1.10 各配置字段）｜注入参数
  - `enabled`：`bool`｜必填｜`false`/`true`｜是否启用
  - `updated_at`：`str`｜必填｜RFC3339 ms｜更新时间
- **不变量**：`config` 字段集合与 `type` 一致。
- **来源**：`src/libdiag/injections.py`（定义并产出）

### 9.2 接口规格

> 每个接口固定 6 段：`功能` / `输入`（逐参数）/ `输出` / `返回值`（每条件一行）/ `统计 · 日志` / `数据库`。

#### 9.2.1 `IF-LIBDIAG-SWITCH` · 开关（`settings.py`）

##### `switches()`
- **功能**：读取全局开关状态；供 M005 呈现、M003/M001 记录前判定。
- **输入**：无。
- **输出**：`SwitchState`（§9.1.1）。
- **返回值**：始终 → `SwitchState`（无错误分支）。
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_settings`（`singleton=1`），不改数据。

##### `set_switches(snapshots_enabled=None, stats_enabled=None, conn=None)`
- **功能**：部分更新全局开关。
- **输入**：
  - `snapshots_enabled: bool?`｜可选，默认 `null`（不变）｜`false`/`true`｜快照开关
  - `stats_enabled: bool?`｜可选，默认 `null`（不变）｜`false`/`true`｜统计开关
  - `conn: Connection?`｜可选，默认 `null`（自开事务）｜—｜调用方事务接入
- **输出**：更新后的 `SwitchState`（§9.1.1）。
- **返回值**：
  - 成功 → `SwitchState`
  - 参数非 `bool`（且非 `null`）→ `ApiError(400, "invalid_request")`（`param`=字段名）
- **统计 · 日志**：无。
- **数据库**：`UPDATE diagnostic_settings SET snapshots_enabled,stats_enabled WHERE singleton=1`；`conn` 非空时并入调用方事务。

#### 9.2.2 `IF-LIBDIAG-RECORD` · 记录（`traces.py`/`snapshots.py`/`stats.py`）

##### `record_trace(request_id, stage, detail=None, correlation_id=None)`
- **功能**：追加一个 trace 阶段；**fail-open**（失败不影响数据面）。
- **输入**：
  - `request_id: str`｜必填｜非空｜请求标识
  - `stage: str`｜必填｜∈ §9.1.2 集合｜阶段名
  - `detail: object?`｜可选，默认 `null`｜任意 JSON（脱敏）｜阶段上下文
  - `correlation_id: str?`｜可选，默认 `null`｜非空或 `null`｜关联标识
- **输出**：无。
- **返回值**：恒无返回值（`None`）；写失败**不抛**，改记 warning。
- **统计 · 日志**：写失败记 `OperationalLog(warning, diagnostics, capture_failed)`。
- **数据库**：`INSERT trace_events`（`id=tev_*`、`request_id`、`stage`、`stage_timestamp=now`、`detail=JSON`、`correlation_id`、`created_at=now`）。

##### `capture_snapshot(request_id, deployment_id, model, upstream_url, backend_model, http_status, latency_ms, error_summary)`
- **功能**：记录一次上游调用快照（受 `snapshots_enabled` 控制）；**fail-open**。
- **输入**：
  - `request_id: str`｜必填｜非空｜请求标识
  - `deployment_id: str?`｜必填位，可空｜非空或 `null`｜部署 ID
  - `model: str?`｜必填位，可空｜非空或 `null`｜tier 名
  - `upstream_url: str`｜必填｜去 query｜上游 URL
  - `backend_model: str?`｜必填位，可空｜非空或 `null`｜上游模型名
  - `http_status: int?`｜必填位，可空｜100–599｜HTTP 状态（`null` → error 类）
  - `latency_ms: float?`｜必填位，可空｜≥0｜端到端延迟
  - `error_summary: str?`｜必填位，可空｜≤256 字节（超出截断）｜错误摘要
- **输出**：`snap_id: str`（新建快照 ID）。
- **返回值**：
  - `snapshots_enabled=true` 且写成功 → `snap_id`
  - `snapshots_enabled=false` → `null`
  - 写失败 → `null`（不抛）
- **统计 · 日志**：写失败记 warning（`capture_failed`）。
- **数据库**：`INSERT diagnostic_snapshots`（`snapshot_type=upstream` 当 `http_status` 非空，否则 `error`）。

##### `record_latency(deployment_id, model, status_code, latency_ms)`
- **功能**：记录一次请求的小时桶统计与延迟样本（受 `stats_enabled` 控制）；**fail-open**。
- **输入**：
  - `deployment_id: str?`｜必填位，可空｜非空或 `null`｜部署 ID
  - `model: str?`｜必填位，可空｜非空或 `null`｜tier 名
  - `status_code: int?`｜必填位，可空｜100–599；`null` 或 <100 → 记 `upstream_error`｜HTTP 状态
  - `latency_ms: float?`｜必填位，可空｜≥0｜延迟（`null` 只计请求不计延迟）
- **输出**：无。
- **返回值**：恒无返回值；写失败不抛。
- **统计 · 日志**：写失败记 warning；`status_code≥400` 或 `upstream_error` ⇒ `error_count+1`。
- **数据库**：`UPSERT data_plane_stats`（`request_count`/`error_count` 累加）；`latency_ms` 非空时 `INSERT data_plane_latency_samples`。

#### 9.2.3 `IF-LIBDIAG-QUERY` · 查询（`traces.py`/`snapshots.py`/`stats.py`）

##### `trace(request_id)`
- **功能**：按 `request_id` 返回完整 trace 视图（阶段 + 最近快照 + 用量）。
- **输入**：
  - `request_id: str`｜必填｜非空｜请求标识
- **输出**：`TraceView`（§9.1.4）。
- **返回值**：
  - 有记录 → `TraceView`
  - 无记录 → `ApiError(404, "not_found")`
- **统计 · 日志**：无。
- **数据库**：只读 `trace_events`/`diagnostic_snapshots`/`usage_record_versions`。

##### `traces(since=None, until=None, deployment_id=None, model=None, limit=50, cursor=None)`
- **功能**：时间窗内按请求去重的时间线分页（G-1）。
- **输入**：
  - `since/until: str?`｜可选，默认 `null`（不限）｜RFC3339｜时间窗
  - `deployment_id/model: str?`｜可选，默认 `null`｜非空或 `null`｜经快照过滤
  - `limit: int`｜可选，默认 `50`｜夹到 `[1,500]`｜页大小
  - `cursor: str?`｜可选，默认 `null`｜`first_ts|request_id`｜续页游标
- **输出**：`TracePage`（§9.1.5）。
- **返回值**：
  - 始终 → `TracePage`
  - 无匹配 → `items=[]`、`has_more=false`
- **统计 · 日志**：无。
- **数据库**：只读 `trace_events`（+`diagnostic_snapshots` 过滤）。

##### `snapshots_page(since=None, until=None, deployment_id=None, model=None, limit=50, cursor=None)`
- **功能**：快照时间窗分页。
- **输入**：
  - `since/until: str?`｜可选，默认 `null`｜RFC3339｜时间窗
  - `deployment_id/model: str?`｜可选，默认 `null`｜非空或 `null`｜过滤
  - `limit: int`｜可选，默认 `50`｜夹到 `[1,500]`｜页大小
  - `cursor: str?`｜可选，默认 `null`｜末条 `id`｜续页游标
- **输出**：`SnapshotPage`（§9.1.7）。
- **返回值**：始终 → `SnapshotPage`（无匹配 `items=[]`）。
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_snapshots`。

##### `stats(since, until, deployment_id=None, model=None)`
- **功能**：按小时桶聚合统计视图。
- **输入**：
  - `since/until: str`｜必填｜RFC3339（取前 13 字符做小时）｜时间窗
  - `deployment_id/model: str?`｜可选，默认 `null`｜非空或 `null`｜过滤
- **输出**：`StatsView`（§9.1.9）。
- **返回值**：
  - 始终 → `StatsView`
  - 无数据 → `windows=[]`
- **统计 · 日志**：无。
- **数据库**：只读 `data_plane_stats` + `data_plane_latency_samples`。

#### 9.2.4 `IF-LIBDIAG-INJECT` · 注入（`injections.py`/`stream.py`）

##### `set_injections(deployment_id, actor_items, conn=None)`
- **功能**：校验并 upsert 某 deployment 的注入项；返回全量视图。
- **输入**：
  - `deployment_id: str`｜必填｜非空｜部署 ID
  - `actor_items: object[]`｜必填｜每项含 `type`（6 种）+ `config` + `enabled`｜注入项数组
  - `conn: Connection?`｜可选，默认 `null`（自开事务）｜—｜调用方事务接入
- **输出**：`InjectionView[]`（§9.1.11）。
- **返回值**：
  - 成功 → `InjectionView[]`
  - 类型非法 / 缺字段 / 越界 → `ApiError(400, "invalid_injection")`
  - 非列表 → `ApiError(400, "invalid_injection")`
  - 未知 deployment → `ApiError(404, "not_found")`
- **统计 · 日志**：无。
- **数据库**：`UPSERT diagnostic_injections`（键 `(deployment_id,injection_type)`；`fault_502`→`fault_status=502`，`fault_503`→`503`）。

##### `injections(deployment_id)`
- **功能**：列出某 deployment 的全部注入项。
- **输入**：
  - `deployment_id: str`｜必填｜非空｜部署 ID
- **输出**：`InjectionView[]`（§9.1.11）。
- **返回值**：
  - 成功 → 列表（可 `[]`）
  - 未知 deployment → `ApiError(404, "not_found")`
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_injections`。

##### `enabled_injection(deployment_id)`
- **功能**：取启用中的**前置阶段**注入（优先级 `fault_502→fault_503→rate_limit→delay`）。
- **输入**：
  - `deployment_id: str`｜必填｜非空｜部署 ID
- **输出**：`EnabledInjection?`（§9.1.10）。
- **返回值**：
  - 命中 → `EnabledInjection`
  - 无 → `null`
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_injections`（`enabled=1`）。

##### `enabled_stream_injection(deployment_id)`
- **功能**：取启用中的**流阶段**注入（`stream_terminate→malformed_event`）。
- **输入**：
  - `deployment_id: str`｜必填｜非空｜部署 ID
- **输出**：`EnabledInjection?`（§9.1.10）。
- **返回值**：
  - 命中 → `EnabledInjection`
  - 无 → `null`
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_injections`（`enabled=1`）。

##### `stream_wrapper(deployment_id, base_stream)`
- **功能**：按流阶段注入包装 SSE 字节流（截断/畸形）；无注入则透传。
- **输入**：
  - `deployment_id: str`｜必填｜非空｜部署 ID
  - `base_stream: Iterable[bytes]`｜必填｜—｜原始 SSE 字节流
- **输出**：`Iterable[bytes]`（惰性）。
- **返回值**：
  - 恒 → 生成器
  - 命中 `stream_terminate` → 第 N 块后结束
  - 命中 `malformed_event` → 第 N 块后追加一帧畸形事件并结束
- **统计 · 日志**：无。
- **数据库**：只读 `diagnostic_injections`。

#### 9.2.5 `IF-LIBDIAG-CLEANUP` · 保留期（`retention.py`）

##### `cleanup(days=7)`
- **功能**：删除超过保留期的快照/trace/统计；**fail-open**。
- **输入**：
  - `days: int`｜可选，默认 `7`｜≥0｜保留天数
- **输出**：删除行数 `int`（≥0）。
- **返回值**：
  - 成功 → 删除数
  - 失败 → `0`（不抛）
- **统计 · 日志**：失败记 warning（`capture_failed`）。
- **数据库**：删除 `diagnostic_snapshots`/`trace_events`/`data_plane_latency_samples`/`data_plane_stats` 中早于 `now-days` 的行。

## 10. 并发、失败与恢复

#### 10.1 `F-DIAG-WRITE` · 记录写入失败
- **初始条件 / 并发交错 / 失败点**：Store 错误
- **检测事实 / authority / 期限**：异常
- **处理行为 / 副作用边界**：`_warn`；返回空/继续；**不改推理**
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：N/A + 理由：尽力而为
- **最终状态 / 资源归属 / 后续合法入口**：缺失记录
- **验证项 / 组合责任**：`VRC-DIAG-003`

#### 10.2 `F-DIAG-INJECT-VALID` · 注入非法
- **初始条件 / 并发交错 / 失败点**：非法类型/参数
- **检测事实 / authority / 期限**：`_validate`（§8.4）
- **处理行为 / 副作用边界**：400 `invalid_request`；不落库
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：修正后重试
- **最终状态 / 资源归属 / 后续合法入口**：400
- **验证项 / 组合责任**：`VRC-DIAG-004`

#### 10.3 `F-DIAG-INIT` · 初始化失败
- **初始条件 / 并发交错 / 失败点**：`DiagnosticsService` 构造失败
- **检测事实 / authority / 期限**：异常
- **处理行为 / 副作用边界**：降级运行（M005 记误）
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：重启
- **最终状态 / 资源归属 / 后续合法入口**：诊断不可用
- **验证项 / 组合责任**：`VRC-DIAG-003`

## 11. 安全、权限与可观测性

- **脱敏**：快照 URL 去 query、summary 截断；禁 Secret/凭据/正文（C-OBS-3）
- **权限**：不鉴权（能力库）；访问控制由 M001/M005
- **fail-open**：记录失败不改推理（C-OBS-2）
- **日志**：`_warn` 只写摘要，不含敏感内容

## 12. 容量、性能与运行限制

#### 12.1 `CAP-DIAG-RETENTION` · 保留期
- **目标 / 限制 / 单位**：7 天
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`cleanup(days)`
- **负载、数据规模与并发口径**：启动清理
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：删除过期
- **验证项 / Evidence**：`VRC-DIAG-002`；NOT_RUN

#### 12.2 `CAP-DIAG-STATS` · 统计内存
- **目标 / 限制 / 单位**：内存上限 + LRU
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`record_latency`
- **负载、数据规模与并发口径**：并发请求
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：淘汰最旧
- **验证项 / Evidence**：`VRC-DIAG-002`；NOT_RUN

#### 12.3 `CAP-DIAG-SNAP` · 快照分页
- **目标 / 限制 / 单位**：50/页
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`snapshots_page`
- **负载、数据规模与并发口径**：单查询
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：`next_cursor`
- **验证项 / Evidence**：`VRC-DIAG-002`；NOT_RUN

## 13. 实现步骤与文件清单

### 13.1 文件分解（设计 → 代码文件）

本模块按**一个功能一个文件**拆分；`diagnostics.py` 只保留**组合点**（门面），不含具体功能逻辑。

| 文件 | 功能 | 关键 symbol | 承接 ID | 状态 |
|---|---|---|---|---|
| `src/libdiag/diagnostics.py` | 组合点（门面） | `DiagnosticsService`（`switches/set_switches/record_trace/trace/traces/capture_snapshot/snapshots_page/record_latency/stats/set_injections/injections/enabled_injection/enabled_stream_injection/stream_wrapper/cleanup`）、`_warn` | `IF-LIBDIAG-*` | Implemented |
| `src/libdiag/settings.py` | 功能1 开关 | `SettingsDiagnostics.switches/set_switches` | `F-DIAG-SWITCH`、`RULE-DIAG-SWITCH`、`C-OBS-1` | Implemented |
| `src/libdiag/traces.py` | 功能2 trace | `TraceDiagnostics.record_trace/trace/traces`（`_trace_view` 组合 snapshot+usage） | `F-DIAG-TRACE`、`F-DIAG-TRACES` | Implemented |
| `src/libdiag/snapshots.py` | 功能3 快照 | `SnapshotDiagnostics.capture_snapshot/snapshots_page`（组合 settings） | `F-DIAG-SNAPSHOT`、`RULE-DIAG-TRUNC` | Implemented |
| `src/libdiag/stats.py` | 功能4 统计 | `StatsDiagnostics.record_latency/stats`（组合 settings） | `F-DIAG-STATS`、`RULE-DIAG-PCTL` | Implemented |
| `src/libdiag/injections.py` | 功能5 注入 | `InjectionDiagnostics.set_injections/injections/enabled_injection/enabled_stream_injection`（`_validate`） | `F-DIAG-INJECT`、`RULE-DIAG-INJECT` | Implemented |
| `src/libdiag/stream.py` | 功能6 流包装 | `stream_wrapper(injections, did, base_stream)`（组合 injections） | `F-DIAG-STREAM` | Implemented |
| `src/libdiag/retention.py` | 功能7 保留期 | `cleanup(store, warn, days)` | `F-DIAG-CLEANUP`、`CAP-DIAG-RETENTION` | Implemented |
| `src/libdiag/common.py` | 共享 helper | `now/hour_of/iso/percentile` | （无独立需求 ID） | Implemented |
| `src/util/migrations/002_observability.sql` | 观测 6 表 DDL（M007 执行） | `diagnostic_settings`/`diagnostic_snapshots`/`data_plane_stats`/`diagnostic_injections`/`trace_events`/`data_plane_latency_samples` | `R-OBS-06` | Implemented |

**每个文件的职责 / 非职责**：门面只组合、不含功能逻辑；功能文件各自实现单一功能、不互相直连（除下表 §5.3 的显式组合）；`common.py` 只提供纯函数；DDL 只建表不含逻辑。

**构建目标 / 依赖 / 宿主装配**：全部随 `Application` 装配；功能文件依赖 `util.store`（M007）与 `http_api.errors`（ApiError）；DDL 由 `Store.migrate` 执行。

**验证入口**：`VRC-DIAG-001..004`。

### 13.2 实现步骤

#### 13.2.1 表结构与开关
- **前置输入 / 依赖**：迁移文件
- **新增 / 修改文件与 symbol**：`util/migrations/002_observability.sql`、`settings.py` `switches/set_switches`
- **固定语义 / 可自行决定范围**：默认关固定；实现可自选
- **交付结果**：开关可读写
- **完成检查**：`VRC-DIAG-001`

#### 13.2.2 记录与查询
- **前置输入 / 依赖**：Store
- **新增 / 修改文件与 symbol**：`diagnostics.py` `record_*`/`*_page`/`stats`/`trace`
- **固定语义 / 可自行决定范围**：脱敏/截断固定；实现可自选
- **交付结果**：记录与视图
- **完成检查**：`VRC-DIAG-002/003`

#### 13.2.3 注入与流包装
- **前置输入 / 依赖**：注入表
- **新增 / 修改文件与 symbol**：`diagnostics.py` `set_injections`/`stream_wrapper`
- **固定语义 / 可自行决定范围**：白名单固定；实现可自选
- **交付结果**：注入配置 + 流包装
- **完成检查**：`VRC-DIAG-004`

## 14. 测试与验收

#### 14.1 `VRC-DIAG-001` · 开关
- **覆盖 Function / Rule / Constraint / Interface**：`F-DIAG-SWITCH`、`RULE-DIAG-SWITCH`、`C-OBS-1`、`IF-LIBDIAG-SWITCH`
- **Case / 正常、边界与失败输入**：关/开；部分更新
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：关闭零写入
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M005

#### 14.2 `VRC-DIAG-002` · 记录与查询
- **覆盖 Function / Rule / Constraint / Interface**：`F-DIAG-TRACE/SNAPSHOT/STATS`、`RULE-DIAG-TRUNC/PCTL`、`C-OBS-3`
- **Case**：一次调用后 trace/snapshot/stats；URL 带 query
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：字段/脱敏/百分位正确
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003/M005

#### 14.3 `VRC-DIAG-003` · fail-open
- **覆盖 Function / Rule / Constraint / Interface**：`RULE-OBS-FAILOPEN`、`C-OBS-2`
- **Case**：写入失败/初始化失败
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：推理结果不变
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003

#### 14.4 `VRC-DIAG-004` · 注入
- **覆盖 Function / Rule / Constraint / Interface**：`F-DIAG-INJECT/STREAM`、`RULE-DIAG-INJECT`、`C-OBS-4`
- **Case**：四类注入 + 流截断/畸形；非法类型
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：400；命中确定性
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003/M001；`LT-OPEN-05`

## 15. 风险、未决问题与引用

#### 15.ISD · 实现规格采用方式
- **采用模式**：`separate`（模块设计不兼作 ISD）
- **模块对象 ID**：M006
- **实现规格 Document ID**：`libdiag-isd`
- **metadata 覆盖映射入口**：`libdiag-isd` 的 `implementation_specification.coverage_mapping`
- **理由 / 决定引用**：本文已含表结构/符号/失败/验证

#### 15.1 `RISK-DIAG-1` · 统计可丢
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 `F-DIAG-STATS`
- **事实缺口 / 触发条件**：重启/缓存满
- **影响 / 阻塞边界**：统计不连续；不影响账本
- **Owner / 最晚关闭 Gate**：LLMTier / —
- **选项 / 推荐 / 下一步取证**：明示非账本语义
- **关闭条件 / 决定或当前状态**：观察

#### 15.2 `OPEN-DIAG-1` · 流注入实现门禁
- **类型 / 影响的规则、接口、流程或约束**：Open Question；`LT-OPEN-05`
- **事实缺口 / 触发条件**：`stream_terminate`/`malformed_event` 需改造流式输出
- **影响 / 阻塞边界**：流注入验收待实现确认
- **Owner / 最晚关闭 Gate**：LLMTier / 实现门禁
- **选项 / 推荐 / 下一步取证**：确认 `stream_wrapper` 集成方案
- **关闭条件 / 决定或当前状态**：未决

引用：系统设计 §3.2/§11.3；机制 M-OBS §14.4（`R-OBS-01/06`）；`observability-design.md`；`src/util/migrations/002_observability.sql`。

## 附录 A. 机制承接表

#### A.1 `llmtier-observability-mechanism` / `R-OBS-01` · 观测底层读写
- **来源 Capability / Step / Constraint / 接口成员**：C-OBS-3、Step 2/3/4/5、interface `DiagnosticService` 全部
- **本模块必须负责的行为与保证**：开关/注入/记录底层读写、脱敏、fail-open
- **本模块提供 / 消费的接口**：`switches`/`set_switches`/`record_trace`/`capture_snapshot`/`record_latency`/`get_enabled_injections`/`stream_wrapper`/查询
- **本文落实位置**：§5.1、§6、§8、§9
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`
- **允许自行决定的范围**：存储/聚合实现
- **本地验证 / 组合验证交接**：`VRC-DIAG-001..004`
