<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 可观测性机制（LT-OBS）

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-observability-mechanism` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `design.system-mechanism` |
| Template Version | `2.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/observability.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

跨服务失败时无法定位"**哪一层、哪个请求、哪个上游调用**"。本机制把定位链路产品化：上游环回快照、数据面统计、故障注入、单请求 trace 与关联标识透传。

**为什么不能由一个单元独立完成**：事实在 Inference 的请求路径上产生，开关/注入配置需被入口层切换，查询/呈现属 Observability，底层读写归 `libdiag`；横跨请求路径、管理面、基础库。

**输入 → 处理 → 输出**：
- 输入：推理请求路径事件（received/validated/routed/upstream_started/…）、管理面开关与注入配置
- 处理：按开关决定是否写入；注入配置在路由前生效；统计累积
- 输出：快照 / 统计 / trace 查询结果；`X-Request-ID` 与可选关联标识回显

**核心取舍**：**默认关闭、关闭零开销、开启时尽力而为（fail-open）**——观测**绝不**改变推理结果。

## 2. 使用场景与功能

| Capability ID | 业务任务与触发 | 输入与可观察结果 | 提供方 / 消费者 | 实现状态 | 验证判据 |
|---|---|---|---|---|---|
| CAP-OBS-1 上游快照 | 一次上游调用结束后 | url/status/时延/错误摘要写入并可分页查 | `libdiag` / Observability | Implemented | 快照用例 |
| CAP-OBS-2 数据面统计 | 每次请求完成 | 计数 + P50/P95/min/max | `libdiag` / Observability | Implemented | 统计用例 |
| CAP-OBS-3 全局开关 | Operator 切换 | snapshots/stats 开或关 | Observability / Operator | Implemented | 开关生效用例 |
| CAP-OBS-5 故障注入 | 按 deployment 配置 | delay/fault/rate_limit/流异常 | `libdiag` / Operator | Implemented（流注入见 LT-OPEN-05）| 四类注入用例 |
| CAP-OBS-6 单请求 trace | 按 request_id 查询 | 全生命周期 stages + usage | `libdiag` / Operator | Implemented | trace 用例 |
| CAP-OBS-7 关联标识 | Consumer 传 `X-Correlation-ID`/`traceparent` | 透传并回显 | HTTP API / Consumer | Implemented | 关联用例 |

**不提供**：Secret/credential/完整 prompt 或输出正文记录；自动轮询；跨系统分布式追踪后端。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3 与 §11。

| Constraint ID | 约束 | 参与方保证 | 自由度 | 本文落实位置 |
|---|---|---|---|---|
| C-OBS-1 | 默认关闭，关闭时零开销 | `libdiag` | 开关存储 | §7、§9 |
| C-OBS-2 | fail-open：观测故障不得使推理失败 | 全体 | 捕获实现 | §7、§9 |
| C-OBS-3 | 不记录 Secret/credential/完整正文 | `libdiag` | 脱敏实现 | §8、§11 |
| C-OBS-4 | 注入调用在账本标注 `injected` | Inference | 标注方式 | §8 |
| C-OBS-5 | 调试能力由 `libdiag` **提供**、Observability **呈现** | Observability | — | §14 |

### 3.2 运行时统筹与确认责任

`libdiag` 提供能力（开关/注入配置/记录读写）；Observability 调用并呈现；Inference 在请求路径**按配置注入并写入事实**。写入是尽力而为，不作为请求成功的条件。

### 3.3 拓扑、目标身份与共享故障域

单节点。观测为**尽力而为**，与推理**故障域隔离**（观测故障不传播到推理）。目标身份为 `request_id` 与可选关联标识。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

> 数据定义分支：**已有机器源**（见下表“机器源”列）；正文只给阅读视图与差异，不另抄完整规范。

| 表 | 用途 | 关键字段 |
|---|---|---|
| `diagnostic_snapshots` | LT-OBS-1 上游快照 | id、request_id、captured_at、upstream_url（脱敏）、backend_model、http_status、latency_ms、error_summary（≤256B UTF-8 安全截断）、model、deployment_id、snapshot_type(`upstream`/`error`) |
| `data_plane_stats` | LT-OBS-2 统计聚合 | 按 deployment/model/hour 的计数与 P50/P95/min/max |
| `diagnostic_injections` | LT-OBS-5 注入配置 | id、deployment_id、injection_type、enabled + 各 type 配置列（见下）|
| `trace_events` | LT-OBS-6 trace | request_id、stage、timestamp、detail、correlation_id |

