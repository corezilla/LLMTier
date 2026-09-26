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
| Last Modified Date | `2026-09-25` |
| Template ID | `design.definition` |
| Template Version | `3.2.0` |
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
- **调用方**：M001（`GET /tier/admin/v1/diagnostics/stats`，扁平别名 `GET /v1/diagnostics/stats`）
- **输入与前提**：`since/until` + 可选 `deployment_id/model`
- **行为**：按小时桶聚合为 `windows[]`；每窗口计数 + `status_breakdown{status:count}` + P50/P95/min/max/sum
- **输出**：`{windows: [StatsWindow]}`，`StatsWindow = {stat_hour, deployment_id, model, status_breakdown:{"200":n,"503":m,"429":k,"upstream_error":x}, error_4xx_count, error_5xx_count, request_count, error_count, latency_p50_ms, latency_p95_ms, latency_min_ms, latency_max_ms, latency_sum_ms}`
- **错误与边界**：400（缺时间）
- **验收条件**：`status_breakdown` 按 HTTP status 分列；`error_4xx_count`/`error_5xx_count` 由分列派生；口径为"数据面统计、可丢"，非账本

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
- **错误与边界**：无记录 → 404（`ERR-NOTFOUND`）
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
- **验收条件**：支持"过去 10 分钟所有请求/失败请求"查询；分页稳定（`next_cursor`）。**当前状态：Implemented（G-1 已实现；正式契约待补，扁平别名 `/v1/diagnostics/traces` 已提供）**

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

> 本模块内部/跨模块文件交接逐项映射到 §9 的成员定义；签名、输入输出、错误与寿命以 §9 对应记录为唯一来源，本节不再复写。

| 内部契约 ID | provider → consumer | §9 成员 | 本文件责任 | 验证 |
|---|---|---|---|---|
| `IF-OBS-01` | `src/http_api/app.py` → `src/libdiag/diagnostics.py`（查询/开关/注入） | §9.1 `IF-DIAGNOSTICS`、`IF-DIAG-SNAPSHOTS`、`IF-DIAG-STATS`、`IF-DIAG-INJECTIONS`、`IF-TRACE`、`IF-DIAG-TRACES` | 路由只经 `DiagnosticsService` 读写，不直连表 | `VRC-OBS-001/002/003/004/005` |
| `IF-OBS-02` | `src/http_api/app.py` → `src/management/admin.py`（开关/注入审计） | §9.1 `IF-DIAGNOSTICS`、`IF-DIAG-INJECTIONS` | 写操作经 `AdminService.mutate` 包裹审计 | `VRC-OBS-003` |
| `IF-OBS-03` | `src/http_api/app.py` → `src/libdiag/diagnostics.py`（关联标识） | §9.1 `IF-OBS-CORRELATION` | 入口透传/回显并写 trace | `VRC-OBS-004` |

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

## 6. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0：主章“数据结构设计”，章内按**数据性质分类**。M005 不拥有持久表与 wire 报文，其数据对象为 M006 `libdiag` 结构的**呈现投影**；继承结构只定位原定义并记录本地投影。`6.4 通信报文`、`6.5 设备与 FPGA 表项`、`6.6 运行状态`、`6.7 数据库表结构` 不适用。本层拥有的结构逐项完整记录（Data/Type ID、用途与来源／逐字段／跨字段与寿命／合法与拒绝实例／验证），每个结构以真实名称作带编号小节标题。

**适用性**：6.1 公共基础类型与枚举 ✓｜6.2 业务与操作数据结构 ✓（M006 解析投影）｜6.3 配置与规则数据结构 ✓（注入配置，继承 M006）｜6.4 通信报文 ✗（wire 由 M001/OpenAPI 拥有）｜6.5 设备与 FPGA 表项 ✗（无设备）｜6.6 运行状态数据结构 ✗（开关/查询均请求级；运行记录状态归 M006）｜6.7 数据库表结构 ✗（表由 M006/libdiag 拥有，M005 不直连）｜6.8 错误码与错误结构 ✓（引用系统 Error ID）。

### 6.1 公共基础类型与枚举

**6.1.1 `CorrelationId`（公共基础类型与枚举）**

