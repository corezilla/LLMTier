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

#### 5.3.1 `IF-DIAG-01` · `M005 app.py` → `diagnostics.py`（查询/开关/注入）
- **签名 / 入口**：`switches/set_switches/snapshots_page/stats/trace/set_injections/injections`
- **输入与前置条件**：查询参数 / 注入项
- **输出 / 异常**：视图/状态/列表；400/404
- **ownership / 生命周期**：请求级；持久（M007）
- **实现与验证位置**：`diagnostics.py`；`VRC-DIAG-001`

#### 5.3.2 `IF-DIAG-02` · `M003 responses.py` → `diagnostics.py`（记录）
- **签名 / 入口**：`record_trace`/`capture_snapshot`/`record_latency`/`get_enabled_injections`
- **输入与前置条件**：请求阶段/上游事实
- **输出 / 异常**：行；fail-open
- **ownership / 生命周期**：持久（7 天）
- **实现与验证位置**：`diagnostics.py`；`VRC-DIAG-002`

#### 5.3.3 `IF-DIAG-03` · `M001 app.py` → `diagnostics.py`（流注入）
- **签名 / 入口**：`stream_wrapper(deployment_id, base_stream)`
- **输入与前置条件**：SSE 字节流
- **输出 / 异常**：字节流；透传或注入
- **ownership / 生命周期**：请求级流
- **实现与验证位置**：`diagnostics.py`；`VRC-DIAG-004`

#### 5.3.4 `IF-DIAG-INT` · 模块内文件间接口（门面 ↔ 功能 ↔ helper）
- **签名 / 入口**：
  - `diagnostics.py`（门面）→ 各功能：`settings.switches/set_switches`、`traces.record_trace/trace/traces`、`snapshots.capture_snapshot/snapshots_page`、`stats.record_latency/stats`、`injections.set_injections/injections/enabled_injection/enabled_stream_injection`、`retention.cleanup`、`stream.stream_wrapper`
  - `snapshots.py` / `stats.py` → `settings.py`：`switches()`（开关判定）
  - `stream.py` → `injections.py`：`enabled_stream_injection()`
  - `settings/traces/snapshots/stats/retention.py` → `common.py`：`now/hour_of/iso/percentile`
- **输入与前置条件**：门面在 `__init__` 持有 `store`/`logs`，并注入各功能（含 `_warn` 回调）
- **输出 / 异常**：功能返回值原样透传；`ApiError`/`sqlite3.Error` 冒泡到门面
- **ownership / 生命周期**：功能对象随门面（`Application`）寿命；无跨文件可变共享状态
- **实现与验证位置**：`src/libdiag/*.py`；`VRC-DIAG-001..004`

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

#### 6.1 `diagnostic_settings`
- **Authority / 定义位置**：`util/migrations/002_observability.sql`（单行 `singleton=1`）
- **字段**：`snapshots_enabled:int`、`stats_enabled:int`
- **键与跨字段约束**：单行；默认 0
- **Writer / Reader**：I1 写；I2–I6 读
- **创建、持有、借用/复制与释放**：持久
- **状态转换 / 并发规则**：部分更新
- **验证项**：`VRC-DIAG-001`

#### 6.2 `diagnostic_snapshots`
- **Authority / 定义位置**：`util/migrations/002_observability.sql`
- **字段**：`id`、`request_id`、`captured_at`、`upstream_url`、`backend_model`、`http_status`、`latency_ms`、`error_summary`、`model`、`deployment_id`、`snapshot_type`
- **键与跨字段约束**：URL 去 query；summary ≤256B
- **Writer / Reader**：I3 写；M005 读
- **创建、持有、借用/复制与释放**：持久（7 天）
- **状态转换 / 并发规则**：只追加
- **验证项**：`VRC-DIAG-002`

#### 6.3 `data_plane_stats`
- **Authority / 定义位置**：`util/migrations/002_observability.sql` + 内存聚合
- **字段**：`id`、按 deployment/model/hour 的计数与延迟
- **键与跨字段约束**：可丢、非账本
- **Writer / Reader**：I4 写；M005 读
- **创建、持有、借用/复制与释放**：持久/内存
- **状态转换 / 并发规则**：聚合
- **验证项**：`VRC-DIAG-002`