**注入类型**：`fault_502`、`fault_503`、`delay`（`delay_ms`）、`rate_limit`（`retry_after_sec`）、`stream_terminate`（`stream_terminate_after_events`）、`malformed_event`（`malformed_after_events`、`malformed_event_type`）。

### 4.2 编码、布局与共享类型映射

不适用二进制 ABI：SQLite 行 + JSON（`detail`、`config_json`）。详细 schema 见 `llmtier-diagnostics.isd.md`。

### 4.3 一致性、可见性与数据寿命

保留 **7 天**（由清理任务删除过期 snapshot 与 trace）。同 `request_id` 的 trace 事件**有序**。统计为**内存缓存**（上限 + LRU 淘汰），非账本、可丢。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

**内部能力（`libdiag` → Observability/Inference）**：

| 操作 | 签名 | 语义 | 失败 |
|---|---|---|---|
| 开关 | `get/update_diagnostics_settings`、`snapshots_enabled()`、`stats_enabled()` | 全局开关读写 | fail-open |
| 快照 | `capture_snapshot(...)` → `snapshot_id` | 写上游快照 | 记 warning、返回空串、**不抛** |
| 统计 | `record_latency(...)`、`get_stats(...)` | 累积/查询 | 缓存满 LRU 淘汰 |
| 注入 | `get_injections`、`upsert_injections`、`get_enabled_injections` | 按 deployment CRUD | — |
| Trace | `record_trace(...)`、`get_trace(request_id)` | 写/查全生命周期 | 记 warning、继续 |
| 清理 | `cleanup_old_records()` → 删除数 | 删 7 天前 | — |

**对外路由（Observability，operator / consumer 视凭据）**：

| 路由 | 方法 | 描述 |
|---|---|---|
| `GET/PATCH /v1/diagnostics` | GET / PATCH | 全局调试开关 |
| `GET /v1/diagnostics/snapshots` | GET | 快照分页查询 |
| `GET /v1/diagnostics/stats` | GET | 统计查询 |
| `GET/PATCH /v1/deployments/{id}/diagnostics` | GET / PATCH | 注入配置 |
| `GET /v1/trace/{request_id}` | GET | 单请求 trace |

**调用演练**：PATCH `/v1/deployments/dep_local_gemma/diagnostics`（`delay`,`enabled=true`,`delay_ms=2000`）→ 发一次推理 → trace 中 `routed` 阶段带注入标记 → 快照/统计出现该请求 → `GET /v1/trace/{request_id}` 返回有序 stages 与 usage。

## 6. 正常端到端流程

![可观测性记录与查询时序](../../assets/diagrams/diagram-mech-obs-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-obs-sequence.svg)

图 M · 可观测性记录与查询时序（实线=请求，虚线=响应；先后关系非时间比例）。

1. **received**：入口生成/接收 `request_id`，提取可选关联标识并回显。
2. **validated**：校验阶段写 trace。
3. **routed**：读该 deployment 的 enabled 注入并**生效**（delay/fault/rate_limit）。
4. **upstream_started / upstream_ended**：写上游快照 + `record_latency`。
5. **completed / error / aborted**：终态 trace；注入命中时账本 `source=injected`。
6. **查询**：快照/统计/trace 按各自接口返回。

### 6.1 交叠请求、跨轮次与生命周期边界

逐阶段记录；同一 `request_id` 事件有序。**交叠**：多请求共享内存统计（并发累积，LRU 上限）；注入配置为**逐请求读取**，切换即时生效；观测写入与推理路径解耦（fail-open）。

## 7. 分支和替代流程

| 分支 | 触发 | 处理 |
|---|---|---|
| 开关关闭 | snapshots/stats 关 | **不写入、零开销** |
| 注入命中 | enabled 注入 | 按类型 delay/fault/rate_limit/流异常 |
| 观测写入失败 | 库/缓存错误 | 记 warning，**不阻塞**推理 |
| 缓存满 | 统计上限 | LRU 淘汰最旧，继续 |
| 清理到期 | 7 天前记录 | 删除 |
| 流注入 | `stream_terminate`/`malformed_event` | 需改造流式输出（`LT-OPEN-05`）|