```text
CorrelationId {
  source: string,          // "X-Correlation-ID" | "traceparent"
  value: string
}
```

- **Data/Type ID、用途与来源**：

  `D-OBS-CORRELATION`；Consumer 提供的关联标识，用于跨系统串联；来源 `src/http_api/app.py` 入口头，映射 M006 trace detail。

- **`source`**：

  必填字符串，∈ {`X-Correlation-ID`,`traceparent`}；表示取值头来源（W3C `traceparent` 取 trace id）。

- **`value`**：

  必填字符串；原样透传的关联值。

- **跨字段与寿命**：

  **只透传、不生成、不修改**；仅当 consumer 提供时在响应头回显；请求级，随 trace detail 持久（M006）。

- **合法/拒绝实例**：

  合法 `X-Correlation-ID: abc` → 响应回显 + trace；边界：未提供 → 不回显、不报错。

- **验证**：

  `VRC-OBS-004`；来源 M006 §6.1。

**6.1.2 `TraceStageName`（公共基础类型与枚举，继承 M006 §6.1）**

```text
enum TraceStageName {
  received, validated, routed, upstream_started,
  upstream_ended, completed, aborted
}
```

- **Data/Type ID、用途与来源**：

  `D-OBS-STAGE`；trace 阶段名；定义与有序性由 M006 `traces.py` 维护，本层只呈现。

- **`received`**：

  入口收到请求。

- **`validated`**：

  校验阶段完成。

- **`routed`**：

  路由/注入读取完成。

- **`upstream_started`**：

  上游调用开始。

- **`upstream_ended`**：

  上游调用结束。

- **`completed`**：

  正常终态。

- **`aborted`**：

  客户端断开/中断终态。

- **跨字段与寿命**：

  同一 `request_id` 阶段按时间升序、不重定义取值；随 M006 trace 持久（7 天）。

- **合法/拒绝实例**：

  合法完整有序阶段；边界：无记录 → 空 `stages`（非错误）。

- **验证**：

  `VRC-OBS-004`；来源 `libdiag-design.md` §6.1。

### 6.2 业务与操作数据结构

**6.2.1 `SwitchView`（业务与操作数据结构，继承 M006 §6.2 `SwitchState`）**

```text
SwitchView {
  snapshots_enabled: bool,
  stats_enabled: bool
}
```

- **Data/Type ID、用途与来源**：

  `D-SWITCH-STATE`；诊断全局开关的呈现视图；底层单行持久于 M006，本层只读投影。

- **`snapshots_enabled`**：

  必填布尔；快照记录开关；缺省 `false`。

- **`stats_enabled`**：

  必填布尔；统计记录开关；缺省 `false`。

- **跨字段与寿命**：

  只读投影；写由 M006 `set_switches` 承担；请求级只读，底层单行持久。

- **合法/拒绝实例**：

  合法 `{true,false}`；边界：缺省默认 `false`，关闭时零写入。

- **验证**：

  `VRC-OBS-001`；来源 `libdiag-design.md` §6.2。

**6.2.2 `DiagnosticSnapshotView`（业务与操作数据结构，继承 M006 §6.2 `SnapshotView`）**

```text
DiagnosticSnapshotView {
  id: string,
  request_id: string,
  captured_at: timestamp,
  upstream_url: string,      // 去 query
  backend_model: string?,
  http_status: int?,
  latency_ms: float?,
  error_summary: string?,    // ≤256B
  model: string?,
  deployment_id: string?,
  snapshot_type: string
}
```

- **Data/Type ID、用途与来源**：

  `D-DIAG-SNAPSHOT-VIEW`；一次上游调用快照的呈现视图；底层持久于 M006，本层请求级只读。

- **`id`**：

  必填、非空字符串；快照稳定身份。

- **`request_id`**：

  必填字符串；关联请求身份。

- **`captured_at`**：

  必填时间戳；捕获时刻。

- **`upstream_url`**：

  必填字符串，**去 query**；不携带查询串中的敏感值。

- **`backend_model`**：

  可空字符串；上游实际模型名；缺失为 `null`。

- **`http_status`**：

  可空整数；上游 HTTP 状态；无响应时为空。

- **`latency_ms`**：

  可空浮点（≥0）；上游耗时毫秒；无响应时为空。

