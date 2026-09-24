<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M005 Observability 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `observability` |
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
| Canonical Path | `docs/40_module_design/observability-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 单元摘要：为什么存在

| 项目 | 内容 |
|---|---|
| 模块编号 / 正式英文名称 | **M005** / Observability |
| 直属父对象编号 / 名称 | LLMTier 软件系统（本项目无子系统）|
| 父设计 Document ID / 登记位置 | `llmtier-system-design` / 系统设计 §3.2（唯一登记表）|
| 上级系统 / 父单元 | LLMTier 软件系统 |
| 解决的问题 | 跨服务失败时"知道有问题却定位不出哪一层/哪个请求/哪个上游调用"——把定位链路的**查询与呈现**（快照/统计/注入/trace/关联标识）与**开关切换**产品化，且不改推理契约 |
| 提供的能力 | 诊断管理面：`GET/PATCH /tier/admin/v1/diagnostics`（全局开关）、快照分页、统计、注入配置、单请求 trace；关联标识透传/回显；M002 诊断页数据 |
| 主要使用者 | M001 HTTP API（路由）、M002 Web UI（诊断页）、Operator |
| 不负责 | 观测记录的**底层读写**（M006 `libdiag`）；HTTP 传输（M001）；页面渲染（M002）；记录脱敏写入（M008）|

### 1.1 继承的上级约束与落实方式

#### 1.1.1 `C-OBS-1` · 默认关闭、关闭零开销
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：全部观测能力
- **继承预算或行为保证**：开关关闭时不写入、零开销
- **可自行选择 / 不可改变**：开关存储可自选；默认关不可变
- **本地落实 / 内部再分配**：I1/I2 经 M006 判定开关；§8
- **验证方法与结果 / 证据**：`VRC-OBS-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.2 `C-OBS-2` · fail-open
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：任意观测故障
- **继承预算或行为保证**：观测失败不改变推理结果
- **可自行选择 / 不可改变**：捕获实现可自选；fail-open 不可变
- **本地落实 / 内部再分配**：I1–I3 捕获；§10
- **验证方法与结果 / 证据**：`VRC-OBS-003`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M006 一致

#### 1.1.3 `C-OBS-3` · 不记录 Secret/凭据/完整正文
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：快照/统计/trace/注入
- **继承预算或行为保证**：只含脱敏字段
- **可自行选择 / 不可改变**：脱敏实现可自选；禁记不可变
- **本地落实 / 内部再分配**：I1–I4 + M006/M008；§11
- **验证方法与结果 / 证据**：`VRC-OBS-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M008 一致

#### 1.1.4 `C-OBS-4` · 注入调用标注 source=injected
- **上级基线与决定状态**：系统设计 §11.3；已采用
- **适用条件**：注入命中
- **继承预算或行为保证**：账本可区分注入调用
- **可自行选择 / 不可改变**：标注实现可自选；可区分不可变
- **本地落实 / 内部再分配**：I3 入口 + M003/M-METER；§8
- **验证方法与结果 / 证据**：`VRC-OBS-004`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M-METER 一致

#### 1.1.5 `C-OBS-5` · 能力由 libdiag 提供、Observability 呈现
- **上级基线与决定状态**：系统设计 §3.2；已采用
- **适用条件**：全部观测能力
- **继承预算或行为保证**：底层读写归 M006；呈现/切换归 M005
- **可自行选择 / 不可改变**：—（职责边界）
- **本地落实 / 内部再分配**：§5.1、§5.3
- **验证方法与结果 / 证据**：`VRC-OBS-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

## 2. 需求、功能与验收条件

### 2.1 `F-OBS-SWITCH` · 全局调试开关
- **上级需求 / Constraint ID**：`C-OBS-1`；机制 M-OBS CAP-OBS-3
- **调用方**：M001（`GET/PATCH /tier/admin/v1/diagnostics`）
- **输入与前提**：operator 凭据；PATCH 可部分更新
- **行为**：读/写 `snapshots_enabled`/`stats_enabled`
- **输出**：开关状态
- **错误与边界**：—
- **验收条件**：状态反映写入值；关闭时零写入

### 2.2 `F-OBS-SNAPSHOTS` · 快照查询
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-1
- **调用方**：M001（`GET /tier/admin/v1/diagnostics/snapshots`）
- **输入与前提**：`since/until/deployment_id/model/limit/cursor`
- **行为**：按条件分页返回上游快照
- **输出**：`{items, next_cursor, has_more}`
- **错误与边界**：400（cursor/时间窗）
- **验收条件**：字段完整且已脱敏；分页稳定