## 8. 状态机与不变量

| INV-ID | 可验证断言（量词、条件和预期必须明确） | Enforcement / 事实来源 | 反例输入/违反后的结果 | 验证项 |
|---|---|---|---|---|
| INV-1 | ∀ 记录：不含 Secret、credential、完整 prompt/输出/reasoning/vector | 写入前脱敏（§11）| 记录正文 → 泄密 | T-OBS-SNAP |
| INV-2 | ∀ `error_summary`：≤256 字节且 UTF-8 安全截断 | 截断函数 | 截断非法 → 查询报错 | T-OBS-SNAP |
| INV-3 | ∀ 注入调用：账本 `source=injected` | Inference 标注（§14.4）| 注入混入真实账本 → 对账失真 | T-OBS-INJECT |
| INV-4 | 开关关闭时：零写入 | `snapshots_enabled`/`stats_enabled` 短路 | 关闭仍写 → 违反零开销 | T-OBS-SWITCH |
| INV-5 | ∀ request：trace 事件有序 | `record_trace` 追加 | 乱序 → 无法还原时序 | T-OBS-TRACE |
| INV-6 | ∀ 观测失败：不影响推理结果（fail-open）| 捕获 + warning（§7）| 观测抛错 → 阻断推理 | T-OBS-FAILOPEN |

### 8.1 资源预留、交付、释放与复位

无预留/租约。**交付** = 尽力而为写入；**复位** = 清理任务（7 天）+ 关闭开关即零开销。`DiagnosticService` 初始化失败时**降级运行**。

## 9. 失败传播、重试与恢复

| Failure ID / 检测方 | 失败点与传播 | 结果已知性 | 已发生/可能副作用 | 访问安全/证据 | 操作终态 | 资源释放 | 重新准入/重试条件 |
|---|---|---|---|---|---|---|---|
| F-OBS-1 / `capture_snapshot` | 写入失败 | — | 记 warning | 无 | 返回空串，不抛 | 无 | 下次调用重试 |
| F-OBS-2 / `record_latency` | 缓存满 | — | 记 warning | 无 | LRU 淘汰 | 淘汰最旧缓存 | — |
| F-OBS-3 / `record_trace` | 写入失败 | — | 记 warning | 无 | 继续 | 无 | 下次调用重试 |
| F-OBS-4 / 初始化 | `DiagnosticService` 失败 | — | 记 error | 无 | **降级运行**，Data Plane 不受影响 | 无 | 重启 |

**恢复边界**：任何观测失败**不得**改变推理结果或阻断请求（C-OBS-2）。

## 10. 并发、排序与容量

| 作用域 | 约束 | 行为 |
|---|---|---|
| 统计缓存 | 内存上限 | LRU 淘汰 |
| trace/快照写 | 尽力而为 | 无背压到推理 |
| 注入读 | 逐请求 | 即时生效 |
| 保留 | 7 天 | 定时清理 |

## 11. 安全、权限与信任边界

| 资产 | 身份 | 强制点 | 拒绝 | 审计 |
|---|---|---|---|---|
| 开关/注入/快照/统计/trace | operator 凭据 | 管理面授权 | 401/403 | — |
| 关联标识 | Consumer | 入口透传并回显 | — | — |

边界：需 operator 凭据；`upstream_url` 移除 query string；`error_summary` UTF-8 安全截断（INV-1/2）。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

本机制即**证据来源**；与 `logs`（脱敏运行日志）、`audit`（管理动作审计）**分离**但互补。关联由 `X-Request-ID` + 可选 `X-Correlation-ID`/`traceparent`。

### 12.2 维护命令、自检与调试路径

| Maintenance API / Command / Diagnostic ID | 执行位置、入口、目标、权限 | 完整请求/语法与结果/错误契约 | 施加/回读点及覆盖 | 依赖/占用/恢复退出 | 验证 |
|---|---|---|---|---|---|
| 联合诊断 `joint-diagnose.sh` | 消费方主机；operator | 入参 = `x-request-id`；结果 = trace/snapshots | 只读查询 | 依赖 LLMTier 诊断 API | T-OBS-TRACE |
| 全局开关 `GET/PATCH /v1/diagnostics` | LLMTier 管理面；operator | PATCH = `snapshots_enabled`/`stats_enabled`；结果 = 开关状态；错误 401/403 | 施加=开关；回读=状态 | 默认关；无危险控制 | T-OBS-SWITCH |
| 诊断页面 `/ui/diagnostics` | 浏览器 → LLMTier；operator | 4 tabs：快照/统计/注入/Trace | 只读/切换 | 依赖各诊断 API | 组合 |