- **`error_summary`**：

  可空字符串，UTF-8 安全截断 ≤256B；无正文/Secret。

- **`model`**：

  可空字符串；逻辑等级名；缺失为 `null`。

- **`deployment_id`**：

  可空字符串；命中 deployment；缺失为 `null`。

- **`snapshot_type`**：

  必填字符串；快照类型（如 `upstream`）。

- **跨字段与寿命**：

  URL 去 query、`error_summary` 截断；分页 `{items,next_cursor,has_more}`；底层持久 7 天（M006）；本层请求级只读。

- **合法/拒绝实例**：

  合法 `snapshot_type=upstream` 带 status；边界：`snapshots_enabled=false` → 不产生新行。

- **验证**：

  `VRC-OBS-002`；来源 `libdiag-design.md` §6.2。

**6.2.3 `StatsView` / `StatsWindow`（业务与操作数据结构，继承 M006 §6.2）**

```text
StatsView {
  windows: StatsWindow[]
}
StatsWindow {
  stat_hour: string,             // "YYYY-MM-DDTHH"
  deployment_id: string?,
  model: string?,
  status_breakdown: map<string,int>,
  error_4xx_count: int,
  error_5xx_count: int,
  request_count: int,
  error_count: int,
  latency_p50_ms: float?,
  latency_p95_ms: float?,
  latency_min_ms: float?,
  latency_max_ms: float?,
  latency_sum_ms: float
}
```

- **Data/Type ID、用途与来源**：

  `D-STATS-VIEW`；按小时桶聚合的统计呈现视图；底层 `data_plane_stats` + 内存 samples（M006）。

- **`windows`**：

  必填数组；无数据 → `[]`。

- **`stat_hour`**：

  必填；小时桶键（`YYYY-MM-DDTHH`）。

- **`deployment_id` / `model`**：

  可空字符串；桶维度；缺失为 `null`。

- **`status_breakdown`**：

  必填映射；按 HTTP status 计数。

- **`error_4xx_count` / `error_5xx_count`**：

  必填整数；由 `status_breakdown` 派生（4xx 与 5xx/`upstream_error`）。

- **`request_count` / `error_count`**：

  必填整数；窗口内请求数 / 错误数。

- **`latency_p50_ms` / `latency_p95_ms` / `latency_min_ms` / `latency_max_ms`**：

  可空浮点；耗时毫秒；无样本为 `null`。

- **`latency_sum_ms`**：

  必填浮点；耗时总和毫秒；无样本 → `0`。

- **跨字段与寿命**：

  可丢、非账本；`error_*_count` 与 `status_breakdown` 一致；请求级只读，底层内存聚合。

- **合法/拒绝实例**：

  合法 window；边界：无数据 → `windows=[]`。

- **验证**：

  `VRC-OBS-002`；来源 `libdiag-design.md` §6.2。

**6.2.4 `TraceView` / `TracePage`（业务与操作数据结构，继承 M006 §6.2）**

```text
TraceView {
  request_id: string,
  correlation_id: string?,
  stages: TraceStage[],
  snapshot: DiagnosticSnapshotView?,
  usage: Usage?
}
TracePage {
  items: TraceView[],
  next_cursor: string?,
  has_more: bool
}
```

- **Data/Type ID、用途与来源**：

  `D-TRACE-VIEW`（单请求）/ `D-OBS-PAGE`（分页）；单请求完整 trace 视图与时间窗分页；底层持久于 M006，本层请求级只读。

- **`request_id`**：

  必填字符串；trace 键。

- **`correlation_id`**：

  可空字符串；consumer 提供时存在（§6.1.1）。

- **`stages`**：

  必填数组，元素为 §6.1.2 `TraceStageName`；非空且按时间升序。

- **`snapshot`**：

  可空，§6.2.2 `DiagnosticSnapshotView`；最近上游快照。

- **`usage`**：

  可空；请求用量（账本语义归 M-METER）。

- **`TracePage.items`**：

  必填数组；按 `request_id` 去重、`first_ts DESC`。

- **`TracePage.next_cursor`**：

  可空字符串；末条游标。

- **`TracePage.has_more`**：

  必填布尔；是否还有后续页。