### 2.3 `F-OBS-STATS` · 统计查询
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-2；契约 §5.3（口径）
- **调用方**：M001（`GET /tier/admin/v1/diagnostics/stats`）
- **输入与前提**：`since/until` + 可选 `deployment_id/model`
- **行为**：聚合计数 + `status_breakdown{status:count}` + P50/P95/min/max/avg
- **输出**：`{request_count, error_count, status_breakdown:{"200":n,"503":m,"429":k,"upstream_error":x}, latency_p50_ms, latency_p95_ms, latency_min_ms, latency_max_ms, latency_sum_ms}`
- **错误与边界**：400（缺时间）
- **验收条件**：`status_breakdown` 按 HTTP status 分列；保留 4xx/5xx 总数作兼容；口径为"数据面统计、可丢"，非账本

### 2.4 `F-OBS-INJECTIONS` · 注入配置
- **上级需求 / Constraint ID**：`C-OBS-4`；机制 M-OBS CAP-OBS-5；契约 §5.1
- **调用方**：M001（`GET/PATCH /tier/admin/v1/deployments/{id}/diagnostics`）
- **输入与前提**：operator；注入项列表
- **行为**：按 deployment 读/写注入配置（部分更新）；**多 enabled 时按确定性优先级取"下一步要触发的一条"**——`fault_502 → fault_503 → rate_limit → delay`；流阶段同理 `stream_terminate → malformed_event`
- **输出**：注入项列表 / 单条 enabled 项
- **错误与边界**：400（非法类型/配置）；404
- **验收条件**：非法参数被拒；多 enabled 时优先级确定且唯一；注入调用可区分（`source=injected`）

