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
| Last Modified Date | `2026-09-25` |
| Template ID | `design.definition` |
| Template Version | `3.2.0` |
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

#### 1.1.1 `CON-OBS-001` · 默认关闭、关闭零开销
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：全部记录原语
- **继承预算或行为保证**：开关关 → 短路不写
- **可自行选择 / 不可改变**：存储可自选；默认关不可变
- **本地落实 / 内部再分配**：I1 开关；§8
- **验证方法与结果 / 证据**：`VRC-DIAG-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.2 `CON-OBS-002` · fail-open
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：全部记录/查询
- **继承预算或行为保证**：失败不抛到推理路径
- **可自行选择 / 不可改变**：捕获实现可自选；fail-open 不可变
- **本地落实 / 内部再分配**：I2–I7；§10
- **验证方法与结果 / 证据**：`VRC-DIAG-003`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.3 `CON-OBS-003` · 不记录 Secret/凭据/完整正文
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：快照/统计/trace/注入
- **继承预算或行为保证**：只存脱敏字段
- **可自行选择 / 不可改变**：脱敏实现可自选；禁记不可变
- **本地落实 / 内部再分配**：I3/I4 截断；§11
- **验证方法与结果 / 证据**：`VRC-DIAG-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.4 `CON-OBS-005` · 能力提供者
- **上级基线与决定状态**：系统设计 §3.2；已采用
- **适用条件**：全部观测能力
- **继承预算或行为保证**：libdiag 提供能力，Observability 呈现
- **可自行选择 / 不可改变**：—（职责边界）
- **本地落实 / 内部再分配**：§5.1、§5.3
- **验证方法与结果 / 证据**：`VRC-DIAG-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M005 一致

## 2. 需求、功能与验收条件

### 2.1 `F-DIAG-SWITCH` · 开关读写
- **上级需求 / Constraint ID**：`CON-OBS-001`；机制 M-OBS CAP-OBS-3
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
- **上级需求 / Constraint ID**：`CON-OBS-004`；机制 M-OBS CAP-OBS-5
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
- **本模块提供**：`record_trace/capture_snapshot/record_latency/enabled_injection/enabled_stream_injection/stream_wrapper`
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

> 采用**接口固定格式**（功能 / 输入 / 输出 / 返回值 / 统计 · 日志 / 数据库）。覆盖**跨模块文件**与**模块内文件 ↔ 文件**调用；逐方法细节见 §9.1，数据结构见 §6。

#### 5.3.1 `IF-DIAG-01` · `src/http_api/app.py` → `src/libdiag/diagnostics.py`（查询/开关/注入）
- **功能**：M005 诊断路由经门面做查询、开关切换与注入配置读写。
- **输入**：
  - `switches()` / `set_switches(snapshots_enabled?, stats_enabled?, conn?)`｜开关（`conn` 非空并入调用方事务）
  - `snapshots_page(...)` / `stats(...)` / `trace(...)` / `traces(...)` / `injections(...)` / `set_injections(...)`｜查询 / 写配置
- **输出**：`SwitchState` / `SnapshotPage` / `StatsView` / `TraceView` / `InjectionView[]`（§6.2）。
- **返回值**：见 §9.1；`400`/`404` 由门面透传。
- **统计 · 日志**：无。
- **数据库**：见 §9.1 各接口（查询只读；`set_switches`/`set_injections` 写）。

#### 5.3.2 `IF-DIAG-02` · `src/inference/responses.py` → `src/libdiag/diagnostics.py`（记录）
- **功能**：推理路径经门面记录 trace / 快照 / 统计。
- **输入**：`record_trace(...)` / `capture_snapshot(...)` / `record_latency(...)`（逐参数见 §9.1）。
- **输出**：无 / `snap_id`。
- **返回值**：`None` / `snap_id` / `null`；**fail-open 不抛**。
- **统计 · 日志**：写失败记 warning（`capture_failed`）。
- **数据库**：见 §9.1（`INSERT trace_events`/`diagnostic_snapshots`；`UPSERT data_plane_stats`）。

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

## 6. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0 §2：主章“数据结构设计”，章内按**数据性质分类**（§6.1–§6.8），仅保留适用类别。底层列权威为 `util/migrations/002_observability.sql`（由 M007 `migrate()` 执行）；本模块拥有下层类型 ID 前缀 `D-DIAG-*`，逐结构完整记录（Data/Type ID、用途与来源／逐字段／跨字段与寿命／合法与拒绝实例／验证）。

**类别适用性**：6.1 公共基础类型与枚举 ✓｜6.2 业务与操作数据结构 ✓｜6.3 配置与规则数据结构 ✓｜6.4 通信报文结构 ✗（进程内库，无 wire）｜6.5 设备与 FPGA 表项结构 ✗（无设备）｜6.6 运行状态数据结构 ✓｜6.7 数据库表结构 ✓｜6.8 错误码与错误结构 ✓（引用系统 Error ID）。

### 6.1 公共基础类型与枚举

**6.1.1 `D-DIAG-STAGE` · TraceStageName（公共基础类型与枚举）**

```text
enum TraceStageName {
  received, validated, routed, upstream_started, upstream_ended, completed, aborted
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-STAGE`；trace 阶段名集合；唯一来源 `src/libdiag/traces.py`（调用方约定集合，代码不强制校验）。

- **`received`/`validated`/`routed`/`upstream_started`/`upstream_ended`/`completed`/`aborted`**：

  必填枚举值；每值 ≤64 字符；同 request 的 `stages` 按 `timestamp` 升序。

- **跨字段与寿命**：

  无状态枚举；随 `trace_events.stage` 持久（7 天）。

- **合法/拒绝实例**：

  合法 `completed`；边界：未知字符串可写入（无强制），消费方按未知处理。

- **验证**：

  `VRC-DIAG-002`；来源 `traces.py`。

**6.1.2 `D-DIAG-INJECTION-TYPE` · InjectionType（公共基础类型与枚举）**

```text
enum InjectionType {
  fault_502, fault_503, delay, rate_limit, stream_terminate, malformed_event
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-INJECTION-TYPE`；故障注入类型枚举；唯一来源 `src/libdiag/injections.py` 白名单。

- **`fault_502`/`fault_503`/`delay`/`rate_limit`/`stream_terminate`/`malformed_event`**：

  必填枚举值；白名单；每类型有固定 `config` 字段集（§6.3.1）。

- **跨字段与寿命**：

  白名单校验；随 `diagnostic_injections.injection_type` 持久；库寿命。

- **合法/拒绝实例**：

  合法 `delay`；拒绝 `nope` → 400 `invalid_injection`。

- **验证**：

  `VRC-DIAG-004`；来源 `injections.py`。

**6.1.3 `D-DIAG-SNAPSHOT-TYPE` / `D-DIAG-MALFORMED-TYPE`（公共基础类型与枚举）**

```text
enum SnapshotType { upstream, error }
enum MalformedEventType { invalid_json, unknown_event_type }
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-SNAPSHOT-TYPE` ∈ {`upstream`,`error`}；`D-DIAG-MALFORMED-TYPE` ∈ {`invalid_json`,`unknown_event_type`}；唯一来源 `src/libdiag/snapshots.py`/`injections.py`。

- **`upstream`/`error`**：

  必填枚举值；`upstream` 由 `http_status` 存在决定。

- **`invalid_json`/`unknown_event_type`**：

  必填枚举值；malformed 类型白名单。

- **跨字段与寿命**：

  随 `diagnostic_snapshots.snapshot_type` / 注入配置持久。

- **合法/拒绝实例**：

  `upstream`（有 status）；`invalid_json`。

- **验证**：

  `VRC-DIAG-002`、`VRC-DIAG-004`；来源 `snapshots.py`/`injections.py`。

### 6.2 业务与操作数据结构

**6.2.1 `D-DIAG-SWITCH` · SwitchState（业务与操作数据结构）**

```text
SwitchState {
  snapshots_enabled: bool,
  stats_enabled: bool
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-SWITCH`；全局诊断开关状态；唯一来源 `src/libdiag/settings.py`（`diagnostic_settings` 单行）。

- **`snapshots_enabled`**：

  必填布尔，默认 `false`；快照记录开关。

- **`stats_enabled`**：

  必填布尔，默认 `false`；统计记录开关。

- **跨字段与寿命**：

  两字段独立；恒取自 `singleton=1` 单行；关闭 ⇒ 零写入（CON-OBS-001）；持久单行；I1 写、I2–I6 读；随库寿命。

- **合法/拒绝实例**：

  合法 `{true,false}`；边界：缺行返回默认 `false`（迁移保证恒有）。

- **验证**：

  `VRC-DIAG-001`；来源 `settings.py`。

**6.2.2 `D-DIAG-TRACE` · TraceView / TraceStage（业务与操作数据结构）**

```text
TraceView {
  request_id: string, correlation_id: string?,
  stages: TraceStage[>=1], snapshot: SnapshotView?, usage: UsageView?
}
TraceStage { stage: TraceStageName, timestamp: RFC3339ms, detail: object? }
UsageView {
  record_version: int>=1, is_final: bool, model: string,
  input_tokens: int?, output_tokens: int?, total_tokens: int?,
  measurement_status: string∈{measured,unknown}, source: string
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-TRACE`；单请求完整 trace 视图；唯一来源 `src/libdiag/traces.py`；组合 `trace_events` + `diagnostic_snapshots` + `usage_record_versions`（M003/M004）。

- **`request_id`/`correlation_id`**：

  `request_id` 必填、非空；`correlation_id` 可空。

- **`stages`**：

  必填、≥1、升序；`TraceStage` 含 `stage`（§6.1.1）/`timestamp`/`detail?`。

- **`snapshot`/`usage`**：

  可空；组合最近快照与用量视图。

- **`UsageView.measurement_status`**：

  必填 ∈ {`measured`,`unknown`}；`measured⇒tokens 非空`、`unknown⇒空（不补零）`。

- **跨字段与寿命**：

  `stages` 非空且升序；`measured⇒tokens 非空`、`unknown⇒空（不补零）`；只读视图，请求级、非持久。

- **合法/拒绝实例**：

  合法完整 trace；拒绝：无记录 → `trace()` 返回 404 `not_found`。

- **验证**：

  `VRC-DIAG-002`；来源 `traces.py`。

**6.2.3 `D-DIAG-PAGE` · TracePage / SnapshotPage（业务与操作数据结构）**

```text
Page<T> { items: T[], next_cursor: string?, has_more: bool }   # items 长度 <= limit
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-PAGE`；trace / 快照分页；唯一来源 `traces.py`/`snapshots.py`。

- **`items`**：

  必填数组，≤limit；空匹配 → `[]`。

- **`next_cursor`**：

  可空字符串；`has_more=false ⇒ next_cursor=null`；cursor 稳定（trace=`first_ts|request_id`；快照=末条 `id`）。

- **`has_more`**：

  必填布尔；是否还有下一页。

- **跨字段与寿命**：

  `has_more=false ⇒ next_cursor=null`；cursor 稳定；请求级只读。

- **合法/拒绝实例**：

  合法翻页；边界：空匹配 → `items=[]`、`has_more=false`。

- **验证**：

  `VRC-DIAG-002`；来源 `traces.py`/`snapshots.py`。

**6.2.4 `D-DIAG-SNAPSHOT` · SnapshotView（业务与操作数据结构）**

```text
SnapshotView {
  id: string, request_id: string, captured_at: RFC3339ms,
  upstream_url: string,          # 去 query
  backend_model: string?, http_status: int?(100–599),
  latency_ms: float?(>=0), error_summary: string?(<=256B),
  model: string?, deployment_id: string?, snapshot_type: SnapshotType
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-SNAPSHOT`；一次上游调用快照；唯一来源 `src/libdiag/snapshots.py`，列权威 §6.7。

- **`id`**：

  必填字符串；快照标识。

- **`request_id`**：

  必填字符串；关联请求身份。

- **`captured_at`**：

  必填 `RFC3339ms`；捕获时间。

- **`upstream_url`**：

  必填字符串；去 query 的上游 URL。

- **`backend_model`**：

  可空字符串；后端模型名。

- **`http_status`**：

  可空整数，100–599；`upstream ⇒ 非空`。

- **`latency_ms`**：

  可空浮点，≥0；时延。

- **`error_summary`**：

  可空字符串，≤256B；UTF-8 安全截断。

- **`model`/`deployment_id`**：

  可空字符串；逻辑等级 / deployment。

- **`snapshot_type`**：

  必填 `D-DIAG-SNAPSHOT-TYPE`（§6.1.3）。

- **跨字段与寿命**：

  `upstream⇒http_status 非空`、`error⇒http_status 空`；URL 去 query；summary ≤256B；持久 `diagnostic_snapshots`；I3 写、M005 读；只追加；7 天。

- **合法/拒绝实例**：

  合法 `upstream` 快照；拒绝：`snapshots_enabled=false` → 不写（返回 null）。

- **验证**：

  `VRC-DIAG-002`；来源 `snapshots.py`。

**6.2.5 `D-DIAG-STATS` · StatsView / StatsWindow（业务与操作数据结构）**

```text
StatsView { windows: StatsWindow[] }
StatsWindow {
  stat_hour: YYYY-MM-DDTHH,
  deployment_id: string?, model: string?,
  status_breakdown: map<string,int>,
  error_4xx_count: int, error_5xx_count: int, request_count: int, error_count: int,
  latency_p50_ms: float?, latency_p95_ms: float?, latency_min_ms: float?, latency_max_ms: float?,
  latency_sum_ms: float
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-STATS`；按小时桶聚合统计；唯一来源 `src/libdiag/stats.py`（组合 `data_plane_stats` + 内存 samples）。

- **`windows`**：

  必填数组；无数据 → `[]`。

- **`stat_hour`**：

  必填；小时桶键（`YYYY-MM-DDTHH`）。

- **`status_breakdown`/`request_count`/`error_count`**：

  必填；按 HTTP status 计数；`error_*_count` 由 breakdown 派生。

- **`latency_p50/p95/min/max_ms`**：

  可空浮点；无样本 ⇒ 百分位 `null`。

- **`latency_sum_ms`**：

  必填浮点；无样本 ⇒ `sum=0`。

- **跨字段与寿命**：

  可丢、非账本；无样本 ⇒ 百分位 `null`、`sum=0`；请求级只读；内存聚合非持久。

- **合法/拒绝实例**：

  合法 window；边界：无数据 → `windows=[]`。

- **验证**：

  `VRC-DIAG-002`；来源 `stats.py`。

**6.2.6 `D-DIAG-INJECTION` · InjectionView / EnabledInjection（业务与操作数据结构）**

```text
InjectionView {
  id: string, deployment_id: string, type: InjectionType,
  config: object, enabled: bool, updated_at: RFC3339ms
}
EnabledInjection = diagnostic_injections 全行（enabled:int 恒 1）
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-INJECTION`；注入配置视图 / 命中的启用注入；唯一来源 `src/libdiag/injections.py`。

- **`id`/`deployment_id`**：

  必填字符串；注入标识 / 目标 deployment。

- **`type`**：

  必填 `D-DIAG-INJECTION-TYPE`（§6.1.2）。

- **`config`**：

  必填对象；字段集与 `type` 一致（§6.3.1）。

- **`enabled`/`updated_at`**：

  必填布尔 / 必填时间。

- **`EnabledInjection`**：

  `diagnostic_injections` 全行，`enabled=1`。

- **跨字段与寿命**：

  `config` 字段集与 `type` 一致；`EnabledInjection` 仅 `enabled=1`；持久；I5 写、I5/I6 读。

- **合法/拒绝实例**：

  合法 `delay`；拒绝非法 type/config → 400 `invalid_injection`。

- **验证**：

  `VRC-DIAG-004`；来源 `injections.py`。

### 6.3 配置与规则数据结构

**6.3.1 `D-DIAG-INJECTION-CONFIG` · InjectionConfig（配置与规则数据结构，按类型）**

```text
InjectionConfig {
  fault_502 | fault_503: { error_body: string },              # 非空, >512B 静默截断到 512B
  delay: { delay_ms: int },                                   # 0–60000
  rate_limit: { retry_after_sec: int },                       # 0–300
  stream_terminate: { stream_terminate_after_events: int },   # 1–10000
  malformed_event: { malformed_after_events: int, malformed_event_type: MalformedEventType }  # 0–10000
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-INJECTION-CONFIG`；各注入类型的 `config` 字段集与范围；唯一来源 `src/libdiag/injections.py` `_validate`。

- **`fault_502`/`fault_503`**：

  必填 `error_body: string`（非空）；超过 512B 时**静默按 UTF-8 安全截断到 512B**（不拒绝）；空串/非字符串 → 400 `invalid_injection`。

- **`delay`**：

  必填 `delay_ms: int`（0–60000）。

- **`rate_limit`**：

  必填 `retry_after_sec: int`（0–300）。

- **`stream_terminate`**：

  必填 `stream_terminate_after_events: int`（1–10000）。

- **`malformed_event`**：

  必填 `malformed_after_events: int`（0–10000）+ `malformed_event_type: D-DIAG-MALFORMED-TYPE`（§6.1.3）。

- **跨字段与寿命**：

  字段齐备且落在范围；越界/缺失 → 400 `invalid_injection`；持久于 `diagnostic_injections` 对应列；部分更新 upsert。

- **合法/拒绝实例**：

  合法 `{delay_ms:200}`；拒绝 `{delay_ms:60001}` → 400。

- **验证**：

  `VRC-DIAG-004`；来源 `injections.py`。

### 6.4 通信报文结构（适用时）

不适用：libdiag 为进程内库，不拥有跨执行边界的消息/事件/流 wire；SSE 输出由 M001 传输，本模块只提供 `stream_wrapper` 变换。理由与 tailoring 依据见章首。

### 6.5 设备与 FPGA 表项结构（适用时）

不适用：无连接器、总线、寄存器或 FPGA 端口。

### 6.6 运行状态数据结构

**6.6.1 `D-DIAG-RUNTIME-STATE` · DiagnosticsRuntimeState（运行状态数据结构）**

```text
DiagnosticsRuntimeState {
  switches: SwitchState,
  stats_cache: map<key, Agg>(上限 + LRU),
  last_cleanup: object?
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-RUNTIME-STATE`；诊断开关的运行时事实与统计缓存；唯一来源 `settings.py`（开关）与 `stats.py`（内存聚合 LRU）。

- **`switches`**：

  必填；等同 `D-DIAG-SWITCH`（§6.2.1）。

- **`stats_cache`**：

  必填映射；统计内存缓存，上限 + LRU 淘汰。

- **`last_cleanup`**：

  可空过程量；最近 `cleanup` 结果，不持久。

- **跨字段与寿命**：

  唯一写者=`set_switches`/`record_latency`；记录前判定（关闭零写入，CON-OBS-001）；缓存满 LRU 淘汰；单行持久 + 请求级过程量；进程退出丢失内存统计（不承诺恢复）。

- **合法/拒绝实例**：

  关 → 无新行；开 → 正常写入；缓存满 → 淘汰最旧。

- **验证**：

  `VRC-DIAG-001`；来源 `settings.py`。

### 6.7 数据库表结构

**6.7.1 `diagnostic_*` / `data_plane_*` / `trace_events`（数据库表）**

```text
tables {
  diagnostic_settings { singleton=1, snapshots_enabled, stats_enabled },
  diagnostic_snapshots { id PK, snapshot_type, http_status?, ... },
  data_plane_stats { (stat_hour, deployment_id, model, status) PK, ... },
  data_plane_latency_samples { 无 PK（追加）, ... },
  diagnostic_injections { id PK, UNIQUE(deployment_id, injection_type), injection_type, fault_status?, fault_body?, delay_ms?, retry_after_sec?, stream_terminate_after_events?, malformed_after_events?, malformed_event_type?, enabled, updated_at },
  trace_events { id PK, request_id, stage, ... }
}
```

- **Data/Type ID、用途与来源**：

  Authority = `util/migrations/002_observability.sql`（由 M007 `migrate()` 执行）；列级定义见 `util.isd` §4.4；本模块拥有上列 6 张表。

- **`diagnostic_settings.singleton`**：

  主键恒 =1；单行。

- **`diagnostic_snapshots.id`**：

  主键；`snapshot_type` 由 `http_status` 判定。

- **`data_plane_stats`**：

  主键 `(stat_hour,deployment_id,model,status)`；累加 upsert。

- **`data_plane_latency_samples`**：

  无主键；只追加。

- **`diagnostic_injections`**：

  `id` 主键；`UNIQUE(deployment_id,injection_type)`；**离散列**（无 `config_json`）：`injection_type`、`fault_status`、`fault_body`、`delay_ms`、`retry_after_sec`、`stream_terminate_after_events`、`malformed_after_events`、`malformed_event_type`、`enabled`、`updated_at`；按 `(deployment_id,injection_type)` upsert。

- **`trace_events.id`**：

  主键；只追加。

- **跨字段与寿命**：

  `diagnostic_snapshots.snapshot_type` 由 `http_status` 判定；`data_plane_stats` 累加 upsert；注入按 `(deployment_id,injection_type)` upsert；`diagnostic_settings`/`diagnostic_injections` 库寿命，快照/trace 7 天（追加），统计与样本按保留期。

- **合法/拒绝实例**：

  合法：空库由 M007 一次性建表；拒绝：非空库 schema 版本不符由 M007 拒绝启动（系统 `ERR-SCHEMA`，不属于本模块）。

- **验证**：

  `VRC-DIAG-002`；来源 `util/migrations/002_observability.sql`。

### 6.8 错误码与错误结构

**6.8.1 `D-DIAG-ERROR-MAP` · 诊断错误映射（错误码与错误结构，引用系统 §8.8）**

```text
enum DiagnosticErrorRef { ERR-NOTFOUND, ERR-INJECTION, ERR-REQ-VALIDATION, ERR-STORE }
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-ERROR-MAP`；本模块**不新增公共错误码**，对外错误引用系统目录（`llmtier-system-design` §8.8）；唯一来源系统 §8.8（公共含义）与 `openapi`（产生）；载荷 `D-ERROR-ENVELOPE`。

- **`ERR-NOTFOUND`（404 `not_found`）**：

  `trace()` 无记录 / 未知 deployment（注入）；未受理、无副作用；修 id。

- **`ERR-INJECTION`（400 `invalid_injection`）**：

  注入类型/字段/范围非法；未写入、配置不变；修正注入项。

- **`ERR-REQ-VALIDATION`（400 `invalid_request`）**：

  `set_switches` 参数非 `bool`；未更新；修正参数。

- **`ERR-STORE`（503 `usage_store_unavailable`）**：

  存储不可用；原生 `sqlite3.Error` 上抛；稍后重试。

- **跨字段与寿命**：

  `record_*` 失败 fail-open（不抛，记 warning），不产生公共错误；`trace`/`injections`/`set_injections` 的拒绝为显式 `ApiError`。

- **合法/拒绝实例**：

  拒绝：未知 deployment → 404；边界：写失败 → warning，无错误返回。

- **验证**：

  `VRC-DIAG-003`；来源 `errors.py` + 系统 §8.8。

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
- **结果 / 不变量 / 边界**：关闭零写入（CON-OBS-001）
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：存储可自选；短路不可变
- **具体输入推演 / 验证项**：关→无新行；`VRC-DIAG-001`

#### 8.2 `RULE-DIAG-TRUNC` · 脱敏与截断
- **输入前提 / 适用条件**：快照写入
- **算法 / 规则 / 选择依据**：`upstream_url` 去 query；`error_summary` 截断 256B（UTF-8 安全）
- **结果 / 不变量 / 边界**：只存脱敏字段（CON-OBS-003）
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

## 9. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口设计用途**分类（面向使用方的可调用 API 与组件/系统间协作的消息与数据流接口），逐接口完整记录；标题为真实调用形式，标题下先给**完整接口声明**，再就地说明输入/输出/错误/交互/验证，最后按固定六项。本模块接口**全部为进程内可调用函数，归 API**；消息与数据流/硬件与固件/人机与维护三类不适用（见 §9.2–§9.4）。数据结构引用 §6。门面 `DiagnosticsService`（`src/libdiag/diagnostics.py`）为唯一对外面。

### 9.1 API（适用时）

#### `DiagnosticsService.switches() -> SwitchState`
```text
DiagnosticsService.switches() -> SwitchState
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-SWITCH`；读取诊断全局开关；libdiag 提供、M005/M003/M001 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/diagnostics.py` → `settings.py` `SettingsDiagnostics.switches`。
- **输入与前提**：无参数；由调用方自行保证上下文。
- **成功输出与保证**：`SwitchState`（§6.2.1）——读取用途：供 M003/M001 记录前判定、M005 呈现；`transaction none`。
- **错误与合法下一步**：无（除存储不可达 → `ERR-STORE`，§6.8）；调用方稍后重试。
- **交互与生命周期**：同步；调用方线程；无期限/取消；幂等只读。
- **实现与验证**：正常 `{snapshots_enabled,stats_enabled}`；边界：并发 `set_switches` 后读到新值（单行事务）。`VRC-DIAG-001`。

#### `DiagnosticsService.set_switches(snapshots_enabled=None, stats_enabled=None, conn=None) -> SwitchState`
```text
set_switches(snapshots_enabled: bool | None = None, stats_enabled: bool | None = None, conn: Connection | None = None) -> SwitchState
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-SWITCH`；部分更新诊断全局开关；libdiag 提供、M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `settings.py` `SettingsDiagnostics.set_switches`。
- **输入与前提**：`snapshots_enabled: bool|None`（默认 `None`=不变）；`stats_enabled: bool|None`；`conn: Connection|None`；非 `bool`（且非 `None`）→ 拒绝。
- **成功输出与保证**：更新后的 `SwitchState`（§6.2.1）——生效范围：同事务内提交（`conn` 非空并入调用方事务）后对外可见。
- **错误与合法下一步**：参数非 `bool` → `ApiError(400,"invalid_request")`（`param`=字段名，系统 `ERR-REQ-VALIDATION`，§6.8）；副作用=无（未更新）；调用方修正参数。
- **交互与生命周期**：同步；`conn` 传入时加入调用方事务（否则自开 `BEGIN IMMEDIATE`）；幂等（重复设同值无副作用）。
- **实现与验证**：正常 `set_switches(stats_enabled=True)`；拒绝 `set_switches(snapshots_enabled="yes")` → 400。`VRC-DIAG-001`。

#### `DiagnosticsService.record_trace(request_id, stage, detail=None, correlation_id=None) -> None`
```text
record_trace(request_id: str, stage: str, detail: dict | None = None, correlation_id: str | None = None) -> None
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-RECORD`；追加一条 trace 事件；libdiag 提供、M001/M003 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/traces.py` `TraceDiagnostics.record_trace`。
- **输入与前提**：`request_id: str`（非空）；`stage: str`（∈§6.1）；`detail: dict|None`；`correlation_id: str|None`；字段约束见 §6.1/§6.2。
- **成功输出与保证**：无——受理即追加一行 `trace_events`（§6.7）。
- **错误与合法下一步**：写失败 → **fail-open**：不抛，记 `OperationalLog(warning, diagnostics, capture_failed)`；结果已知性=丢失该阶段；副作用=无（无半写）；调用方继续请求，不改推理。
- **交互与生命周期**：同步；请求线程；无期限；不幂等（每次一行）；`transaction creates new`。
- **实现与验证**：正常 `record_trace("req","received")`；边界：DB 只读 → warning 且不阻断请求。`VRC-DIAG-002/003`。

#### `DiagnosticsService.capture_snapshot(request_id, deployment_id, model, upstream_url, backend_model, http_status, latency_ms, error_summary) -> str | None`
```text
capture_snapshot(request_id: str, deployment_id: str | None, model: str | None, upstream_url: str, backend_model: str | None, http_status: int | None, latency_ms: float | None, error_summary: str | None) -> str | None
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-RECORD`；写入一次上游调用快照；libdiag 提供、M003 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/snapshots.py` `SnapshotDiagnostics.capture_snapshot`。
- **输入与前提**：`request_id`；`deployment_id`；`model`；`upstream_url`（去 query）；`backend_model`；`http_status`（100–599）；`latency_ms`（≥0）；`error_summary`（≤256B 截断）；受 `SwitchState.snapshots_enabled` 控制（§6.6）。
- **成功输出与保证**：`snap_id: str`——受理并持久一行 `diagnostic_snapshots`（§6.7）。
- **错误与合法下一步**：开关关 → `null`（未受理）；写失败 → `null` + warning（fail-open，§6.8）；调用方继续请求。
- **交互与生命周期**：同步；请求线程；`transaction creates new`；不幂等（每次新 id）。
- **实现与验证**：正常（status 200）→ `snap_*`；边界：开关关 → `null` 且无行。`VRC-DIAG-002`。

#### `DiagnosticsService.record_latency(deployment_id, model, status_code, latency_ms) -> None`
```text
record_latency(deployment_id: str | None, model: str | None, status_code: int | None, latency_ms: float | None) -> None
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-RECORD`；累加统计与延迟样本；libdiag 提供、M003 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/stats.py` `StatsDiagnostics.record_latency`。
- **输入与前提**：`deployment_id`；`model`；`status_code`（100–599；`None`/<100 → 记 `upstream_error`）；`latency_ms`（≥0；`None` 只计请求不计延迟）；受 `stats_enabled` 控制。
- **成功输出与保证**：无——`UPSERT data_plane_stats`；`latency_ms` 非空时追加 `data_plane_latency_samples`（§6.7）。
- **错误与合法下一步**：写失败 → fail-open warning（§6.8）；`≥400` 或 `upstream_error` ⇒ `error_count+1`；调用方继续请求。
- **交互与生命周期**：同步；`transaction creates new`；不幂等（累加）。
- **实现与验证**：正常（200,120ms）；边界：`status_code=None` → `upstream_error`。`VRC-DIAG-002`。

#### `DiagnosticsService.trace(request_id) -> TraceView`
```text
trace(request_id: str) -> TraceView
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-QUERY`；聚合单请求完整 trace；libdiag 提供、M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/traces.py` `TraceDiagnostics.trace`。
- **输入与前提**：`request_id: str`（非空）。
- **成功输出与保证**：`TraceView`（§6.2.2）——组合 trace 阶段 + 最近快照 + 用量；只读。
- **错误与合法下一步**：无记录 → `ApiError(404,"not_found")`（系统 `ERR-NOTFOUND`，§6.8）；副作用=无；调用方修 id。
- **交互与生命周期**：同步只读；请求级；幂等。
- **实现与验证**：正常已有 request；拒绝未知 id → 404。`VRC-DIAG-002`。

#### `DiagnosticsService.traces(since=None, until=None, deployment_id=None, model=None, limit=50, cursor=None) -> TracePage`
```text
traces(since: str | None = None, until: str | None = None, deployment_id: str | None = None, model: str | None = None, limit: int = 50, cursor: str | None = None) -> TracePage
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-QUERY`；时间窗分页查询 trace；libdiag 提供、M005 消费；状态=Implemented（G-1）；唯一契约=本设计；文件·symbol `src/libdiag/traces.py` `TraceDiagnostics.traces`。
- **输入与前提**：`since/until: str|None`（RFC3339）；`deployment_id/model`（经快照过滤）；`limit`（夹 `[1,500]`）；`cursor`（`first_ts|request_id`）。
- **成功输出与保证**：`TracePage`（§6.2.3）——按请求去重、`first_ts DESC`。
- **错误与合法下一步**：无（恒返回页；空 → `items=[]`）。
- **交互与生命周期**：同步只读；`limit ≤500`；游标基于 `(first_ts,request_id)` 稳定。
- **实现与验证**：正常窗口分页；边界：空窗口 → `has_more=false`。`VRC-DIAG-004`。

#### `DiagnosticsService.snapshots_page(since=None, until=None, deployment_id=None, model=None, limit=50, cursor=None) -> SnapshotPage`
```text
snapshots_page(since: str | None = None, until: str | None = None, deployment_id: str | None = None, model: str | None = None, limit: int = 50, cursor: str | None = None) -> SnapshotPage
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-QUERY`；分页查询上游快照；libdiag 提供、M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/snapshots.py` `SnapshotDiagnostics.snapshots_page`。
- **输入与前提**：输入同 `traces`；`cursor`=末条 `id`。
- **成功输出与保证**：`SnapshotPage`（§6.2.3）——快照按 `captured_at DESC,id DESC`。
- **错误与合法下一步**：无。
- **交互与生命周期**：同步只读；`limit ≤500`；cursor 稳定。
- **实现与验证**：正常分页；边界：无快照 → `items=[]`。`VRC-DIAG-002`。

#### `DiagnosticsService.stats(since, until, deployment_id=None, model=None) -> StatsView`
```text
stats(since: str, until: str, deployment_id: str | None = None, model: str | None = None) -> StatsView
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-QUERY`；按小时桶聚合统计查询；libdiag 提供、M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/stats.py` `StatsDiagnostics.stats`。
- **输入与前提**：`since/until: str`（必填，RFC3339，取前 13 字符做小时）；`deployment_id/model`。
- **成功输出与保证**：`StatsView`（§6.2.5）。
- **错误与合法下一步**：无；无数据 → `windows=[]`。
- **交互与生命周期**：同步只读。
- **实现与验证**：正常窗口；边界：无样本 → 百分位 `null`。`VRC-DIAG-002`。

#### `DiagnosticsService.set_injections(deployment_id, actor_items, conn=None) -> list[InjectionView]`
```text
set_injections(deployment_id: str, actor_items: list[dict], conn: Connection | None = None) -> list[InjectionView]
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-INJECT`；写入/更新按 deployment 的注入配置；libdiag 提供、M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/injections.py` `InjectionDiagnostics.set_injections`。
- **输入与前提**：`deployment_id`；`actor_items: list`（每项 `{type,config,enabled}`，字段约束见 §6.3.1）；`conn`。
- **成功输出与保证**：全量 `InjectionView[]`（§6.2.6）——生效范围：upsert 提交后可见。
- **错误与合法下一步**：类型/字段/范围非法或非列表 → `ApiError(400,"invalid_injection")`（`ERR-INJECTION`）；未知 deployment → `ApiError(404,"not_found")`（`ERR-NOTFOUND`）；副作用=无（校验失败不写）；调用方修正注入项。
- **交互与生命周期**：同步；`conn` 非空并入调用方事务；幂等（按 `(deployment_id,type)` upsert）。
- **实现与验证**：正常 `[{type:"delay",config:{delay_ms:200},enabled:true}]`；拒绝未知 type → 400。`VRC-DIAG-004`。

#### `DiagnosticsService.injections(deployment_id) -> list[InjectionView]`
```text
injections(deployment_id: str) -> list[InjectionView]
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-INJECT`；读取按 deployment 的注入配置；libdiag 提供、M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/injections.py` `InjectionDiagnostics.injections`。
- **输入与前提**：`deployment_id`（非空）。
- **成功输出与保证**：`InjectionView[]`（§6.2.6），按 `injection_type` 排序。
- **错误与合法下一步**：未知 deployment → `ApiError(404,"not_found")`（§6.8）。
- **交互与生命周期**：同步只读；幂等。
- **实现与验证**：正常列表；边界：无注入 → `[]`。`VRC-DIAG-004`。

#### `DiagnosticsService.enabled_injection(deployment_id) -> EnabledInjection | None`
```text
enabled_injection(deployment_id: str) -> EnabledInjection | None
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-INJECT`；取命中的前置阶段注入；libdiag 提供、M001/M003/M005 消费；状态=Implemented；唯一契约=本设计；文件·symbol `injections.py` `InjectionDiagnostics.enabled_injection`。
- **输入与前提**：`deployment_id`（非空）。
- **成功输出与保证**：命中的前置阶段注入（优先级 `fault_502→fault_503→rate_limit→delay`，§6.2.6）或 `null`。
- **错误与合法下一步**：无；无命中 → `null`。
- **交互与生命周期**：同步只读；幂等。
- **实现与验证**：正常多注入取最高优先；边界：全关 → `null`。`VRC-DIAG-004`。

#### `DiagnosticsService.enabled_stream_injection(deployment_id) -> EnabledInjection | None`
```text
enabled_stream_injection(deployment_id: str) -> EnabledInjection | None
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-INJECT`；取命中的流阶段注入；libdiag 提供、I6/M001 消费；状态=Implemented；唯一契约=本设计；文件·symbol `injections.py` `InjectionDiagnostics.enabled_stream_injection`。
- **输入与前提**：`deployment_id`（非空）。
- **成功输出与保证**：命中的流阶段注入（`stream_terminate→malformed_event`）或 `null`。
- **错误与合法下一步**：无；无命中 → `null`。
- **交互与生命周期**：同步只读；幂等。
- **实现与验证**：正常命中；边界：无 → `null`。`VRC-DIAG-004`。

#### `DiagnosticsService.stream_wrapper(deployment_id, base_stream) -> Iterable[bytes]`
```text
stream_wrapper(deployment_id: str, base_stream: Iterable[bytes]) -> Iterable[bytes]
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-INJECT`；按流注入包装 SSE 字节流；libdiag 提供、M001 消费；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/stream.py` `stream_wrapper`（组合 `injections.py`）。
- **输入与前提**：`deployment_id`；`base_stream: Iterable[bytes]`（SSE 字节流）。
- **成功输出与保证**：惰性字节流——无注入透传；命中 `stream_terminate` 第 N 块后结束；`malformed_event` 第 N 块后追加一帧畸形事件并结束；受理/完成：生成器按块产出。
- **错误与合法下一步**：无（无注入即透传）。
- **交互与生命周期**：同步惰性；请求级流；不改变无注入流。
- **实现与验证**：正常透传；边界：命中 `stream_terminate` → 提前结束。`VRC-DIAG-004`。

#### `DiagnosticsService.cleanup(days=7) -> int`
```text
cleanup(days: int = 7) -> int
```
- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LIBDIAG-CLEANUP`；删除过期快照/trace/统计；libdiag 提供、启动/M005 触发；状态=Implemented；唯一契约=本设计；文件·symbol `src/libdiag/retention.py` `cleanup`。
- **输入与前提**：`days: int`（默认 7，≥0）。
- **成功输出与保证**：删除行数 `int`（≥0）——删除早于 `now-days` 的快照/trace/统计。
- **错误与合法下一步**：失败 → `0` + warning（fail-open，不抛，§6.8）。
- **交互与生命周期**：启动/显式调用；同步；幂等。
- **实现与验证**：正常删除过期；边界：无过期 → `0`。`VRC-DIAG-002`。

### 9.2 消息与数据流接口（适用时）

不适用（libdiag 为进程内库，不拥有消息/事件/流；SSE 流由 M001 传输、本模块只提供 `stream_wrapper` 变换，已在 §9.1 记录）。

### 9.3 硬件与固件接口（适用时）

不适用（无连接器/总线/寄存器/FPGA 端口）。

### 9.4 人机与维护接口（适用时）

不适用（无 UI/CLI；诊断入口归 M005/M001）。

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
- **处理行为 / 副作用边界**：400 `invalid_injection`；不落库
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

- **脱敏**：快照 URL 去 query、summary 截断；禁 Secret/凭据/正文（CON-OBS-003）
- **权限**：不鉴权（能力库）；访问控制由 M001/M005
- **fail-open**：记录失败不改推理（CON-OBS-002）
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
| `src/libdiag/settings.py` | 功能1 开关 | `SettingsDiagnostics.switches/set_switches` | `F-DIAG-SWITCH`、`RULE-DIAG-SWITCH`、`CON-OBS-001` | Implemented |
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
- **覆盖 Function / Rule / Constraint / Interface**：`F-DIAG-SWITCH`、`RULE-DIAG-SWITCH`、`CON-OBS-001`、`IF-LIBDIAG-SWITCH`
- **Case / 正常、边界与失败输入**：关/开；部分更新
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：关闭零写入
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M005

#### 14.2 `VRC-DIAG-002` · 记录与查询
- **覆盖 Function / Rule / Constraint / Interface**：`F-DIAG-TRACE/SNAPSHOT/STATS`、`RULE-DIAG-TRUNC/PCTL`、`CON-OBS-003`
- **Case**：一次调用后 trace/snapshot/stats；URL 带 query
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：字段/脱敏/百分位正确
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003/M005

#### 14.3 `VRC-DIAG-003` · fail-open
- **覆盖 Function / Rule / Constraint / Interface**：`RULE-OBS-FAILOPEN`、`CON-OBS-002`
- **Case**：写入失败/初始化失败
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：推理结果不变
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003

#### 14.4 `VRC-DIAG-004` · 注入
- **覆盖 Function / Rule / Constraint / Interface**：`F-DIAG-INJECT/STREAM`、`RULE-DIAG-INJECT`、`CON-OBS-004`
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

引用：系统设计 §3.2/§11.3；机制 M-OBS §14.4（`R-OBS-01/06`）、M-INFER §14.4（`R-INF-08`）；`observability-design.md`；`src/util/migrations/002_observability.sql`。

## 附录 A. 机制承接表

#### A.1 `llmtier-observability-mechanism` / `R-OBS-01` · 观测底层读写
- **来源 Capability / Step / Constraint / 接口成员**：CON-OBS-003、Step 2/3/4/5、interface `DiagnosticService` 全部
- **本模块必须负责的行为与保证**：开关/注入/记录底层读写、脱敏、fail-open
- **本模块提供 / 消费的接口**：`switches`/`set_switches`/`record_trace`/`capture_snapshot`/`record_latency`/`enabled_injection`/`enabled_stream_injection`/`stream_wrapper`/查询
- **本文落实位置**：§5.1、§6、§8、§9
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`
- **允许自行决定的范围**：存储/聚合实现
- **本地验证 / 组合验证交接**：`VRC-DIAG-001..004`

#### A.2 `llmtier-inference-stream-mechanism` / `R-INF-08` · 推理路径诊断写入底层
- **来源 Capability / Step / Constraint / 接口成员**：CON-INFER-005（承接 `observability-design.md` A.2 的底层读写）
- **本模块必须负责的行为与保证**：`record_trace`/`capture_snapshot`/`record_latency` 等写入的底层读写、默认关闭零开销、脱敏、fail-open
- **本模块提供 / 消费的接口**：`DiagnosticService` 写入方法（供 M003 推理路径与 M005 经 M001 调用）
- **本文落实位置**：§5.1、§6、§8、§9
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`
- **允许自行决定的范围**：存储/聚合实现
- **本地验证 / 组合验证交接**：`VRC-DIAG-001..004`；观测用例