- **跨字段与寿命**：

  `stages` 非空且按时间升序；分页去重 `request_id`、`first_ts DESC`；底层持久 7 天（M006）。

- **合法/拒绝实例**：

  合法完整 trace；拒绝：单请求无记录 → `trace()` 404（`ERR-NOTFOUND`）；边界：时间窗无匹配 → `TracePage.items=[]`（不报错）。

- **验证**：

  `VRC-OBS-004/005`；来源 `libdiag-design.md` §6.2。

**6.2.5 `InjectionView`（业务与操作数据结构，继承 M006 §6.2）**

```text
InjectionView {
  id: string,
  deployment_id: string,
  type: string,
  config: object,
  enabled: bool,
  updated_at: timestamp
}
```

- **Data/Type ID、用途与来源**：

  `D-INJECTION-VIEW`；按 deployment 的注入配置呈现视图；底层持久于 M006，本层请求级只读。

- **`id`**：

  必填、非空字符串；注入项身份。

- **`deployment_id`**：

  必填字符串；目标 deployment。

- **`type`**：

  必填字符串；注入类型白名单（见 §6.3.1）。

- **`config`**：

  必填对象；该 type 的参数集（见 §6.3.1）。

- **`enabled`**：

  必填布尔；是否生效。

- **`updated_at`**：

  必填时间戳；最后更新时刻。

- **跨字段与寿命**：

  `type` 白名单与 `config` 字段集一致；多 enabled 时按确定性优先级取单条；底层持久（M006），本层请求级只读。

- **合法/拒绝实例**：

  合法 `type=delay`；边界：未知 deployment → 404。

- **验证**：

  `VRC-OBS-003`；来源 `libdiag-design.md` §6.2。

### 6.3 配置与规则数据结构

**6.3.1 `InjectionConfig`（配置与规则数据结构，继承 M006 §6.3）**

```text
InjectionConfig {
  type: string,            // fault_502|fault_503|delay|rate_limit|stream_terminate|malformed_event
  config: {
    error_body?: string,                    // fault_502|fault_503: 非空, >512B 静默截断
    delay_ms?: uint32,                      // delay: 0–60000
    retry_after_sec?: uint32,               // rate_limit: 0–300
    stream_terminate_after_events?: uint32, // 1–10000
    malformed_after_events?: uint32,        // 0–10000
    malformed_event_type?: string
  }
}
```

- **Data/Type ID、用途与来源**：

  `D-OBS-INJECTION-CONFIG`；各注入类型的 `config` 字段集与范围；持久于 M006 `diagnostic_injections`。

- **`type`**：

  必填字符串，白名单 {`fault_502`,`fault_503`,`delay`,`rate_limit`,`stream_terminate`,`malformed_event`}。

- **`config.error_body`**：

  条件必填字符串；`type ∈ {fault_502,fault_503}` 时必填；非空；超过 512B 时**静默按 UTF-8 安全截断到 512B**（不拒绝）。

- **`config.delay_ms`**：

  条件必填无符号整数，范围 0–60000；`type=delay` 时必填。

- **`config.retry_after_sec`**：

  条件必填无符号整数，范围 0–300；`type=rate_limit` 时必填。

- **`config.stream_terminate_after_events`**：

  条件必填无符号整数，范围 1–10000；`type=stream_terminate` 时必填。

- **`config.malformed_after_events`**：

  条件必填无符号整数，范围 0–10000；`type=malformed_event` 时必填。

- **`config.malformed_event_type`**：

  条件必填字符串；与 `malformed_after_events` 同用的异常事件类型。

- **跨字段与寿命**：

  字段齐备且在范围内，越界/缺失 → `ERR-INJECTION`；持久于 M006 `diagnostic_injections`。

- **合法/拒绝实例**：

  合法 `{delay_ms:200}`；拒绝 `{delay_ms:60001}` → 400。

- **验证**：

  `VRC-OBS-003`；来源 `libdiag-design.md` §6.3。

### 6.8 错误码与错误结构

本模块**不新增公共错误码**；对外错误引用系统目录（`llmtier-system-design` §8.8）：