### 2.5 `F-OBS-TRACE` · 单请求 trace
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-6
- **调用方**：M001（/v1/trace/{request_id}`）
- **输入与前提**：`request_id`
- **行为**：返回有序 stages + usage 关联
- **输出**：`{request_id, correlation_id?, stages[], usage?}`
- **错误与边界**：无记录 → 空 stages（不报错）
- **验收条件**：stage 有序；关联 usage 版本

### 2.6 `F-OBS-CORRELATION` · 关联标识
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-7；契约 §5.4
- **调用方**：M001（`X-Correlation-ID`/`traceparent`）
- **输入与前提**：Consumer 头
- **行为**：透传并写入 trace；**仅当 consumer 提供时在响应头回显 `X-Correlation-ID`**；未提供时不回显、不报错
- **输出**：回显头（仅提供时）
- **错误与边界**：缺省不影响
- **验收条件**：消费者提供则回显；未提供则响应无该头且不报错

### 2.7 `F-OBS-TRACES` · trace 时间窗查询（G-1）
- **上级需求 / Constraint ID**：机制 M-OBS CAP-OBS-6；Piko 联调缺口 G-1
- **调用方**：M001（`GET /tier/admin/v1/diagnostics/traces`）
- **输入与前提**：`since/until` + 可选 `deployment_id/model/limit/cursor`
- **行为**：按时间窗聚合 `trace_events`（去重 request_id），逐条返回 stages + correlation + usage；与 snapshots 对称分页
- **输出**：`{items:[{request_id, stages[], correlation_id?, usage?}], next_cursor, has_more}`
- **错误与边界**：无匹配 → 空 items（不报错）
- **验收条件**：支持"过去 10 分钟所有请求/失败请求"查询；分页稳定（`next_cursor`）。**当前状态：Planned（接口未实现，见 review G-1）**

## 3. UI、CLI、服务端点或设备操作面

**N/A — 本模块没有直接操作面。** 诊断端点由 **M001 HTTP API** 暴露、由 **M002 Web UI**（`/ui/diagnostics` 4 tabs + 全局开关）呈现。Tailoring 依据：系统设计 §3.2 规定入口层终止 HTTP/SSE、Web UI 承载呈现。

## 4. 外部边界与依赖

#### 4.1 `DEP-M001` · HTTP API（调用方）
- **角色 / 运行位置 / Owner**：调用方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：诊断查询/开关/注入的内部接口（经 `DiagnosticsService`）
- **契约 authority / 版本 / selector**：本文 §9；对外 OpenAPI 由 M001 映射
- **同步方式 / timeout / 生命周期**：同步；请求级
- **不可用或失败影响 / 责任出口**：`ApiError` 冒泡

#### 4.2 `DEP-M006` · libdiag（能力提供）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：`DiagnosticsService.switches/set_switches/snapshots_page/stats/trace/set_injections/injections`
- **本模块提供**：—
- **契约 authority / 版本 / selector**：`llmtier-observability-mechanism` §14.4 `R-OBS-01`
- **同步方式 / timeout / 生命周期**：同步；记录由 M007 持久化
- **不可用或失败影响 / 责任出口**：fail-open（C-OBS-2）

#### 4.3 `DEP-M002` · Web UI（呈现）
- **角色 / 运行位置 / Owner**：消费者；浏览器；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：诊断数据（经 M001）
- **契约 authority / 版本 / selector**：`llmtier-observability-mechanism` §14.4 `R-OBS-05`
- **同步方式 / timeout / 生命周期**：HTTP
- **不可用或失败影响 / 责任出口**：页面提示

#### 4.4 `DEP-M007/M008` · util / log（存储与脱敏）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：`Store`（经 M006）；脱敏日志
- **本模块提供**：—
- **契约 authority / 版本 / selector**：`llmtier-observability-mechanism` §14.4 `R-OBS-06`；M008 §9
- **同步方式 / timeout / 生命周期**：同步
- **不可用或失败影响 / 责任出口**：503/记 warning

## 5. 内部结构与实现位置

### 5.1 内部组成

#### 5.1.1 `I1` · 开关呈现与切换
- **职责与非职责**：读/写全局开关（`snapshots_enabled`/`stats_enabled`）；不实现记录读写
- **输入、处理与输出**：PATCH body → 开关状态
- **协作对象**：M006 `DiagnosticsService.set_switches/switches`
- **文件 / symbol / 实现状态**：`app.py` 路由 + `diagnostics.py` `switches/set_switches`；Implemented
- **拆分依据与替代方案代价**：开关由 libdiag 存、Observability 呈现，避免入口层直连基础层

#### 5.1.2 `I2` · 观测查询
- **职责与非职责**：快照/统计/trace 查询路由与返回整形；不做记录写入
- **输入、处理与输出**：查询参数 → 视图
- **协作对象**：M006 `snapshots_page/stats/trace/traces`
- **文件 / symbol / 实现状态**：`app.py` 路由 + `diagnostics.py` 查询方法；Implemented
- **拆分依据与替代方案代价**：查询与写入分离

#### 5.1.3 `I3` · 注入配置入口
- **职责与非职责**：按 deployment 读/写注入配置（经 libdiag 校验）；不执行注入
- **输入、处理与输出**：注入项列表 → 规范化配置
- **协作对象**：M006 `set_injections/injections`
- **文件 / symbol / 实现状态**：`app.py` 路由 + `diagnostics.py`；Implemented
- **拆分依据与替代方案代价**：注入执行在 M003 请求路径，配置入口在此

#### 5.1.4 `I4` · 关联标识
- **职责与非职责**：接收 `X-Correlation-ID`/`traceparent`，**仅 consumer 提供时回显**；不生成
- **输入、处理与输出**：请求头 → （提供时）回显 + trace detail
- **协作对象**：M001、M006 `record_trace`
- **文件 / symbol / 实现状态**：`app.py`；Implemented
- **拆分依据与替代方案代价**：标识透传在入口，记录在 libdiag

### 5.2 内部调用过程

#### 5.2.1 `CALL-OBS-QUERY` · 一次诊断查询
- **入口与调用上下文**：M001 → `DiagnosticsService.{snapshots_page,stats,trace}`
- **调用链**：`app.py` 路由 → `DiagnosticsService` 查询 → `Store`（经 M006）→ 视图
- **逐步传递的数据**：`(since,until,deployment_id,model,limit,cursor)` → `items/trace`
- **返回、异常与清理**：返回视图；查询错误 → 503/400
- **对应流程 / 接口 / 验证**：§7 P-OBS-QUERY / `VRC-OBS-002`

#### 5.2.2 `CALL-OBS-SWITCH` · 一次开关切换
- **入口与调用上下文**：M001 → `set_switches`（经 `admin.mutate` 审计）
- **调用链**：`app.py` → `admin.mutate` → `DiagnosticsService.set_switches` → `Store`
- **逐步传递的数据**：`{snapshots_enabled?, stats_enabled?}` → 状态
- **返回、异常与清理**：返回状态；审计成功/失败
- **对应流程 / 接口 / 验证**：§7 P-OBS-SWITCH / `VRC-OBS-001`

### 5.3 文件间接口契约

#### 5.3.1 `IF-OBS-01` · `app.py` → `diagnostics.py`
- **签名 / 入口**：`DiagnosticsService.switches/set_switches/snapshots_page/stats/trace/injections/set_injections`
- **输入与前置条件**：operator `Principal`；查询参数
- **输出 / 异常**：视图 / 状态；400/404
- **ownership / 生命周期**：请求级；记录持久（M007）
- **实现与验证位置**：`diagnostics.py`；`VRC-OBS-001/002`

#### 5.3.2 `IF-OBS-02` · `app.py` → `admin.py`（开关/注入审计）
- **签名 / 入口**：`AdminService.mutate(actor, "diagnostics.*", target, request_id, fn)`
- **输入与前置条件**：operator
- **输出 / 异常**：结果；`ApiError`
- **ownership / 生命周期**：请求级
- **实现与验证位置**：`admin.py`；`VRC-OBS-003`

#### 5.3.3 `IF-OBS-03` · `app.py` → `diagnostics.py`（关联标识）
- **签名 / 入口**：`record_trace(request_id, "received", {...}, correlation_id=...)`
- **输入与前置条件**：请求头 `X-Correlation-ID`/`traceparent`
- **输出 / 异常**：trace 行；fail-open
- **ownership / 生命周期**：记录持久
- **实现与验证位置**：`diagnostics.py`；`VRC-OBS-004`

### 5.4 服务提供方式（条件适用）

- **运行载体与入口**：N/A + 依据 —— 无独立 server；由 M001 进程内调用
- **并发/线程模型**：N/A + 依据 —— 使用调用方线程；统计聚合内含锁/上限
- **初始化、Ready、生效与停止**：N/A + 依据 —— 随 `Application` 装配；`cleanup(7)` 在启动时调用
- **宿主装配、失败和资源回收责任**：由 M001/启动装配；观测失败 fail-open

### 5.5 依赖方向

- **允许方向**：M001 → M005 → M006 → {M007, M008}
- **禁止方向与原因**：M005 不得直接读表（须经 M006/libdiag）；不得回调 M001/M002
- **循环/越层检查**：`app.py` 的诊断分支只调 `DiagnosticsService`；不直接 SQL
- **变更影响**：`DiagnosticsService` 查询签名变更影响 M001 路由与 M002 呈现

## 6. 数据模型、状态与 ownership

#### 6.1 `DiagnosticSnapshotView`
- **Authority / 定义位置**：M006 `diagnostics.py`（`diagnostic_snapshots`）
- **字段**：`id`、`request_id`、`captured_at`、`upstream_url`(脱敏)、`backend_model`、`http_status`、`latency_ms`、`error_summary`(≤256B)、`model`、`deployment_id`、`snapshot_type`
- **键与跨字段约束**：`upstream_url` 去 query；无正文/Secret
- **Writer / Reader**：M003 写；M005 读
- **创建、持有、借用/复制与释放**：持久（保留 7 天）
- **状态转换 / 并发规则**：只追加
- **验证项**：`VRC-OBS-002`

#### 6.2 `StatsView`
- **Authority / 定义位置**：M006 `diagnostics.py`（内存聚合）
- **字段**：`request_count`、`error_count`（按 HTTP status 分列见 `status_breakdown`）、`p50/p95/min/max/avg`
- **键与跨字段约束**：可丢、非账本
- **Writer / Reader**：M003 写；M005 读
- **创建、持有、借用/复制与释放**：内存缓存（LRU/TTL）
- **状态转换 / 并发规则**：并发累积
- **验证项**：`VRC-OBS-002`

#### 6.3 `TraceView`
- **Authority / 定义位置**：M006 `diagnostics.py`（`trace_events`）
- **字段**：`request_id`、`correlation_id?`、`stages[{stage,timestamp,detail}]`、`usage?`
- **键与跨字段约束**：同 request 有序；usage 关联账本版本
- **Writer / Reader**：M001/M003 写；M005 读
- **创建、持有、借用/复制与释放**：持久（7 天）
- **状态转换 / 并发规则**：只追加
- **验证项**：`VRC-OBS-004`

#### 6.4 `InjectionView`
- **Authority / 定义位置**：M006 `diagnostics.py`（`diagnostic_injections`）
- **字段**：`id`、`deployment_id`、`injection_type`、`enabled` + 各 type 配置；`config_json`
- **键与跨字段约束**：`injection_type ∈ {fault_502,fault_503,delay,rate_limit,stream_terminate,malformed_event}`
- **Writer / Reader**：M005 写（经审计）；M003 读（`enabled_injection`）
- **创建、持有、借用/复制与释放**：持久；`UNIQUE(deployment_id, injection_type)`
- **状态转换 / 并发规则**：部分更新
- **验证项**：`VRC-OBS-003`

## 7. 主流程与数据流

**内部流程正文**：诊断查询由 M001 路由到 `DiagnosticsService` 的查询方法，`Store` 返回后整形为视图（快照分页/统计/trace）；开关与注入的写操作经 `admin.mutate` 包裹审计，再调 `set_switches`/`set_injections`。所有写入 fail-open，失败记 warning 不改推理结果。关联标识在入口接收并回显、写入 trace。

#### 7.1 `P-OBS-QUERY` · 诊断查询
- **触发/适用条件**：`GET /tier/admin/v1/diagnostics*`、`/tier/admin/v1/trace/{id}`
- **图与正文位置**：§5.2.1；机制 M-OBS §6
- **正常出口**：视图
- **异常出口**：400/404/503

#### 7.2 `P-OBS-SWITCH` · 开关/注入变更
- **触发/适用条件**：`PATCH /tier/admin/v1/diagnostics`、`PATCH /tier/admin/v1/deployments/{id}/diagnostics`
- **图与正文位置**：§5.2.2
- **正常出口**：新状态 + 审计(success)
- **异常出口**：400/404 + 审计(failed)

#### 7.3 `P-OBS-RECORD` · 记录（由 M003 触发，本模块只提供能力）
- **触发/适用条件**：推理路径各阶段
- **图与正文位置**：机制 M-OBS §6
- **正常出口**：trace/快照/统计写入
- **异常出口**：记 warning（不阻断）

## 8. 关键算法与业务规则

#### 8.1 `RULE-OBS-SWITCH` · 开关语义
- **输入前提 / 适用条件**：任意记录路径
- **算法 / 规则 / 选择依据**：`snapshots_enabled`/`stats_enabled` 关 → 短路不写
- **结果 / 不变量 / 边界**：关闭零写入（C-OBS-1）
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：存储可自选；默认关不可变
- **具体输入推演 / 验证项**：关闭后无新行；`VRC-OBS-001`

#### 8.2 `RULE-OBS-FAILOPEN` · fail-open
- **输入前提 / 适用条件**：任意观测写入失败
- **算法 / 规则 / 选择依据**：捕获异常，记 warning 到运行日志，继续
- **结果 / 不变量 / 边界**：推理结果不变（C-OBS-2）
- **复杂度 / 资源限制**：—
- **允许替换范围 / 不可改变保证**：捕获实现可自选；不改结果不可变
- **具体输入推演 / 验证项**：注入库写失败仍返回推理结果；`VRC-OBS-003`

#### 8.3 `RULE-OBS-REDACT` · 脱敏
- **输入前提 / 适用条件**：任意记录
- **算法 / 规则 / 选择依据**：`upstream_url` 去 query；`error_summary` UTF-8 安全截断 256B；禁 Secret/凭据/正文
- **结果 / 不变量 / 边界**：查询结果不含敏感字段（C-OBS-3）
- **复杂度 / 资源限制**：O(len)
- **允许替换范围 / 不可改变保证**：实现可自选；禁记不可变
- **具体输入推演 / 验证项**：`?token=x` 被移除；`VRC-OBS-002`

#### 8.4 `RULE-OBS-INJECT` · 注入参数校验
- **输入前提 / 适用条件**：`PATCH /tier/admin/v1/deployments/{id}/diagnostics`
- **算法 / 规则 / 选择依据**：`injection_type` 白名单；各 type 参数范围；部分更新语义
- **结果 / 不变量 / 边界**：非法 → 400；未知 deployment → 404
- **复杂度 / 资源限制**：O(items)
- **允许替换范围 / 不可改变保证**：实现可自选；白名单/范围不可变
- **具体输入推演 / 验证项**：非法 `injection_type` → 400；`VRC-OBS-003`

#### 8.5 `RULE-OBS-CORR` · 关联标识
- **输入前提 / 适用条件**：入口请求
- **算法 / 规则 / 选择依据**：取 `X-Correlation-ID` 或 `traceparent`；有则回显并写入 trace
- **结果 / 不变量 / 边界**：不生成、不修改；缺省 silent
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；透传语义不可变
- **具体输入推演 / 验证项**：带 `X-Correlation-ID` → 响应头回显；`VRC-OBS-004`

## 9. 接口与机器契约

对外端点由 M001 暴露；字段 authority 为 `interfaces/openapi/llmtier.openapi.json`。

#### 9.1 `IF-DIAGNOSTICS` · 全局开关
- **Direction / Operation / 责任模块 / backend**：in；`GET/PATCH /tier/admin/v1/diagnostics`；M005
- **Request / Response / Error / ownership**：PATCH `{snapshots_enabled?, stats_enabled?}` → 状态；—
- **Contract authority / version / revision / hash / selector**：OpenAPI
- **前提 / timeout / 兼容边界 / Error model**：operator；部分更新
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`app.py` + `diagnostics.py`
- **Constraint / VRC / Case / 环境 / Run**：`C-OBS-1`；`VRC-OBS-001`；NOT_RUN
- **关联类型字段 ID**：开关状态

#### 9.2 `IF-DIAG-SNAPSHOTS` · 快照
- **Direction / Operation / 责任模块 / backend**：in；`GET /tier/admin/v1/diagnostics/snapshots`；M005
- **Request / Response / Error / ownership**：`since/until/deployment_id/model/limit/cursor` → `{items,next_cursor,has_more}`
- **Contract authority / version / revision / hash / selector**：OpenAPI
- **前提 / timeout / 兼容边界 / Error model**：400
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py` `snapshots_page`
- **Constraint / VRC / Case / 环境 / Run**：`C-OBS-3`；`VRC-OBS-002`；NOT_RUN
- **关联类型字段 ID**：`DiagnosticSnapshotView`（§6.1）