#### 6.4 `diagnostic_injections`
- **Authority / 定义位置**：`util/migrations/002_observability.sql`
- **字段**：`id`、`deployment_id`、`injection_type`、`enabled`、`fault_status`、`fault_body`、`delay_ms`、`retry_after_sec`、`stream_terminate_after_events`、`malformed_after_events`、`malformed_event_type`、`config_json`
- **键与跨字段约束**：`UNIQUE(deployment_id, injection_type)`；类型白名单
- **Writer / Reader**：I5 写；I5/I6 读
- **创建、持有、借用/复制与释放**：持久
- **状态转换 / 并发规则**：部分更新
- **验证项**：`VRC-DIAG-004`

#### 6.5 `trace_events`
- **Authority / 定义位置**：`util/migrations/002_observability.sql`
- **字段**：`id`、`request_id`、`stage`、`timestamp`、`detail_json`、`correlation_id`
- **键与跨字段约束**：同 request 有序
- **Writer / Reader**：I2 写；M005 读
- **创建、持有、借用/复制与释放**：持久（7 天）
- **状态转换 / 并发规则**：只追加
- **验证项**：`VRC-DIAG-002`

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

对外无端点；以下为内部操作（M005/M003/M001 消费）。

#### 9.1 `IF-LIBDIAG-SWITCH` · 开关
- **Direction / Operation / 责任模块 / backend**：in；`switches`/`set_switches`；M006；Store
- **Request / Response / Error / ownership**：部分更新 → 状态；fail-open
- **Contract authority / version / revision / hash / selector**：本文 §6.1
- **前提 / timeout / 兼容边界 / Error model**：—
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`（门面）→ `settings.py`
- **Constraint / VRC / Case / 环境 / Run**：`C-OBS-1`；`VRC-DIAG-001`；NOT_RUN
- **关联类型字段 ID**：`diagnostic_settings`

#### 9.2 `IF-LIBDIAG-RECORD` · 记录
- **Direction / Operation / 责任模块 / backend**：in；`record_trace`/`capture_snapshot`/`record_latency`；M006；Store
- **Request / Response / Error / ownership**：事实字段 → 行/聚合；fail-open
- **Contract authority / version / revision / hash / selector**：本文 §6.2–6.5
- **前提 / timeout / 兼容边界 / Error model**：开关开启
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`（门面）→ `traces.py`/`snapshots.py`/`stats.py`
- **Constraint / VRC / Case / 环境 / Run**：`C-OBS-2/3`；`VRC-DIAG-002/003`；NOT_RUN
- **关联类型字段 ID**：`diagnostic_snapshots`/`trace_events`/`data_plane_stats`

#### 9.3 `IF-LIBDIAG-QUERY` · 查询
- **Direction / Operation / 责任模块 / backend**：in；`snapshots_page`/`stats`/`trace`；M006
- **Request / Response / Error / ownership**：查询 → 视图
- **Contract authority / version / revision / hash / selector**：本文 §6
- **前提 / timeout / 兼容边界 / Error model**：—
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`（门面）→ `traces.py`/`snapshots.py`/`stats.py`
- **Constraint / VRC / Case / 环境 / Run**：`VRC-DIAG-002`；NOT_RUN
- **关联类型字段 ID**：视图

#### 9.4 `IF-LIBDIAG-INJECT` · 注入
- **Direction / Operation / 责任模块 / backend**：in；`set_injections`/`injections`/`enabled_injection`/`enabled_stream_injection`/`stream_wrapper`；M006
- **Request / Response / Error / ownership**：注入项 → 行/字节流；400
- **Contract authority / version / revision / hash / selector**：本文 §6.4
- **前提 / timeout / 兼容边界 / Error model**：白名单
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py`（门面）→ `injections.py`/`stream.py`
- **Constraint / VRC / Case / 环境 / Run**：`C-OBS-4`；`VRC-DIAG-004`；NOT_RUN
- **关联类型字段 ID**：`diagnostic_injections`

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