| 本层错误 | 条件 | 系统 Error ID | 合法下一步 |
|---|---|---|---|
| `ApiError(404,"not_found")` | 未知 deployment / 无 trace | `ERR-NOTFOUND` | 修 id |
| `ApiError(400,"invalid_injection")` | 注入类型/字段/范围非法 | `ERR-INJECTION` | 修注入项 |
| `ApiError(400,"invalid_request")` | cursor/时间窗非法 | `ERR-CURSOR` / `ERR-REQ-VALIDATION` | 修查询参数 |
| `ApiError(503,"usage_store_unavailable")` | 存储不可读 | `ERR-STORE` | 稍后重试 |

- **约束 / 不变量**：查询无匹配返回空视图（非错误）；写配置非法才拒绝；观测记录 fail-open 不产生公共错误。
- **实例**：拒绝：未知 deployment → 404；边界：无 trace → 空 stages。
- **来源 / 验证**：`app.py` + 系统 §8.8；`VRC-OBS-002/003`。

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

## 9. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口设计用途**分类（面向使用方的 API 与组件/系统间协作的消息与数据流接口），逐接口完整记录；标题为真实调用形式（HTTP 路由），标题下先给**完整接口声明**，再就地说明参数/结果字段，最后按固定六项。诊断端点向 operator 提供可观测能力，归 API；消息流/硬件/人机三类不适用。数据结构引用 §6。端点由 M001 暴露、处理器位于 `src/http_api/app.py`，底层能力来自 M006 `DiagnosticsService`。

### 9.1 API（适用时）

> **路由别名**：下列契约前缀 `/tier/admin/v1/*` 路由由 M001 同入口同时提供 `/v1/*` 扁平别名（`29efe80`），语义与响应完全一致，例如 `GET /tier/admin/v1/diagnostics/traces` ≡ `GET /v1/diagnostics/traces`。本表以契约前缀为准，扁平别名不改变契约。

#### `GET /tier/admin/v1/diagnostics`

```text
GET /tier/admin/v1/diagnostics -> 200 {"snapshots_enabled": bool, "stats_enabled": bool}
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAGNOSTICS`；读取诊断全局开关；M005 呈现、M006 持有；状态=Implemented；唯一契约=本设计；文件·symbol `src/http_api/app.py`（诊断分支）→ `DiagnosticsService.switches`。
- **输入与前提**：无；operator 角色由 M001 入口判定。
- **成功输出与保证**：`SwitchView`（§6.2.1）——读自 M006 单行开关；生效范围=当前全局配置。
- **错误与合法下一步**：存储不可达 → `ERR-STORE`（503）；调用方稍后重试。
- **交互与生命周期**：同步只读；请求级；幂等。
- **实现与验证**：正常 `{true,false}`；边界：缺行 → 默认 `false`。`VRC-OBS-001`；`app.py`。

#### `PATCH /tier/admin/v1/diagnostics`

```text
PATCH /tier/admin/v1/diagnostics {snapshots_enabled?: bool, stats_enabled?: bool} -> 200 SwitchView
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAGNOSTICS`；切换诊断全局开关；M005 呈现、M006 持有；状态=Implemented；唯一契约=本设计；文件·symbol `app.py` → `admin.py` `mutate` → `DiagnosticsService.set_switches`。
- **输入与前提**：可选 `snapshots_enabled`、`stats_enabled`（部分更新，缺省不变；非 bool → 400）。
- **成功输出与保证**：更新后的 `SwitchView`（§6.2.1）——经 `AdminService.mutate` 记审计后提交。
- **错误与合法下一步**：非 bool → `ApiError(400,"invalid_request")`（`ERR-REQ-VALIDATION`）；审计失败不改开关。
- **交互与生命周期**：同步；请求级；幂等（重复设同值无副作用）。
- **实现与验证**：正常 `{stats_enabled:true}`；拒绝 `"yes"` → 400。`VRC-OBS-001`；`app.py`。

#### `GET /tier/admin/v1/diagnostics/snapshots`