#### 9.3 `IF-DIAG-STATS` · 统计
- **Direction / Operation / 责任模块 / backend**：in；`GET /tier/admin/v1/diagnostics/stats`；M005
- **Request / Response / Error / ownership**：`since/until/deployment_id/model` → `{request_count,error_count,status_breakdown:{"200":n,"503":m,"429":k,"upstream_error":x},latency_p50_ms,latency_p95_ms,latency_min_ms,latency_max_ms,latency_sum_ms}`
- **Contract authority / version / revision / hash / selector**：OpenAPI
- **前提 / timeout / 兼容边界 / Error model**：400（缺时间）
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py` `stats`
- **Constraint / VRC / Case / 环境 / Run**：`VRC-OBS-002`；NOT_RUN
- **关联类型字段 ID**：`StatsView`（§6.2）

#### 9.4 `IF-DIAG-INJECTIONS` · 注入
- **Direction / Operation / 责任模块 / backend**：in；`GET/PATCH /tier/admin/v1/deployments/{id}/diagnostics`；M005
- **Request / Response / Error / ownership**：注入项列表；400/404
- **Contract authority / version / revision / hash / selector**：OpenAPI
- **前提 / timeout / 兼容边界 / Error model**：白名单/部分更新；多 enabled 时确定性优先级（fault_502→fault_503→rate_limit→delay；流阶段 stream_terminate→malformed_event），首个命中触发一种
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py` `set_injections/injections`；暴露的 `enabled_injection()` 返回单条最高优先级
- **Constraint / VRC / Case / 环境 / Run**：`C-OBS-4`；`VRC-OBS-003`；NOT_RUN
- **关联类型字段 ID**：`InjectionView`（§6.4）