## 13. 配置、兼容与部署

开关与注入配置存于存储；**默认关闭**。保留期 7 天为配置项。部署随单一实例；清理任务在应用内定时运行。

## 14. 跨责任单元分解与接口分配（下级设计输入）

本章是**要求侧**：把本机制分解到各责任单元（LLMTier 为纯软件，责任单元 = 软件模块），说明每个对象必须负责什么、提供什么接口。下级模块设计在附录"机制承接表"逐条记录**落实侧**。

### 14.1 参与方到架构对象映射

| 机制参与方（§3） | 责任单元/Owner | 架构对象 ID / 类型 / 层或领域 | 下级设计文档 | 在本机制中的主责与非职责 |
|---|---|---|---|---|
| 能力提供 | LLMTier | `libdiag`（基础层）| `llmtier-diagnostics-design.md` | 开关/注入/记录读写；不改推理契约 |
| 查询与呈现 | Observability / LLMTier | 诊断管理面（业务层）| `llmtier-diagnostics-design.md` | 查询、切换开关；不直读库 |
| 事件产生 | Inference / LLMTier | 请求路径集成（业务层）| `llmtier-core-design.md` | 按配置注入、写事实；不改推理结果 |
| 入口 | HTTP API / LLMTier | HTTP Adapter（入口层）| `llmtier-core-design.md` | 诊断路由、关联标识透传/回显 |
| 页面 | Web UI / LLMTier | `/ui/diagnostics`（入口层）| `llmtier-webui-design.md` | 4 tabs + 全局开关；不直读库 |
| 存储 | LLMTier | Store（基础层）| `llmtier-core-design.md` | 4 张表 |

### 14.2 功能和步骤到责任单元分配

| Capability / Process Step / Constraint | 主责架构对象 | 协作对象 | 必须产生或消费的结果 | 固定行为 / 本地自由度 | 组合验证责任 |
|---|---|---|---|---|---|
| Step 1 生成/接收 request_id、关联标识 | HTTP Adapter | — | request_id、回显头 | 头解析实现可自定 | 契约 |
| Step 2 validated trace | Inference | `libdiag` | trace 事件 | fail-open 固定 | T-OBS-TRACE |
| Step 3 读注入并生效（CAP-OBS-5）| Inference | `libdiag` | delay/fault/limit | 注入类型固定 | T-OBS-INJECT |
| Step 4 上游快照 + 时延（CAP-OBS-1/2）| Inference | `libdiag` | 快照 + 统计 | 脱敏/截断固定 | T-OBS-SNAP |
| Step 5 终态 trace；注入标注（C-OBS-4）| Inference | `libdiag`、M-METER | trace + `source=injected` | 标注固定 | T-OBS-INJECT |
| Step 6 查询/开关/页面（C-OBS-1）| Observability | HTTP Adapter、Web UI | 查询结果 | 默认关固定 | T-OBS-SWITCH |
| 清理 | `libdiag` | Store | 删除 7 天前 | 保留期固定 | — |

### 14.3 责任单元间接口契约

| 接口成员 ID / 固定 baseline | 提供对象 | 全部消费对象 | 调用/事件形态 | 本机制固定的语义与错误 | 期限/取消/重复及边界 |
|---|---|---|---|---|---|
| `snapshots_enabled` / `stats_enabled` | `libdiag` | Inference、Observability | 函数 | 开关判定 | 默认关 |
| `capture_snapshot` / `record_latency` / `record_trace` | `libdiag` | Inference | 函数 | 写事实 | 记 warning、不抛 |
| `get_enabled_injections(deployment_id)` | `libdiag` | Inference | 函数 | 生效注入 | — |
| `get_trace` / `list_snapshots` / `get_stats` | `libdiag` | Observability | 函数 | 查询 | — |
| `get/update_diagnostics_settings`、`upsert_injections` | `libdiag` | Observability | 函数 | 切换 | — |