```text
GET /tier/admin/v1/diagnostics/snapshots?since&until&deployment_id&model&limit&cursor -> 200 {items:[DiagnosticSnapshotView], next_cursor, has_more}
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAG-SNAPSHOTS`；分页查询上游快照；M005 呈现、M006 提供；状态=Implemented；唯一契约=本设计；文件·symbol `app.py` → `DiagnosticsService.snapshots_page`。
- **输入与前提**：`since/until`（RFC3339）、`deployment_id/model`、`limit`（夹 `[1,500]`）、`cursor`（末条 id）。
- **成功输出与保证**：快照分页（§6.2.2），按 `captured_at DESC,id DESC`。
- **错误与合法下一步**：cursor/时间窗非法 → `ApiError(400,"invalid_request")`（`ERR-CURSOR`/`ERR-REQ-VALIDATION`）；存储不可读 → `ERR-STORE`。
- **交互与生命周期**：同步只读；`limit ≤500`；cursor 基于末条 id 稳定。
- **实现与验证**：正常分页；边界：无快照 → `items=[]`、`has_more=false`。`VRC-OBS-002`；`app.py`。

#### `GET /tier/admin/v1/diagnostics/stats`

```text
GET /tier/admin/v1/diagnostics/stats?since&until&deployment_id&model -> 200 StatsView
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAG-STATS`；查询按小时桶聚合的统计；M005 呈现、M006 提供；状态=Implemented；唯一契约=本设计；文件·symbol `app.py` → `DiagnosticsService.stats`。
- **输入与前提**：`since/until`（必填，取前 13 字符做小时）、`deployment_id/model`。
- **成功输出与保证**：`StatsView`（§6.2.3）。
- **错误与合法下一步**：缺时间 → `ApiError(400,"invalid_request")`（`ERR-REQ-VALIDATION`）；无数据 → `windows=[]`（非错误）。
- **交互与生命周期**：同步只读；请求级。
- **实现与验证**：正常窗口；边界：无样本 → 百分位 `null`。`VRC-OBS-002`；`app.py`。

#### `GET /tier/admin/v1/deployments/{deployment_id}/diagnostics`

```text
GET /tier/admin/v1/deployments/{deployment_id}/diagnostics -> 200 [InjectionView]
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAG-INJECTIONS`；读取按 deployment 的注入配置；M005 呈现、M006 提供；状态=Implemented；唯一契约=本设计；文件·symbol `app.py` → `DiagnosticsService.injections`。
- **输入与前提**：`deployment_id`。
- **成功输出与保证**：`InjectionView[]`（§6.2.5），按 `injection_type` 排序。
- **错误与合法下一步**：未知 deployment → `ApiError(404,"not_found")`（`ERR-NOTFOUND`）。
- **交互与生命周期**：同步只读；幂等。
- **实现与验证**：正常列表；边界：无注入 → `[]`。`VRC-OBS-003`；`app.py`。

#### `PATCH /tier/admin/v1/deployments/{deployment_id}/diagnostics`

```text
PATCH /tier/admin/v1/deployments/{deployment_id}/diagnostics {items:[{type,config,enabled}]} -> 200 [InjectionView]
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAG-INJECTIONS`；写入/更新按 deployment 的注入配置；M005 呈现、M006 持有；状态=Implemented；唯一契约=本设计；文件·symbol `app.py` → `admin.py` `mutate` → `DiagnosticsService.set_injections`。
- **输入与前提**：`deployment_id`；注入项列表（每项 `type/config/enabled`，约束见 §6.3.1）。
- **成功输出与保证**：全量 `InjectionView[]`（§6.2.5）——经审计后按 `(deployment_id,type)` upsert。
- **错误与合法下一步**：类型/字段/范围非法 → `ApiError(400,"invalid_injection")`（`ERR-INJECTION`）；未知 deployment → 404；校验失败不写。
- **交互与生命周期**：同步；并入审计事务；幂等（upsert）。
- **实现与验证**：正常 `[{type:"delay",config:{delay_ms:200},enabled:true}]`；拒绝未知 type → 400。`VRC-OBS-003`；`app.py`。

#### `GET /tier/admin/v1/trace/{request_id}`