#### 9.5 `IF-TRACE` · trace
- **Direction / Operation / 责任模块 / backend**：in；/v1/trace/{request_id}`；M005
- **Request / Response / Error / ownership**：`request_id` → `{request_id,correlation_id?,stages[],usage?}`
- **Contract authority / version / revision / hash / selector**：OpenAPI
- **前提 / timeout / 兼容边界 / Error model**：无记录 → 空 stages
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`diagnostics.py` `trace`
- **Constraint / VRC / Case / 环境 / Run**：`VRC-OBS-004`；NOT_RUN
- **关联类型字段 ID**：`TraceView`（§6.3）

#### 9.6 `IF-DIAG-TRACES` · trace 时间窗查询（G-1）
- **Direction / Operation / 责任模块 / backend**：in；`GET /tier/admin/v1/diagnostics/traces`（+ `/tier/admin/v1/diagnostics/traces` alias）；M005
- **Request / Response / Error / ownership**：`since/until/deployment_id/model/limit/cursor` → `{items:[{request_id,stages[],correlation_id?,usage?}],next_cursor,has_more}`
- **Contract authority / version / revision / hash / selector**：OpenAPI / management-contract
- **前提 / timeout / 兼容边界 / Error model**：与 snapshots 对称；无匹配 → 空 items
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`NOT_IMPLEMENTED`（Planned：`diagnostics.py` `traces`）
- **Constraint / VRC / Case / 环境 / Run**：`VRC-OBS-005`；NOT_RUN
- **关联类型字段 ID**：`TraceView`（§6.3）

## 10. 并发、失败与恢复

#### 10.1 `F-OBS-WRITE` · 观测写入失败
- **初始条件 / 并发交错 / 失败点**：库/缓存错误
- **检测事实 / authority / 期限**：异常（M006）
- **处理行为 / 副作用边界**：记 warning，返回空/继续；**不改推理结果**
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：N/A + 理由：尽力而为
- **最终状态 / 资源归属 / 后续合法入口**：缺失记录
- **验证项 / 组合责任**：`VRC-OBS-003`

#### 10.2 `F-OBS-QUERY` · 查询失败
- **初始条件 / 并发交错 / 失败点**：存储不可用
- **检测事实 / authority / 期限**：Store 异常
- **处理行为 / 副作用边界**：503（不伪装空结果）
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：稍后重试
- **最终状态 / 资源归属 / 后续合法入口**：503
- **验证项 / 组合责任**：`VRC-OBS-002`

#### 10.3 `F-OBS-INIT` · 诊断初始化失败
- **初始条件 / 并发交错 / 失败点**：`DiagnosticsService` 装配失败
- **检测事实 / authority / 期限**：异常
- **处理行为 / 副作用边界**：降级运行，Data Plane 不受影响
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：重启
- **最终状态 / 资源归属 / 后续合法入口**：诊断可用性下降
- **验证项 / 组合责任**：`VRC-OBS-003`

## 11. 安全、权限与可观测性

- **权限**：operator 凭据（M001 入口判定）；M005 不鉴权
- **脱敏**：查询结果只含脱敏字段（C-OBS-3）；`upstream_url` 去 query、`error_summary` 截断
- **禁止记录**：Secret/凭据/完整 prompt·输出·reasoning·vector
- **fail-open**：观测故障不改推理（C-OBS-2）

## 12. 容量、性能与运行限制

#### 12.1 `CAP-OBS-RETENTION` · 保留期
- **目标 / 限制 / 单位**：7 天（快照/trace）
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`cleanup(days)`
- **负载、数据规模与并发口径**：启动清理 + 定时
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：过期删除
- **验证项 / Evidence**：`VRC-OBS-002`；NOT_RUN

#### 12.2 `CAP-OBS-STATS` · 统计缓存上限
- **目标 / 限制 / 单位**：内存上限 + LRU/TTL
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`record_latency`/`stats`
- **负载、数据规模与并发口径**：并发累积
- **推导 / 测量方法与证据等级**：Specified（可丢）
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：淘汰最旧
- **验证项 / Evidence**：`VRC-OBS-002`；NOT_RUN

#### 12.3 `CAP-OBS-PAGE` · 分页
- **目标 / 限制 / 单位**：快照 50/页
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`snapshots_page`
- **负载、数据规模与并发口径**：单查询
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：`next_cursor`
- **验证项 / Evidence**：`VRC-OBS-002`；NOT_RUN

## 13. 实现步骤与文件清单

### 13.1 文件分解（设计 → 代码文件）

#### 13.1.1 `src/llmtier_v03/app.py`（诊断路由）
- **职责 / 非职责**：诊断端点路由、关联标识透传/回显、开关/注入经审计；不含记录逻辑
- **关键 symbol / 导出范围**：`/tier/admin/v1/diagnostics*`、`/tier/admin/v1/trace/{id}` 分支；`X-Correlation-ID` 处理
- **承接 Function / Rule / Constraint / Interface ID**：`F-OBS-SWITCH/SNAPSHOTS/STATS/INJECTIONS/TRACE/CORRELATION`、`C-OBS-4`、`IF-DIAGNOSTICS/SNAPSHOTS/STATS/INJECTIONS/TRACE`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-OBS-001/002/003/004`