### 14.4 下级设计输入清单

| 下级要求 ID | 承接对象 ID / 下级设计文档 | 来源 Capability / Step / Constraint / 接口成员 | 必须负责的行为与保证 | 必须提供/消费的接口 | 下级必须展开的问题 | 允许自行决定的范围 | 本地验证 / 组合验证交接 |
|---|---|---|---|---|---|---|---|
| R-OBS-01 | `libdiag` · `llmtier-diagnostics-design.md` | C-OBS-3、Step 2/3/4/5、interface `DiagnosticService` 全部 | 开关/注入/记录底层读写、脱敏、fail-open | `capture_snapshot`/`record_latency`/`record_trace`/`get_enabled_injections`/查询 | 存储布局、缓存/LRU、TTL、截断 | 存储/聚合实现 | 系统用例 |
| R-OBS-02 | Observability · `llmtier-diagnostics-design.md` | C-OBS-1/5、Step 6 | 查询与呈现、开关切换 | 诊断路由 | 授权、页面 | 呈现实现 | T-OBS-SWITCH |
| R-OBS-03 | Inference · `llmtier-core-design.md` | C-OBS-2/4、Step 3/4/5 | 按配置注入、写事件、`source=injected` | 集成点 | 注入执行点、fail-open 包裹 | 集成实现 | T-OBS-INJECT |
| R-OBS-04 | HTTP Adapter · `llmtier-core-design.md` | Step 1 | 诊断路由、关联标识透传/回显 | 路由 | 头解析、错误映射 | 解析实现 | 契约 |
| R-OBS-05 | Web UI · `llmtier-webui-design.md` | CAP-OBS-3 | `/ui/diagnostics` 4 tabs + 开关 | 页面 | 呈现（不直读库）| 呈现实现 | 组合 |
| R-OBS-06 | Store · `llmtier-core-design.md` | §8 4 张表 | 4 张表事务 | Store | schema/迁移 | 存储实现 | 系统用例 |

**约束**：下游不得记录 Secret/正文；观测不得阻断推理；新增观测维度须回写本节并关联模块设计。

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

| Test / Constraint | 输入与预置事实 | arm/hit/release | 独立 Oracle |
|---|---|---|---|
| T-OBS-SWITCH / C-OBS-1 | 开/关 snapshots/stats | 切换 | 关闭时零写入 |
| T-OBS-SNAP / CAP-OBS-1 | 一次上游调用 | — | 快照字段与脱敏正确 |
| T-OBS-STATS / CAP-OBS-2 | 多次请求 | — | P50/P95/计数正确 |
| T-OBS-INJECT / CAP-OBS-5 | 四类注入 | 配/清 | delay/fault/limit 生效；`source=injected` |
| T-OBS-TRACE / CAP-OBS-6 | 固定 request_id | — | stages 有序 + usage |
| T-OBS-FAILOPEN / C-OBS-2 | 注入库写失败 | — | 推理结果不变 |

### 15.2 环境部署、复位、并发隔离与自动化

测试实例独立库；**测试中注入默认关闭**；并发用例核验缓存/写入与推理隔离。

### 15.3 组合验收、启用与旧机制退出

随 Phase 化实现启用；流注入见 `LT-OPEN-05`。组合验收 = Piko 联调（`joint-diagnose.sh`）。

## 16. 风险、未决问题与决定

| ID | 类别 | 影响 | 下一步 | 状态 |
|---|---|---|---|---|
| LT-OPEN-04 | 决定 | 四类数据各归 1 张表，保留 7 天 | 已采用 | 已定 |
| LT-OPEN-05 | 未决 | 流注入需改造流式输出 | 确认实现方案 | 未决 |
| R-OBS-1 | 风险 | 统计为内存、可丢 | 明示非账本语义 | 观察 |

## A. 输入基线、适用性与图文规则

- 输入：系统设计 §11.3、`docs/99_reference/handoff-piko-joint-obs.md`（Piko 联调输入）。
- 适用性：纯软件、单节点、默认关闭的可观测机制。§4.2（二进制 ABI）不适用；§8.1（租约）不适用（清理代替释放）。
- 图：时序图（§6）表达逐阶段记录与查询。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；`draft.3` 补实全部章节、增模块分解与不变量。修订见 Git。