```text
GET /tier/admin/v1/trace/{request_id} -> 200 TraceView
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-TRACE`；查询单请求完整 trace；M005 呈现、M006 提供；状态=Implemented；唯一契约=本设计；文件·symbol `app.py` → `DiagnosticsService.trace`。
- **输入与前提**：`request_id`。
- **成功输出与保证**：`TraceView`（§6.2.4）——组合 stages + 最近快照 + usage。
- **错误与合法下一步**：无记录 → `ApiError(404,"not_found")`（`ERR-NOTFOUND`）。
- **交互与生命周期**：同步只读；幂等。
- **实现与验证**：正常已有 request；拒绝未知 id → 404。`VRC-OBS-004`；`app.py`。

#### `GET /tier/admin/v1/diagnostics/traces`

```text
GET /tier/admin/v1/diagnostics/traces?since&until&deployment_id&model&limit&cursor -> 200 TracePage
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DIAG-TRACES`；时间窗分页查询 trace；M005 呈现、M006 提供；状态=Implemented（G-1）；唯一契约=本设计；文件·symbol `app.py` → `DiagnosticsService.traces`。
- **输入与前提**：同 snapshots。
- **成功输出与保证**：`TracePage`（§6.2.4）——按 `request_id` 去重、`first_ts DESC`。
- **错误与合法下一步**：无匹配 → 空 `items`（非错误）；cursor 非法 → `ERR-CURSOR`。
- **交互与生命周期**：同步只读；与 snapshots 对称分页。
- **实现与验证**：正常窗口分页；边界：空窗口 → `has_more=false`。`VRC-OBS-005`；`app.py`。

#### `apply_correlation(headers) -> (correlation_id: str | None, trace_detail: dict | None)`

```text
apply_correlation(headers) -> (correlation_id: str | None, trace_detail: dict | None)
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-OBS-CORRELATION`；入口提取并透传关联标识；M005 提供、M001 入口调用；状态=Implemented；唯一契约=本设计；文件·symbol `app.py`（入口）→ `DiagnosticsService.record_trace`。
- **输入与前提**：请求头 `X-Correlation-ID` 或 `traceparent`（由 M001 传入）。
- **成功输出与保证**：`CorrelationId`（§6.1.1）或 `None`——有则在响应头回显并写入 trace detail。
- **错误与合法下一步**：未提供 → 不回显、不报错（无异常）。
- **交互与生命周期**：同步；请求级；不生成、不修改。
- **实现与验证**：正常：带 `X-Correlation-ID` → 响应回显；边界：未带 → 无该头。`VRC-OBS-004`；`app.py`。

### 9.2 消息与数据流接口（适用时）

不适用（诊断端点均为请求-响应 HTTP，向 operator 提供查询/切换能力，属 API；本模块不拥有事件/队列/流，SSE 由 M001/M003 拥有）。

### 9.3 硬件与固件接口（适用时）

不适用（无连接器/总线/寄存器/FPGA 端口）。

### 9.4 人机与维护接口（适用时）

不适用（诊断入口归 M001、呈现归 M002；本模块不拥有 UI/CLI）。

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

#### 13.1.1 `src/http_api/app.py`（诊断路由）
- **职责 / 非职责**：诊断端点路由、关联标识透传/回显、开关/注入经审计；不含记录逻辑
- **关键 symbol / 导出范围**：`/tier/admin/v1/diagnostics*`、`/tier/admin/v1/trace/{id}` 分支；`X-Correlation-ID` 处理
- **承接 Function / Rule / Constraint / Interface ID**：`F-OBS-SWITCH/SNAPSHOTS/STATS/INJECTIONS/TRACE/CORRELATION`、`C-OBS-4`、`IF-DIAGNOSTICS/SNAPSHOTS/STATS/INJECTIONS/TRACE`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-OBS-001/002/003/004`

#### 13.1.2 `src/web_ui/app.js`（诊断页数据）
- **职责 / 非职责**：诊断页 4 tabs + 全局开关的数据装载/呈现；不直读库
- **关键 symbol / 导出范围**：`loadStats`/`loadTrace` 等（见 M002 §13）
- **承接 Function / Rule / Constraint / Interface ID**：`R-OBS-05`（经 M002）
- **构建目标 / 依赖 / 宿主装配**：静态资源（M002 拥有）
- **实现状态**：Implemented
- **验证入口**：M002 `VRC-UI-*`

#### 13.1.3 `src/libdiag/diagnostics.py`（查询方法）
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