#### 13.1.2 `src/llmtier_v03/webui/app.js`（诊断页数据）
- **职责 / 非职责**：诊断页 4 tabs + 全局开关的数据装载/呈现；不直读库
- **关键 symbol / 导出范围**：`loadStats`/`loadTrace` 等（见 M002 §13）
- **承接 Function / Rule / Constraint / Interface ID**：`R-OBS-05`（经 M002）
- **构建目标 / 依赖 / 宿主装配**：静态资源（M002 拥有）
- **实现状态**：Implemented
- **验证入口**：M002 `VRC-UI-*`

#### 13.1.3 `src/llmtier_v03/diagnostics.py`（查询方法）
- **职责 / 非职责**：本模块消费 `switches/set_switches/snapshots_page/stats/trace/set_injections/injections`；记录读写归 M006
- **关键 symbol / 导出范围**：同上（只读/写配置的一部分）
- **承接 Function / Rule / Constraint / Interface ID**：`F-OBS-*`、`IF-OBS-01`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-OBS-001/002`

### 13.2 实现步骤

#### 13.2.1 开关与查询路由
- **前置输入 / 依赖**：`DiagnosticsService`；OpenAPI
- **新增 / 修改文件与 symbol**：`app.py`
- **固定语义 / 可自行决定范围**：端点/权限固定；实现可自选
- **交付结果**：诊断端点可达
- **完成检查**：`VRC-OBS-001/002`

#### 13.2.2 注入配置入口
- **前置输入 / 依赖**：注入白名单；审计
- **新增 / 修改文件与 symbol**：`app.py` + `admin.py` + `diagnostics.py`
- **固定语义 / 可自行决定范围**：白名单固定；实现可自选
- **交付结果**：注入配置可读写
- **完成检查**：`VRC-OBS-003`

#### 13.2.3 关联标识
- **前置输入 / 依赖**：请求头
- **新增 / 修改文件与 symbol**：`app.py`
- **固定语义 / 可自行决定范围**：透传语义固定；实现可自选
- **交付结果**：回显头 + trace
- **完成检查**：`VRC-OBS-004`

## 14. 测试与验收

#### 14.1 `VRC-OBS-001` · 开关
- **覆盖 Function / Rule / Constraint / Interface**：`F-OBS-SWITCH`、`RULE-OBS-SWITCH`、`C-OBS-1`、`IF-DIAGNOSTICS`
- **Case / 正常、边界与失败输入**：关/开 snapshots/stats；关闭时推理
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：关闭时零写入
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M002

#### 14.2 `VRC-OBS-002` · 快照/统计查询与脱敏
- **覆盖 Function / Rule / Constraint / Interface**：`F-OBS-SNAPSHOTS/STATS`、`RULE-OBS-REDACT`、`C-OBS-3`、`IF-DIAG-SNAPSHOTS/STATS`
- **Case**：一次上游调用后查询；`?token=` URL
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：字段完整；URL 去 query；统计口径
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003

#### 14.3 `VRC-OBS-003` · 注入与 fail-open
- **覆盖 Function / Rule / Constraint / Interface**：`F-OBS-INJECTIONS`、`RULE-OBS-INJECT/FAILOPEN`、`C-OBS-2/4`、`IF-DIAG-INJECTIONS`
- **Case**：合法/非法注入；注入库写失败
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：400/404；推理结果不变
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003/M-METER

#### 14.4 `VRC-OBS-004` · trace 与关联标识
- **覆盖 Function / Rule / Constraint / Interface**：`F-OBS-TRACE/CORRELATION`、`RULE-OBS-CORR`、`IF-TRACE`
- **Case**：固定 request_id；带/不带 `X-Correlation-ID`
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：stage 有序；有则回显
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：Piko 联调

#### 14.5 `VRC-OBS-005` · trace 时间窗查询
- **覆盖 Function / Rule / Constraint / Interface**：`F-OBS-TRACES`、`IF-DIAG-TRACES`
- **Case / 正常、边界与失败输入**：多 request 时间窗；分页；越界窗
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：去重 request、`next_cursor` 稳定、越界为空
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：Piko 联调（G-1）

## 15. 风险、未决问题与引用

#### 15.ISD · 实现规格采用方式
- **采用模式**：`separate`（模块设计不兼作 ISD）
- **模块对象 ID**：M005
- **实现规格 Document ID**：`observability-isd`
- **metadata 覆盖映射入口**：`observability-isd` 的 `implementation_specification.coverage_mapping`
- **理由 / 决定引用**：呈现/路由逻辑与 M006 同文件但职责分离，本文已覆盖

#### 15.1 `RISK-OBS-1` · 统计为内存、可丢
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 `F-OBS-STATS`
- **事实缺口 / 触发条件**：进程重启/缓存满
- **影响 / 阻塞边界**：统计不连续；不影响账本
- **Owner / 最晚关闭 Gate**：LLMTier / —
- **选项 / 推荐 / 下一步取证**：明示"非账本语义"
- **关闭条件 / 决定或当前状态**：观察

#### 15.2 `OPEN-OBS-1` · 与 M006 的文件边界
- **类型 / 影响的规则、接口、流程或约束**：Open Question；§5.1/§13.1
- **事实缺口 / 触发条件**：`diagnostics.py` 同时含 M005 查询与 M006 记录
- **影响 / 阻塞边界**：文件分解的职责划分需与 M006 保持一致
- **Owner / 最晚关闭 Gate**：LLMTier / 本轮 review
- **选项 / 推荐 / 下一步取证**：以"记录= M006 / 查询呈现= M005"划分，或后续拆分文件
- **关闭条件 / 决定或当前状态**：未决

引用：系统设计 §3.2/§11.3；机制 M-OBS §14.4（`R-OBS-02/05/06`）；`libdiag-design.md`；`interfaces/openapi/llmtier.openapi.json`。

## 附录 A. 机制承接表

#### A.1 `llmtier-observability-mechanism` / `R-OBS-02` · 观测查询与开关呈现
- **来源 Capability / Step / Constraint / 接口成员**：C-OBS-1/5、Step 6
- **本模块必须负责的行为与保证**：查询与呈现、开关切换；授权
- **本模块提供 / 消费的接口**：诊断路由（经 M001）
- **本文落实位置**：§5.1、§9.1–9.5
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`app.py` + `diagnostics.py`（查询）
- **允许自行决定的范围**：呈现实现
- **本地验证 / 组合验证交接**：`VRC-OBS-001/002`
