<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M004 Management 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `management` |
| Document Version | `0.1.0-draft.2` |
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
| Canonical Path | `docs/40_module_design/management-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 单元摘要：为什么存在

| 项目 | 内容 |
|---|---|
| 模块编号 / 正式英文名称 | **M004** / Management |
| 直属父对象编号 / 名称 | LLMTier 软件系统（本项目无子系统）|
| 父设计 Document ID / 登记位置 | `llmtier-system-design` / 系统设计 §3.2（唯一登记表）|
| 上级系统 / 父单元 | LLMTier 软件系统 |
| 解决的问题 | 配置从哪里来、如何校验与生效、如何审计；provider 账号用量与运行日志如何被 operator 查询——把"配置权威 + 管理动作 + 证据查询"集中到一处 |
| 提供的能力 | provider/deployment/逻辑等级配置的事务化维护（bootstrap + CRUD + ETag）；探测并落库健康；用量查询与范围清空；审计/日志/统计查询；provider 账号用量快照 |
| 主要使用者 | M001 HTTP API（管理面调用）、M002 Web UI、M003 Inference（只读等级能力）|
| 不负责 | 模型推理（M003）；账本持久化机制本身（M-METER，由 M007 落库）；观测记录（M005/M006）|

### 1.1 继承的上级约束与落实方式

#### 1.1.1 `CON-CFG-001` · 初始化后 SQLite 是唯一运行权威
- **上级基线与决定状态**：系统设计 §3.4/§10；已采用
- **适用条件**：bootstrap 之后
- **继承预算或行为保证**：文件不再影响运行；不双写
- **可自行选择 / 不可改变**：存储布局可自选；唯一权威不可变
- **本地落实 / 内部再分配**：I1 配置权威；§8
- **验证方法与结果 / 证据**：`VRC-MGMT-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.2 `CON-CFG-002` · Secret 只存引用
- **上级基线与决定状态**：系统设计 §10；已采用
- **适用条件**：provider 写入
- **继承预算或行为保证**：明文不入库/不入响应/不入 UI
- **可自行选择 / 不可改变**：引用形式固定（`env:`/`file:`）
- **本地落实 / 内部再分配**：I1 校验；§8、§11
- **验证方法与结果 / 证据**：`VRC-MGMT-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.3 `CON-CFG-003` · 先验证再原子推进
- **上级基线与决定状态**：系统设计 §3.4；已采用
- **适用条件**：配置发布
- **继承预算或行为保证**：引用/能力不变量通过才提交；失败不改 active snapshot
- **可自行选择 / 不可改变**：事务实现可自选；原子性不可变
- **本地落实 / 内部再分配**：I1 发布事务；§8、§10
- **验证方法与结果 / 证据**：`VRC-MGMT-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.4 `CON-CFG-004` · 变更失败回滚
- **上级基线与决定状态**：系统设计 §3.4；已采用
- **适用条件**：任意管理变更
- **继承预算或行为保证**：失败保持旧版本
- **可自行选择 / 不可改变**：—
- **本地落实 / 内部再分配**：I1 + Store 事务；§10
- **验证方法与结果 / 证据**：`VRC-MGMT-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.5 `CON-CFG-005` · 初始化失败 not_ready
- **上级基线与决定状态**：系统设计 §10；已采用
- **适用条件**：启动引导
- **继承预算或行为保证**：引导失败服务 not_ready
- **可自行选择 / 不可改变**：—
- **本地落实 / 内部再分配**：I3 引导；§10
- **验证方法与结果 / 证据**：`VRC-MGMT-003`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.6 `CON-METER-004` · 查询稳定分页
- **上级基线与决定状态**：机制 M-METER §3.1；已采用
- **适用条件**：用量/审计/日志分页
- **继承预算或行为保证**：snapshot 冻结；cursor 复核 principal/filter
- **可自行选择 / 不可改变**：cursor 实现可自选；冻结不可变
- **本地落实 / 内部再分配**：I2 分页；§8
- **验证方法与结果 / 证据**：`VRC-MGMT-004`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M-METER 一致

## 2. 需求、功能与验收条件

### 2.1 `F-MGMT-BOOTSTRAP` · 首次引导
- **上级需求 / Constraint ID**：`CON-CFG-001/2/3/5`；机制 M-CONFIG CAP-CFG-BOOTSTRAP
- **调用方**：启动（`__main__`）
- **输入与前提**：空库 + 显式 settings 路径
- **行为**：迁移 schema → 校验字段/ID/引用/Secret 可达 → 单事务写入 providers/deployments/levels + `bootstrap_sha256` + 审计
- **输出**：库内 Registry + hash
- **错误与边界**：503 `bootstrap_required`/`bootstrap_invalid`；失败回滚、not_ready
- **验收条件**：空库无路径 → 503；重复启动 no-op；非法引用回滚

### 2.2 `F-MGMT-CRUD` · 配置增删改查
- **上级需求 / Constraint ID**：`CON-CFG-001/3/4`；机制 M-CONFIG CAP-CFG-CRUD
- **调用方**：M001（`/tier/admin/v1/providers`、`/tier/admin/v1/deployments`、`/tier/admin/v1/service-levels`）
- **输入与前提**：operator 凭据；`If-Match`（PATCH/DELETE）
- **行为**：事务化 CRUD + 能力/不变量校验 + 审计；`version+1`
- **输出**：视图 + `ETag`
- **错误与边界**：400/404/409 `resource_conflict`/`resource_in_use`/412 `version_conflict`/409 `fixed_service_level`
- **验收条件**：ETag 串行化；引用保护；能力交集正确

### 2.3 `F-MGMT-PROBE` · 探测
- **上级需求 / Constraint ID**：机制 M-CONFIG（探测）
- **调用方**：M001（`POST /v1/probes`）
- **输入与前提**：`{deployment_id, confirm_external_call=true}`
- **行为**：适配器 `probe()` → `apply_probe_result` 写健康 → 审计
- **输出**：`{deployment_id, status, checked_at, may_have_incurred_cost}`
- **错误与边界**：400 `confirmation_required`；404 `not_found`
- **验收条件**：未确认不触网；探测结果落库

### 2.4 `F-MGMT-USAGE-QUERY` · 用量查询
- **上级需求 / Constraint ID**：`CON-METER-004`；机制 M-METER CAP-METER-QUERY/ADMIN
- **调用方**：M001（`GET /v1/usage`）
- **输入与前提**：`from/to`（`[from,to)`）、可选 `model/request_id/cursor/limit`
- **行为**：首屏建 snapshot 冻结成员；后续页按冻结视图
- **输出**：`{data,next_cursor,has_more,snapshot_id,snapshot_at}`
- **错误与边界**：400 `invalid_request`/`cursor_expired`；403；503 `usage_store_unavailable`
- **验收条件**：同 request 只取最高版本；旧页不受后续更正影响

### 2.5 `F-MGMT-USAGE-RESET` · 范围清空
- **上级需求 / Constraint ID**：机制 M-METER CAP-METER-RESET
- **调用方**：M001（`DELETE /v1/usage`，admin）
- **输入与前提**：可选 `model`/`deployment_id`
- **行为**：单事务删除义务/版本/head/绑定（`_del_pairs`）
- **输出**：`{deleted}`
- **错误与边界**：403
- **验收条件**：范围与计数一致；孤儿清理

### 2.6 `F-MGMT-STATS` · 统计聚合
- **上级需求 / Constraint ID**：机制 M-METER（统计视图）
- **调用方**：M001（`GET /v1/stats`）
- **输入与前提**：`from/to/group_by ∈ {tier,deployment}`
- **行为**：按最高 record version 聚合 calls/tokens
- **输出**：`{from,to,group_by,data[]}`
- **错误与边界**：400 `invalid_request`（group_by/缺时间）
- **验收条件**：只聚合 head 版本；measured/unknown 分列

### 2.7 `F-MGMT-AUDIT` · 审计查询
- **上级需求 / Constraint ID**：机制 M-CONFIG（审计）
- **调用方**：M001（`GET /v1/audit`）
- **输入与前提**：`limit`
- **行为**：按时间倒序分页
- **输出**：脱敏 `{id,actor,action,target,result,created_at}`
- **错误与边界**：—
- **验收条件**：不含 prompt/output/Secret

### 2.8 `F-MGMT-LOGS` · 运行日志查询
- **上级需求 / Constraint ID**：机制 M-OBS（日志）
- **调用方**：M001（`GET /v1/logs`）
- **输入与前提**：`from/to` + 可选 `level/module/request_id`
- **行为**：查询**写入前已脱敏**的结构化日志
- **输出**：`{data[]}`
- **错误与边界**：400（缺时间）；503
- **验收条件**：脱敏字段；不返回正文/凭据

### 2.9 `F-MGMT-ACCOUNT-USAGE` · provider 账号用量
- **上级需求 / Constraint ID**：机制 M-CONFIG（账号用量只读）
- **调用方**：M001（`GET`/`POST /v1/providers/{id}/usage`）
- **输入与前提**：GET 只读快照；POST 需 `confirm_external_call=true`
- **行为**：GET 读库；POST 调 provider usage API 并持久化快照
- **输出**：账号用量快照（window/percent/reset_at）
- **错误与边界**：400 `invalid_request`；404 `not_found`；未确认 POST → 400 `confirmation_required`；快照 `unavailable`+`error`
- **验收条件**：GET 不触网；缺字段保持 Unknown

## 3. UI、CLI、服务端点或设备操作面

**N/A — 本模块没有直接操作面。** 管理面端点由 **M001 HTTP API** 暴露、由 **M002 Web UI** 呈现；M004 只提供内部管理服务对象。Tailoring 依据：系统设计 §3.2 规定入口层终止 HTTP/SSE。

## 4. 外部边界与依赖

#### 4.1 `DEP-M001` · HTTP API（调用方）
- **角色 / 运行位置 / Owner**：调用方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：`Registry.*`、`AdminService.*`、`UsageRecorder.page/reset_usage`、`AuditLog.page`、`OperationalLog.page`、`AccountUsageService.*`
- **契约 authority / 版本 / selector**：本文 §9；对外 OpenAPI 由 M001 映射
- **同步方式 / timeout / 生命周期**：同步；请求级
- **不可用或失败影响 / 责任出口**：`ApiError` 冒泡到 M001

#### 4.2 `DEP-M003` · Inference（探测经适配器）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：`providers/openai.py`、`providers/local.py`（探测/列模型）
- **本模块提供**：—
- **契约 authority / 版本 / selector**：`llmtier-inference-stream-mechanism` §14.4 `R-INF-05`
- **同步方式 / timeout / 生命周期**：同步；探测 5 s
- **不可用或失败影响 / 责任出口**：探测失败 → `unhealthy`

#### 4.3 `DEP-M007` · util（存储）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：`Store.transaction/one/all/connection`
- **本模块提供**：—
- **契约 authority / 版本 / selector**：`llmtier-config-lifecycle-mechanism` §14.4 `R-CFG-03`
- **同步方式 / timeout / 生命周期**：同步
- **不可用或失败影响 / 责任出口**：存储错误 → 请求失败

#### 4.4 `DEP-M005/M006` · Observability（诊断开关）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：诊断开关/注入（管理动作转发）
- **本模块提供**：—
- **契约 authority / 版本 / selector**：`llmtier-observability-mechanism` §14.4 `R-OBS-02`
- **同步方式 / timeout / 生命周期**：同步、fail-open
- **不可用或失败影响 / 责任出口**：观测不可用不阻塞管理面

#### 4.5 `DEP-USAGE-API` · Provider 账号用量 API（外部）
- **角色 / 运行位置 / Owner**：外部依赖；进程外；MiniMax / 火山
- **本模块调用或消费**：`GET https://www.minimaxi.com/v1/token_plan/remains`；火山 `GetCodingPlanUsage`
- **本模块提供**：—
- **契约 authority / 版本 / selector**：各 provider 官方 API
- **同步方式 / timeout / 生命周期**：同步 HTTP；15 s；显式刷新
- **不可用或失败影响 / 责任出口**：快照标 `unavailable`+`error`

## 5. 内部结构与实现位置

![M004 内部流程：管理动作与探测](../assets/diagrams/diagram-m004-management-flow.png)

[可编辑 SVG 源](../assets/diagrams/diagram-m004-management-flow.svg)

图 M004-P1 · P-ADMIN-MUTATE 与 P-PROBE 内部流程；成功/失败审计分支展开。

### 5.1 内部组成

#### 5.1.1 `I1` · 配置权威（Registry）
- **职责与非职责**：bootstrap、provider/deployment/level 事务 CRUD、能力交集、候选查询；不承载推理
- **输入、处理与输出**：管理命令 → 视图 + ETag / 候选
- **协作对象**：I3、I5、M007
- **文件 / symbol / 实现状态**：`registry.py` `Registry.*`；Implemented
- **拆分依据与替代方案代价**：配置权威与入口分离，避免文件热载双写歧义

#### 5.1.2 `I2` · 管理动作编排
- **职责与非职责**：`mutate`（审计包裹）、分页快照、统计聚合；不做具体 CRUD
- **输入、处理与输出**：`(actor, action, target, request_id, fn)` → 结果；`data → 页`
- **协作对象**：I1、I5、I6、I8
- **文件 / symbol / 实现状态**：`admin.py` `AdminService.mutate/page/stats`；Implemented
- **拆分依据与替代方案代价**：把"审计 + 成功/失败"统一包裹，避免各调用点漏审计

#### 5.1.3 `I3` · 引导
- **职责与非职责**：空库首次引导、校验、单事务写入、not_ready；不处理运行期变更
- **输入、处理与输出**：settings 路径 → Registry + hash
- **协作对象**：I1、M007
- **文件 / symbol / 实现状态**：`registry.py` `bootstrap_settings` + `app.py` 启动装配；Implemented
- **拆分依据与替代方案代价**：引导独立于 CRUD，保证"一次性"

#### 5.1.4 `I4` · 探测
- **职责与非职责**：适配器探活、健康落库、审计；不做计费探测
- **输入、处理与输出**：`(actor, body={deployment_id, confirm_external_call}, request_id)` → `{deployment_id, status, checked_at, may_have_incurred_cost}`
- **协作对象**：I1、I2、I5、M003 适配器
- **文件 / symbol / 实现状态**：`admin.py` `probe`、`health.py` `apply_probe_result`；Implemented
- **拆分依据与替代方案代价**：探测写 `deployments.health` + `probe_results`，与配置分离；健康四值（含 `degraded`）

#### 5.1.5 `I5` · 审计
- **职责与非职责**：脱敏审计写入与查询；不含 prompt/output/Secret
- **输入、处理与输出**：`(actor, action, target, result, request_id)` → 行
- **协作对象**：I1、I2、I4
- **文件 / symbol / 实现状态**：`audit.py` `AuditLog`；Implemented
- **拆分依据与替代方案代价**：审计经 `mutate` 传入的同一连接与 Registry 写**在同一事务**提交，动作与审计原子；查询独立

#### 5.1.6 `I6` · 运行日志
- **职责与非职责**：写入前脱敏（`_SENSITIVE`）、结构化查询；不含原始日志
- **输入、处理与输出**：`(level, module, event, message, request_id)` → 行
- **协作对象**：I2、M001/M003
- **文件 / symbol / 实现状态**：`logs.py` `OperationalLog`；Implemented
- **拆分依据与替代方案代价**：脱敏在写入前完成，查询侧不再兜底

#### 5.1.7 `I7` · 账号用量
- **职责与非职责**：显式刷新 provider 账号用量并持久化快照；不自动轮询、不 cookie 抓取
- **输入、处理与输出**：`(provider_id, confirm)` → 快照
- **协作对象**：M007、M004 I5
- **文件 / symbol / 实现状态**：`account_usage.py` `AccountUsageService`；Implemented
- **拆分依据与替代方案代价**：MiniMax（API Key）与火山（AK/SK 签名）分实现

#### 5.1.8 `I8` · 用量查询与清空
- **职责与非职责**：分页/清空/范围语义；具体账本语义归 M-METER
- **输入、处理与输出**：`(principal, cursor, …)` → 页；`(model, deployment)` → 计数
- **协作对象**：I2、M007
- **文件 / symbol / 实现状态**：`usage.py` `UsageRecorder.page/reset_usage`；Implemented
- **拆分依据与替代方案代价**：读取/清空与写入分离

### 5.2 内部调用过程

#### 5.2.1 `CALL-MUTATE` · 一次管理动作
- **入口与调用上下文**：M001 → `AdminService.mutate`（请求线程）
- **调用链**：`mutate` → `fn(conn)`（`Registry.create_*` / `update_*` / `delete_*` 或 `usage.reset_usage` 或 `diagnostics.set_*`）→ 同一连接写 `audit.record` + 事务提交后 `logs.record`
- **逐步传递的数据**：`(actor, action, target, request_id)`；`fn` 返回视图/计数/开关
- **返回、异常与清理**：成功 → 结果；异常 → 同一/新事务记 failed 后重抛
- **对应流程 / 接口 / 验证**：§7 P-ADMIN-MUTATE / `VRC-MGMT-002/004`

#### 5.2.2 `CALL-PROBE` · 一次探测
- **入口与调用上下文**：M001 → `AdminService.probe`
- **调用链**：`probe` → `get_deployment`/`get_provider` → `adapter.probe()` → `apply_probe_result` → `audit.record`
- **逐步传递的数据**：`deployment_id` → provider/endpoint/secret_ref → `bool` → 健康行
- **返回、异常与清理**：返回 `{status, checked_at}`；未确认 → 400
- **对应流程 / 接口 / 验证**：§7 P-PROBE / `VRC-MGMT-005`

#### 5.2.3 `CALL-QUERY` · 一次分页查询（用量/审计/日志）
- **入口与调用上下文**：M001 → `page` / `audit.page` / `logs.page`
- **调用链**：首屏建 `query_snapshots` 冻结 → 后续按 `ordinal` 读冻结视图
- **逐步传递的数据**：`(principal, cursor, filters)` → 冻结项
- **返回、异常与清理**：`{data, page}`；cursor 过期 → 400
- **对应流程 / 接口 / 验证**：§7 P-MGMT-QUERY / `VRC-MGMT-004`

### 5.3 文件间接口契约

> 本模块内部/跨模块文件交接逐项映射到 §9 的成员定义；签名、输入输出、错误与寿命以 §9 对应记录为唯一来源，本节不再复写。

| 内部契约 ID | provider → consumer | §9 成员 | 本文件责任 | 验证 |
|---|---|---|---|---|
| `IF-MGMT-01` | `app.py` → `registry.py` | §9.1 `IF-PROVIDERS`、`IF-DEPLOYMENTS`、`IF-LEVELS`、`IF-MGMT-REGISTRY` | 配置权威 CRUD/引导/候选查询 | `VRC-MGMT-001/002` |
| `IF-MGMT-02` | `app.py` → `admin.py` | §9.1 `IF-MGMT-ADMIN`、`IF-MGMT-QUERY`、`IF-MGMT-STATS` | 管理动作审计包裹、分页、统计 | `VRC-MGMT-002/004` |
| `IF-MGMT-03` | `admin.py` → `audit.py` / `logs.py` | §9.1 `IF-AUDIT-LOGS` | 脱敏审计/日志写入与查询 | `VRC-MGMT-003` |
| `IF-MGMT-04` | `admin.py` → `health.py` | §9.1 `IF-PROBES` | 探测结果落库 | `VRC-MGMT-005` |
| `IF-MGMT-05` | `app.py` → `account_usage.py` | §9.1 `IF-MGMT-ACCOUNT-USAGE` | 账号用量快照读/显式刷新 | `VRC-MGMT-006` |
| `IF-MGMT-06` | `app.py` → `usage.py` | §9.1 `IF-USAGE` | 账本分页与范围清空 | `VRC-MGMT-004` |

### 5.4 服务提供方式（条件适用）

- **运行载体与入口**：N/A + 依据 —— 嵌入式库，由 M001 进程内调用
- **并发/线程模型**：N/A + 依据 —— 使用调用方线程；写路径用 `Store.transaction(immediate=True)` 串行化
- **初始化、Ready、生效与停止**：引导在 `Application.__init__`（`bootstrap_settings` + `ensure_fixed_tiers`）；失败置 `bootstrap_error` 供 `/readyz`；成功后 deployments 初始 `health=unknown`，故 `/readyz` 为 `degraded` 直至探测出健康候选
- **宿主装配、失败和资源回收责任**：由 M001/启动装配；无自有线程/fd

### 5.5 依赖方向

- **允许方向**：M001 → M004 → {M003(适配器), M005/M006, M007, M008, 外部 usage API}
- **禁止方向与原因**：M004 不得回调 M001/M002；不得直接承载推理
- **循环/越层检查**：`registry.py`/`admin.py` 不 import `app.py`
- **变更影响**：`Registry` 变更影响 M003 候选与 M001 管理面

## 6. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0：主章“数据结构设计”，章内按**数据性质分类**。M004 为纯软件配置权威与管理服务，无 wire 自有报文、无设备；`6.4 通信报文`、`6.5 设备与 FPGA 表项` 不适用。继承结构（如 M008 `LogEvent`、M-METER `UsageView`）只定位原定义；本层拥有的结构逐项完整记录（Data/Type ID、用途与来源／逐字段／跨字段与寿命／合法与拒绝实例／验证），每个结构以真实名称作带编号小节标题。

**适用性**：6.1 公共基础类型与枚举 ✓｜6.2 业务与操作数据结构 ✓｜6.3 配置与规则数据结构 ✓｜6.4 通信报文 ✗（对外 wire 归 M001/OpenAPI）｜6.5 设备与 FPGA 表项 ✗（无设备）｜6.6 运行状态数据结构 ✓｜6.7 数据库表结构 ✓（authority = `util/migrations/*.sql`）｜6.8 错误码与错误结构 ✓（引用系统 Error ID）。

### 6.1 公共基础类型与枚举

**6.1.1 `CapabilityKey`（公共基础类型与枚举）**

```text
CapabilityKey {
  responses: bool,
  embeddings: bool,
  tools: bool,
  structured_outputs: bool,
  input_modalities: string[],
  output_modalities: string[],
  context_window: int?,
  max_output_tokens: int?,
  embedding_space_id: string?,
  embedding_dimensions: int[]?,
  embedding_max_batch_inputs: int?,
  embedding_max_input_tokens: int?
}
```

- **Data/Type ID、用途与来源**：

  `D-CAPABILITY`；provider/deployment/等级能力位，12 键固定集合；来源 `src/management/registry.py`，机器源 `interfaces/openapi`（`ModelCapabilities`）。

- **`responses`/`embeddings`/`tools`/`structured_outputs`**：

  必填布尔；分别表示是否支持对话、向量化、工具调用、结构化输出。

- **`input_modalities`/`output_modalities`**：

  必填字符串数组；输入/输出模态集合。

- **`context_window`/`max_output_tokens`**：

  必填字段、值可空整数；上下文与单次输出上限；不适用为 `null`。

- **`embedding_space_id`**：

  必填字段、值可空字符串；embedding 空间标识；非 embedding 能力为 `null`。

- **`embedding_dimensions`**：

  必填字段、值可空整数数组；允许维数集合。

- **`embedding_max_batch_inputs`/`embedding_max_input_tokens`**：

  必填字段、值可空整数；Embeddings 批量与输入上限。

- **跨字段与寿命**：

  键集合固定为 12；运行期 CRUD 写入要求 12 键齐备（缺键即非法），bootstrap 输入允许缺键并按默认值补齐后落库；等级能力 = 绑定 deployment 的能力**交集**（deployment 能力来自 deployment 自身，provider 不声明能力）；`Embedding-v1` 必须 embedding-only 且 space/dim/上限冻结；随配置行持久，版本随 `version`。

- **合法/拒绝实例**：

  合法：两成员共同 `responses=true`；拒绝：无共同能力 → `capability_conflict`。

- **验证**：

  `VRC-MGMT-002`；机器源 `openapi` `ModelCapabilities`。

**6.1.2 `Health`（公共基础类型与枚举）**

```text
enum Health { healthy, degraded, unhealthy, unknown }
```

- **Data/Type ID、用途与来源**：

  `D-CFG-HEALTH`；deployment 健康状态；来源 `src/management/registry.py` / `health.py`。

- **`healthy`**：

  探测通过。

- **`degraded`**：

  降级（部分可用/降权），保存或探测均可写入。

- **`unhealthy`**：

  探测失败。

- **`unknown`**：

  尚未探测（启动初值）。

- **跨字段与寿命**：

  只能由探测结果 `apply_probe_result`（接受 `healthy/degraded/unhealthy/unknown` 四值）或启动初始值写入；保存配置 ≠ 健康恢复；持久 `deployments.health`，探测覆盖。

- **合法/拒绝实例**：

  合法 `healthy`/`degraded`；边界：未探测 → `unknown`。

- **验证**：

  `VRC-MGMT-005`；`health.py`。

**6.1.3 `UsageProvider`（公共基础类型与枚举）**

```text
enum UsageProvider { minimax, volc, local, none }
```

- **Data/Type ID、用途与来源**：

  `D-CFG-USAGE-PROVIDER`；账号用量来源类型；来源 `src/management/account_usage.py`，bootstrap 由 provider `kind` 派生。

- **`minimax`**：

  经 MiniMax API Key 刷新。

- **`volc`**：

  经火山 AK-SK HMAC 签名刷新。

- **`local`**：

  本地来源，不触网。

- **`none`**：

  无账号用量，不触网。

- **跨字段与寿命**：

  决定刷新实现；`local`/`none` 不触网；持久 `provider_usage_profiles`。

- **合法/拒绝实例**：

  合法 `minimax`；边界：`local`/`none` → `not_refreshed`。

- **验证**：

  `VRC-MGMT-006`；`account_usage.py`。

**6.1.4 `RecordVersion` / `ETag`（公共基础类型与枚举）**

```text
RecordVersion {
  version: uint32,         // ≥1，单调 +1
  etag: string             // "<id>.v<version>"
}
```

- **Data/Type ID、用途与来源**：

  `D-CFG-VERSION-TAG`；记录版本与乐观并发标记；来源 `src/management/registry.py`。

- **`version`**：

  必填正整数，≥1，单调 `+1`。

- **`etag`**：

  必填字符串，格式 `"<id>.v<version>"`。

- **跨字段与寿命**：

  `If-Match` 必须精确匹配当前 ETag，否则 412；随配置行持久。

- **合法/拒绝实例**：

  合法 `"p1.v3"`；拒绝：过期 ETag → 412 `ERR-STALE`。

- **验证**：

  `VRC-MGMT-002`；`RULE-MGMT-ETAG`。

### 6.2 业务与操作数据结构

**6.2.1 `ProviderView`（业务与操作数据结构）**

```text
ProviderView {
  id: string,
  name: string,
  kind: string,
  endpoint: string,
  has_secret: bool,
  enabled: bool,
  usage: object,
  request_usage: object,
  version: uint32
}
```

- **Data/Type ID、用途与来源**：

  `D-PROVIDER`；provider 配置实体视图；来源 `src/management/registry.py` + OpenAPI。

- **`id`**：

  必填、非空字符串；稳定身份。

- **`name`**：

  必填字符串，全局唯一。

- **`kind`**：

  必填字符串；provider 类型（如 `cloud`/`local`）。

- **`endpoint`**：

  必填字符串；上游端点。

- **`has_secret`**：

  必填布尔；是否已配置 Secret；Secret 只存引用（`env:`/`file:`），不回显。

- **`enabled`**：

  必填布尔；是否参与路由。

- **`usage`/`request_usage`**：

  必填对象；账号用量与请求用量投影。

- **`version`**：

  必填正整数；见 §6.1.4。

- **跨字段与寿命**：

  持久（Store）；`version` 单调；`name` 唯一。

- **合法/拒绝实例**：

  合法：create provider 返回 201+ETag；拒绝：重名 → `ERR-CONFLICT`。

- **验证**：

  `VRC-MGMT-001/002`；`registry.py` + OpenAPI。

**6.2.2 `DeploymentView`（业务与操作数据结构）**

```text
DeploymentView {
  id: string,
  name: string,
  provider_id: string,
  backend_model: string,
  capabilities: CapabilityKey,
  enabled: bool,
  health: Health,
  version: uint32
}
```

- **Data/Type ID、用途与来源**：

  `D-DEPLOYMENT`；deployment 配置实体视图；来源 `src/management/registry.py` + OpenAPI。

- **`id`**：

  必填、非空字符串；稳定身份。

- **`name`**：

  必填字符串；显示名。

- **`provider_id`**：

  必填字符串；引用 §6.2.1 `ProviderView.id`。

- **`backend_model`**：

  必填字符串；上游模型名。

- **`capabilities`**：

  必填，取 §6.1.1 `CapabilityKey`，12 键齐备。

- **`enabled`**：

  必填布尔；Pause/Resume 经此字段。

- **`health`**：

  必填，取 §6.1.2 `Health`。

- **`version`**：

  必填正整数；见 §6.1.4。

- **跨字段与寿命**：

  持久（Store）；`version` 单调；`provider_id` 引用保护。

- **合法/拒绝实例**：

  合法：create 返回 201+ETag；拒绝：未知 `provider_id` → 400；被 tier 引用删除 → 409。

- **验证**：

  `VRC-MGMT-001/002`；`registry.py` + OpenAPI。

**6.2.3 `ServiceLevelView`（业务与操作数据结构）**

```text
ServiceLevelView {
  id: string,
  deployment_ids: string[],
  enabled: bool,
  capabilities: CapabilityKey,
  version: uint32
}
```

- **Data/Type ID、用途与来源**：

  `D-SERVICE-LEVEL`；逻辑等级（tier）配置实体视图；来源 `src/management/registry.py` + OpenAPI。

- **`id`**：

  必填字符串；固定 tier 名。

- **`deployment_ids`**：

  必填有序字符串数组；成员绑定，引用 §6.2.2 `DeploymentView.id`。

- **`enabled`**：

  必填布尔；是否参与路由。

- **`capabilities`**：

  必填，取 §6.1.1 `CapabilityKey`，等于成员能力交集。

- **`version`**：

  必填正整数；见 §6.1.4。

- **跨字段与寿命**：

  持久（Store）；固定 7 Tier；成员顺序稳定；`version` 单调。

- **合法/拒绝实例**：

  合法：成员能力有交集；拒绝无共同能力 → 409 `capability_conflict`/`embedding_space_conflict`。

- **验证**：

  `VRC-MGMT-002`；`RULE-MGMT-CAPS`。

**6.2.4 `AuditEvent`（业务与操作数据结构）**

```text
AuditEvent {
  id: string,
  actor: string,
  action: string,
  target: string,
  result: string,          // success | failed
  created_at: timestamp,
  request_id: string?
}
```

- **Data/Type ID、用途与来源**：

  `D-AUDIT-EVENT`；一次管理动作的脱敏审计行；authority `audit_events` + `src/management/audit.py`。

- **`id`**：

  必填、非空字符串；审计行身份。

- **`actor`**：

  必填字符串；principal_id。

- **`action`**：

  必填字符串；动作名（如 `providers.create`）。

- **`target`**：

  必填字符串；目标对象。

- **`result`**：

  必填字符串，∈ {`success`,`failed`}。

- **`created_at`**：

  必填时间戳；动作时刻。

- **`request_id`**：

  可空字符串；关联请求身份。

- **跨字段与寿命**：

  不含 prompt/output/Secret；管理动作成功/失败均写；持久，只追加；I5 写、I2 读。

- **合法/拒绝实例**：

  合法 `{action:"providers.create",result:"success"}`；边界：动作失败 → `failed`。

- **验证**：

  `VRC-MGMT-003`；`audit.py`。

**6.2.5 `QuerySnapshot`（业务与操作数据结构）**

```text
QuerySnapshot {
  snapshot_id: string,
  principal_id: string,
  snapshot_kind: string,
  filter_digest: string,
  authorization_digest: string,
  created_at: timestamp,
  expires_at: timestamp,
  items: [{ ordinal: int, request_id: string, record_version: int?, frozen_view_json: string, etag: string? }]
}
```

- **Data/Type ID、用途与来源**：

  `D-MET-QUERY-SNAPSHOT`；分页冻结快照；authority `query_snapshots` + `query_snapshot_items`，来源 `admin.py`/`usage.py`。

- **`snapshot_id`**：

  必填、非空字符串；快照身份。

- **`principal_id`**：

  必填字符串；权限隔离键。

- **`snapshot_kind`**：

  必填字符串；快照类别。

- **`filter_digest`**：

  必填字符串；过滤条件摘要。

- **`authorization_digest`**：

  必填字符串；授权主体（principal 或 `admin`）摘要，**仅存储**；cursor 复核实际比较 `principal_id`（非 admin 时）与 `filter_digest`，不复核本摘要。

- **`created_at`/`expires_at`**：

  必填时间戳；创建与到期时刻（TTL 10 分钟）。

- **`items[].ordinal`/`request_id`/`record_version`/`frozen_view_json`/`etag`**：

  必填整数/字符串/可空整数/字符串/可空字符串；冻结项顺序、关联账本身份（版本/ETag）与视图。

- **跨字段与寿命**：

  TTL 10 分钟；同一主键的后续页按 `ordinal` 读冻结视图；cursor 复核 `principal_id`（非 admin）与 `filter_digest`，不复核 `authorization_digest`；到期 → `ERR-CURSOR`。

- **合法/拒绝实例**：

  合法：首屏后更正旧页不变；边界：过期 cursor → 400。

- **验证**：

  `VRC-MGMT-004`；`RULE-MGMT-SNAPSHOT`。

**6.2.6 `AccountUsageSnapshot`（业务与操作数据结构）**

```text
AccountUsageSnapshot {
  provider: string,        // usage-provider 类别：minimax | volc | local | none
  source: string,          // credentials_missing | provider_api | provider_api_error | store | quota_config | unsupported
  status: string,          // ok | unavailable | not_refreshed | unlimited | unsupported
  windows: object[],
  checked_at: timestamp,
  error: string?
}
```

- **Data/Type ID、用途与来源**：

  `D-ACCOUNT-SNAPSHOT`；provider 账号用量快照；authority `provider_usage_snapshots` + `src/management/account_usage.py`。

- **`provider`**：

  必填字符串；usage-provider 类别，取 §6.1.3 `UsageProvider`（`minimax`/`volc`/`local`/`none`），非 provider 记录 id。

- **`source`**：

  必填字符串，∈ {`credentials_missing`,`provider_api`,`provider_api_error`,`store`,`quota_config`,`unsupported`}；快照来源/失败类别。

- **`status`**：

  必填字符串，∈ {`ok`,`unavailable`,`not_refreshed`,`unlimited`,`unsupported`}。

- **`windows`**：

  必填数组；用量窗口。

- **`checked_at`**：

  必填时间戳；刷新时刻。

- **`error`**：

  可空字符串；上游失败摘要（脱敏）。

- **跨字段与寿命**：

  缺失字段保持 Unknown（不填 0）；GET 只读不触网；POST 需 `confirm_external_call=true`；持久（每 provider 一行），显式刷新覆盖。

- **合法/拒绝实例**：

  合法：`status=ok` + `source=provider_api`；边界：上游失败 → `status=unavailable` + `source=provider_api_error`；未刷新 → `status=not_refreshed` + `source=store`；`local` 刷新 → `status=unlimited` + `source=quota_config`。

- **验证**：

  `VRC-MGMT-006`；`account_usage.py`。

**6.2.7 `LogEvent`（业务与操作数据结构，继承 M008 §6.2）**

```text
LogEvent {
  id: string,
  created_at: timestamp,
  level: string,
  module: string,
  event: string,
  message: string,         // ≤512，已脱敏
  request_id: string?
}
```

- **Data/Type ID、用途与来源**：

  `D-LOG-EVENT`；写前脱敏的运行日志行；本层经 M008 `OperationalLog.page` 读取并整形。

- **字段**：

  与 M008 §6.2.1 `LogEvent` 相同，字段与脱敏规则由 M008 §6.2/§8.1 维护，本层不复制第二份 authority。

- **跨字段与寿命**：

  只读；持久归 M008 `operational_logs`。

- **合法/拒绝实例**：

  合法：脱敏日志行；边界：无匹配 → `data=[]`。

- **验证**：

  `VRC-MGMT-003`；来源 `log-design.md` §6.2。

**6.2.8 `UsageView`（业务与操作数据结构，继承 M-METER）**

```text
UsageView {
  request_id: string,
  record_version: uint32,
  model: string,
  usage: object,
  measurement_status: string
}
```

- **Data/Type ID、用途与来源**：

  `D-MET-USAGE-VIEW`；账本用量行/分页投影（同 `request_id` 只取最高 `record_version`）；字段 authority = M-METER 与 OpenAPI，本层只读/清空。

- **字段**：

  与 M-METER 账本视图一致，本层只记录投影用途，不复制字段定义。

- **跨字段与寿命**：

  只读；`reset_usage` 时按范围清空。

- **合法/拒绝实例**：

  合法：最高版本行；边界：unknown 不补零。

- **验证**：

  `VRC-MGMT-004`；`usage.py`。

### 6.3 配置与规则数据结构

**6.3.1 `BootstrapConfig`（配置与规则数据结构）**

```text
BootstrapConfig {
  providers: ProviderSpec[],
  deployments: DeploymentSpec[],
  service_levels: ServiceLevelSpec[]
}
```

- **Data/Type ID、用途与来源**：

  `D-CFG-SETTINGS`；空库首次引导的 settings 输入；authority `config/settings.json`，语义权威 = M004 `bootstrap_settings`。

- **`providers`/`deployments`/`service_levels`**：

  必填数组；字段/引用规则见 M004 §2.1。deployment `capabilities` 允许缺键（缺省补默认值）后落库；`service_levels` 未列出的固定 Tier 以空成员/空能力补齐。

- **跨字段与寿命**：

  仅在空库读取一次；先验证（字段/ID/引用/Secret 可达）再单事务写入；不双写；文件随仓库，运行期权威在 SQLite。

- **合法/拒绝实例**：

  合法：合法引用被写入 + `bootstrap_sha256` + 审计；拒绝：非法引用回滚并 `not_ready`。

- **验证**：

  `VRC-MGMT-001`；`registry.py` + M004 §2.1。

### 6.6 运行状态数据结构

**6.6.1 `BootstrapState`（运行状态数据结构）**

```text
BootstrapState {
  bootstrap_error: string?,     // 供 /readyz
  bootstrap_sha256: string      // 已写入 settings 指纹
}
```

- **Data/Type ID、用途与来源**：

  `D-CFG-BOOTSTRAP-STATE`；进程引导状态事实；来源 `src/http_api/app.py` 启动装配 + `registry.py`。

- **`bootstrap_error`**：

  可空字符串；引导失败原因，供 `/readyz`；成功为 `null`。

- **`bootstrap_sha256`**：

  必填字符串；已写入 settings 指纹。

- **跨字段与寿命**：

  引导失败置 `bootstrap_error`、服务 `not_ready`、不接流量；重复启动 no-op；进程级，随启动。

- **合法/拒绝实例**：

  合法：引导成功可接流量；边界：非法 settings → `not_ready`（`ERR-BOOT`）。

- **验证**：

  `VRC-MGMT-001/003`；`app.py` + `registry.py`。

**6.6.2 `QuerySnapshotLifecycle`（运行状态数据结构）**

```text
QuerySnapshotLifecycle {
  snapshot_id: string,
  expires_at: timestamp,
  ordinal: int              // 读游标
}
```

- **Data/Type ID、用途与来源**：

  `D-MET-QUERY-SNAPSHOT` 的运行时生命周期；来源 `src/management/admin.py`。

- **`snapshot_id`**：

  必填字符串；快照身份。

- **`expires_at`**：

  必填时间戳；到期时刻。

- **`ordinal`**：

  必填整数；读游标。

- **跨字段与寿命**：

  写入一次、按 `ordinal` 只读；到期或 principal 不符 → `ERR-CURSOR`；TTL 10 分钟，到期废弃。

- **合法/拒绝实例**：

  合法：续页命中；边界：过期 → 400。

- **验证**：

  `VRC-MGMT-004`；`admin.py`。

### 6.7 数据库表结构

Authority = `util/migrations/001_initial.sql`、`002_observability.sql`（由 M007 `migrate()` 执行）。本模块拥有下列表（`operational_logs` 归 M008、观测 6 表归 M006）；表间为多对象比较，按矩阵表达：

| 表 | 主键 / 唯一 | 写入者 / 读者 | 说明 |
|---|---|---|---|
| `providers` | `id` / `name` UNIQUE | I1 / M001,M003 | 配置权威 |
| `deployments` | `id` | I1 / M001,M003 | 含 `health`、`enabled` |
| `service_levels` | `id` | I1 / M001,M003 | 固定 7 Tier |
| `service_level_deployments` | `(service_level_id,deployment_id)` + UNIQUE`(service_level_id,ordinal)` | I1 | 成员绑定 |
| `deployment_runtime_profiles` | `deployment_id` | I1 | 并发/限流 profile |
| `provider_usage_profiles` | `provider_id` | I1 | `usage_provider` |
| `provider_usage_snapshots` | `provider_id` | I7 / M001 | 账号用量快照 |
| `provider_request_bindings` | `(principal_id,request_id)` | I8 / M-METER | 绑定 |
| `usage_obligations` | `(principal_id,request_id)` | I8 / M-METER | unknown 义务 |
| `usage_record_versions` | `(principal_id,request_id,record_version)` | I8 / M-METER | 只追加版本 |
| `usage_heads` | `(principal_id,request_id)` | I8 / M-METER | 最高版本指针 |
| `query_snapshots` | `snapshot_id` | I2/I8 / I2 | 分页冻结（含 `authorization_digest`，TTL） |
| `query_snapshot_items` | `(snapshot_id,ordinal)` | I2/I8 / I2 | 冻结项（`request_id`/`record_version`/`etag`） |
| `probe_results` | `deployment_id` | I4 / M001 | 探测结果 |
| `audit_events` | `id` | I5 / I2 | 审计 |

- **约束 / 不变量**：写经 `Store.transaction(immediate=True)`；`version` 乐观并发；引用保护（不级联删除）；`record_version` 只追加。
- **实例**：合法：CRUD 事务提交；拒绝：唯一冲突回滚 → `ERR-CONFLICT`。
- **来源 / 验证**：`util/migrations/*.sql`；`VRC-MGMT-001/002/003/004`。

### 6.8 错误码与错误结构

本模块**不新增公共错误码**；对外错误引用系统目录（`llmtier-system-design` §8.8）：

| 本层错误 | 条件 | 系统 Error ID | 合法下一步 |
|---|---|---|---|
| `ApiError(404,"not_found")` | 未知 provider/deployment/level | `ERR-NOTFOUND` | 修 id |
| `ApiError(400,"invalid_request")` | 字段/`group_by`/时间窗非法 | `ERR-REQ-VALIDATION` | 修请求 |
| `ApiError(409,"resource_conflict")` | `name` 唯一冲突 | `ERR-CONFLICT` | 改名 |
| `ApiError(409,"resource_in_use")` | 被引用删除 | `ERR-INUSE` | 先解绑 |
| `ApiError(412,"version_conflict")` | `If-Match` 过期 | `ERR-STALE` | 重新 GET |
| `ApiError(400,"cursor_expired")` | cursor 失效/不匹配 | `ERR-CURSOR` | 重开查询 |
| `ApiError(400,"confirmation_required")` | 缺二次确认 | `ERR-CONFIRM` | 补确认 |
| `ApiError(503,"bootstrap_required"/"bootstrap_invalid")` | 引导失败 | `ERR-BOOT` | 修正后重启 |
| `ApiError(503,"usage_store_unavailable")` | 存储不可用 | `ERR-STORE` | 稍后重试 |

- **约束 / 不变量**：管理动作失败回滚 + 审计 `failed`；读失败 503（不伪装空页）；不泄露存在性。
- **实例**：拒绝：删除在用 provider → 409 `ERR-INUSE`；边界：缺确认探测 → 400 `ERR-CONFIRM`。
- **来源 / 验证**：`registry.py`/`admin.py` + 系统 §8.8；`VRC-MGMT-001..006`。

## 7. 主流程与数据流

![M004 内部流程：管理动作与探测](../assets/diagrams/diagram-m004-management-flow.png)

[可编辑 SVG 源](../assets/diagrams/diagram-m004-management-flow.svg)

图 M004-P1 · P-ADMIN-MUTATE 与 P-PROBE：管理动作统一经审计包裹（成功/失败分支）；探测写健康并审计。

**内部流程正文**：管理动作由 M001 调用 `mutate`，内部在**同一事务**执行 `fn(conn)`（Registry 事务 / `reset_usage` / 诊断开关）并写 `success` 审计，提交后写 info 日志并返回结果；失败记 `failed` 审计与 warning 日志后重抛，`fn` 本身在 Store 事务内保证回滚（`atomic=False` 仅供带外部调用的账号刷新使用）。探测由 `probe` 二次确认后调用适配器 `probe()`，结果经 `apply_probe_result` 落库并审计。查询走 `query_snapshots` 冻结分页。

#### 7.1 `P-ADMIN-MUTATE` · 管理动作
- **触发/适用条件**：任意管理面写操作
- **图与正文位置**：本段 / 图 M004-P1
- **正常出口**：结果 + 审计(success)
- **异常出口**：`ApiError` + 审计(failed)

#### 7.2 `P-PROBE` · 探测
- **触发/适用条件**：`POST /v1/probes`
- **图与正文位置**：本段 / 图 M004-P1
- **正常出口**：`{deployment_id, status, checked_at, may_have_incurred_cost}`
- **异常出口**：400 `confirmation_required`；探测 false → `unhealthy`

#### 7.3 `P-MGMT-QUERY` · 分页查询
- **触发/适用条件**：用量/审计/日志查询
- **图与正文位置**：§5.2.3
- **正常出口**：冻结页
- **异常出口**：400 cursor 过期/不符

## 8. 关键算法与业务规则

#### 8.1 `RULE-MGMT-CAPS` · 等级能力 = 绑定 deployment 交集
- **输入前提 / 适用条件**：创建/更新 service level
- **算法 / 规则 / 选择依据**：对绑定集合取 12 键交集（bool 全真/值一致）；`Embedding-v1` 必须 embedding-only 且 space/dim/上限冻结
- **结果 / 不变量 / 边界**：无共同能力 → 409 `capability_conflict` / `embedding_space_conflict`
- **复杂度 / 资源限制**：O(deployments×keys)
- **允许替换范围 / 不可改变保证**：算法实现可自选；语义不可变
- **具体输入推演 / 验证项**：两个 deployment 能力不含共同 `responses` → 409；`VRC-MGMT-002`

#### 8.2 `RULE-MGMT-ETAG` · 乐观并发
- **输入前提 / 适用条件**：PATCH/DELETE
- **算法 / 规则 / 选择依据**：`ETag = "<id>.v<version>"`；`If-Match` 不等 → 412 + `current_version`
- **结果 / 不变量 / 边界**：`version` 单调 +1
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；语义不可变
- **具体输入推演 / 验证项**：并发 PATCH → 一个 200、一个 412；`VRC-MGMT-002`

#### 8.3 `RULE-MGMT-REF` · 引用保护
- **输入前提 / 适用条件**：DELETE
- **算法 / 规则 / 选择依据**：provider 被 deployment 引用、deployment 被 level 引用 → 409 `resource_in_use`
- **结果 / 不变量 / 边界**：不级联删除
- **复杂度 / 资源限制**：O(1)（索引）
- **允许替换范围 / 不可改变保证**：实现可自选；语义不可变
- **具体输入推演 / 验证项**：删除在用 provider → 409；`VRC-MGMT-002`

#### 8.4 `RULE-MGMT-PROBE` · 探测确认与落库
- **输入前提 / 适用条件**：`POST /v1/probes`
- **算法 / 规则 / 选择依据**：必须 `confirm_external_call=true`；适配器 `probe()`（5 s，GET `/models`）→ `healthy/unhealthy`；`apply_probe_result` 接受 `healthy/degraded/unhealthy/unknown` 并写 `deployments.health` + `probe_results`（PK `deployment_id`）
- **结果 / 不变量 / 边界**：保存/health/probe 三态分离；四值健康枚举
- **复杂度 / 资源限制**：单次外部 HTTP
- **允许替换范围 / 不可改变保证**：实现可自选；确认语义不可变
- **具体输入推演 / 验证项**：未确认 → 400 `confirmation_required`；`VRC-MGMT-005`

#### 8.5 `RULE-MGMT-SNAPSHOT` · 分页冻结
- **输入前提 / 适用条件**：首屏查询
- **算法 / 规则 / 选择依据**：同事务建 `query_snapshots` + 固化有序成员；后续按 `ordinal` 读
- **结果 / 不变量 / 边界**：TTL 10 分钟；cursor 复核 principal_id（非 admin）与 filter_digest
- **复杂度 / 资源限制**：O(页大小)
- **允许替换范围 / 不可改变保证**：实现可自选；冻结语义不可变
- **具体输入推演 / 验证项**：首屏后更正 → 旧页不变；`VRC-MGMT-004`

#### 8.6 `RULE-MGMT-USAGE-REFRESH` · 账号用量刷新
- **输入前提 / 适用条件**：`POST /v1/providers/{id}/usage`
- **算法 / 规则 / 选择依据**：必须 `confirm_external_call=true`；按 `usage_provider` 分 MiniMax（API Key）/火山（AK/SK HMAC 签名）；GET 不触网
- **结果 / 不变量 / 边界**：缺字段 Unknown；失败标 `unavailable`+`error`
- **复杂度 / 资源限制**：单次外部 HTTP（15 s）
- **允许替换范围 / 不可改变保证**：实现可自选；"只读快照/显式刷新"不可变
- **具体输入推演 / 验证项**：GET 不触网；未确认 POST → 400；`VRC-MGMT-006`

## 9. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口设计用途**分类（面向使用方的 API 与组件/系统间协作的消息与数据流接口），逐接口完整记录；标题为真实调用形式（进程内方法），标题下先给**完整接口声明**，再就地说明参数/结果字段，最后按固定六项。本模块接口均为向 M001 提供配置/查询能力的 API；消息流/硬件/人机三类不适用。数据结构引用 §6。

### 9.1 API（适用时）

#### `Registry.bootstrap_settings(path) -> None`

```text
bootstrap_settings(path: str | None) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-REGISTRY`；空库首次引导装配配置；M004 `management` 提供；状态=Implemented；唯一契约=本设计；文件·symbol `src/management/registry.py` `Registry.bootstrap_settings`。
- **输入与前提**：settings 文件路径（仅空库时读取）；`BootstrapConfig`（§6.3.1）。
- **成功输出与保证**：无返回；单事务写入配置 + `bootstrap_sha256` + 审计。
- **错误与合法下一步**：非法字段/引用/Secret 不可达 → `ApiError(503,"bootstrap_invalid")`（`ERR-BOOT`）并回滚；非空库重复调用 no-op。
- **交互与生命周期**：启动时一次；原子事务；失败置 `not_ready`。
- **实现与验证**：正常引导 + hash；拒绝非法引用 → 回滚 + 503。`VRC-MGMT-001/003`；`registry.py`。

#### `Registry.get_service_level(model) -> (ServiceLevelView, ETag)`

```text
get_service_level(model: str) -> tuple[ServiceLevelView, str]
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-REGISTRY`；按 exact 等级名查询等级视图；M004 提供、M003 消费；状态=Implemented；唯一契约=本设计；文件·symbol `registry.py` `Registry.get_service_level`。
- **输入与前提**：exact 逻辑等级名 `model`。
- **成功输出与保证**：`ServiceLevelView`（§6.2.3）+ ETag（供 M003 只读）。
- **错误与合法下一步**：未知 → `ApiError(404,"not_found")`（`ERR-NOTFOUND`）。
- **交互与生命周期**：同步只读；请求级。
- **实现与验证**：正常 7 Tier；边界：未知 exact 名 → 404。`VRC-INF-004`；`registry.py`。

#### `Registry.candidates(level_id) -> list[Candidate]`

```text
candidates(level_id: str) -> list[Candidate]
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-REGISTRY`；查询等级候选；M004 提供、M003 消费；状态=Implemented；唯一契约=本设计；文件·symbol `registry.py` `Registry.candidates`。
- **输入与前提**：等级 id。
- **成功输出与保证**：该等级已启用且能力匹配的候选（`Candidate`，见 M003 §6.2.4 `Candidate`）。
- **错误与合法下一步**：无（空列表表示无候选）。
- **交互与生命周期**：同步只读；请求级。
- **实现与验证**：正常返回候选；边界：全禁用 → `[]`。`VRC-INF-004`；`registry.py`。

#### `Registry.create_provider/get_provider/list_providers/update_provider/delete_provider(...)`

```text
create_provider(data: dict, conn=None) -> tuple[ProviderView, str]
get_provider(id: str) -> tuple[ProviderView, str]
list_providers() -> list[ProviderView]
update_provider(id: str, data: dict, if_match: str, conn=None) -> tuple[ProviderView, str]
delete_provider(id: str, if_match: str, conn=None) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-PROVIDERS`；provider CRUD；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `registry.py`。
- **输入与前提**：`data`/`id`/`if_match`；可选 `conn`（供 `mutate` 复用在途事务）。
- **成功输出与保证**：视图 + ETag（§6.1.4/§6.2.1）；delete 无返回。
- **错误与合法下一步**：400 `ERR-REQ-VALIDATION`；404 `ERR-NOTFOUND`；409 `ERR-CONFLICT`/`ERR-INUSE`；412 `ERR-STALE`。
- **交互与生命周期**：同步；写经 `Store.transaction(immediate=True)`（传入 `conn` 时加入既有事务）；请求级。
- **实现与验证**：正常 201+ETag；拒绝重名 → 409；删除在用 → 409。`VRC-MGMT-001/002`；`registry.py`。

#### `Registry.create_deployment/get_deployment/list_deployments/update_deployment/delete_deployment(...)`

```text
create_deployment(data: dict, conn=None) -> tuple[DeploymentView, str]
get_deployment(id: str) -> tuple[DeploymentView, str]
list_deployments() -> list[DeploymentView]
update_deployment(id: str, data: dict, if_match: str, conn=None) -> tuple[DeploymentView, str]
delete_deployment(id: str, if_match: str, conn=None) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DEPLOYMENTS`；deployment CRUD（含 Pause/Resume）；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `registry.py`。
- **输入与前提**：`data`/`id`/`if_match`；`capabilities` 12 键（§6.1.1）；可选 `conn`。
- **成功输出与保证**：`DeploymentView`（§6.2.2）+ ETag；delete 无返回。
- **错误与合法下一步**：400/404/409/412（含义同 provider）；`enabled` 切换用于 Pause/Resume。
- **交互与生命周期**：同步事务（传入 `conn` 时加入既有事务）；请求级。
- **实现与验证**：正常 CRUD；边界：PATCH `enabled=false` → Paused。`VRC-MGMT-002`；`registry.py`。

#### `Registry.create_service_level/get_service_level/list_service_levels/update_service_level/delete_service_level(...)`

```text
create_service_level(data: dict, conn=None) -> tuple[ServiceLevelView, str]
get_service_level(id: str) -> tuple[ServiceLevelView, str]
list_service_levels() -> list[ServiceLevelView]
update_service_level(id: str, data: dict, if_match: str, conn=None) -> tuple[ServiceLevelView, str]
delete_service_level(id: str, if_match: str, conn=None) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LEVELS`；service level（tier）CRUD；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `registry.py`。
- **输入与前提**：`data`/`id`/`if_match`；能力 = 成员交集；可选 `conn`。
- **成功输出与保证**：等级视图 + ETag（§6.2.3/§6.1.4）；`delete_service_level` 固定 Tier 恒抛 409 `fixed_service_level`。
- **错误与合法下一步**：400/404 `not_found`/409 `capability_conflict`/`embedding_space_conflict`/`fixed_service_level`/412。
- **交互与生命周期**：同步事务（传入 `conn` 时加入既有事务）；固定 7 Tier。
- **实现与验证**：正常交集；拒绝无共同能力 → 409。`VRC-MGMT-002`；`registry.py`。

#### `AdminService.mutate(actor, action, target, request_id, fn, atomic=True) -> result`

```text
mutate(actor: str, action: str, target: str, request_id: str | None, fn: Callable[[Any], Any], atomic: bool = True) -> Any
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-ADMIN`；管理动作统一审计包裹；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `src/management/admin.py` `AdminService.mutate`。
- **输入与前提**：`actor`（principal_id）、`action`、`target`、`request_id`、`fn(conn)`（实际管理动作）、`atomic`（默认 `True`；`False` 仅用于带外部调用的账号刷新）。
- **成功输出与保证**：`fn(conn)` 结果；成功时 Registry 写与 `success` 审计在**同一事务**提交，提交后记 info 日志。
- **错误与合法下一步**：`fn` 抛出的 `ApiError`/存储错误原样传播；失败记 `failed` + warning 后重抛。
- **交互与生命周期**：同步；`atomic=True` 时审计与业务写同事务；`atomic=False` 时审计独立写。
- **实现与验证**：正常包裹；边界：失败必留 `failed` 审计。`VRC-MGMT-002/003`；`admin.py`。

#### `AdminService.page(data, actor, kind, cursor=None, limit=100) -> dict`

```text
page(data: list, actor: str, kind: str, cursor: str | None = None, limit: int = 100) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-QUERY`；把 provider/deployment/level 列表冻结为稳定分页；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `admin.py` `AdminService.page`。
- **输入与前提**：`data`（待分页列表，如 provider/deployment/level 视图）、`actor`、`kind`、`cursor`、`limit`（钳制到 1..200）。
- **成功输出与保证**：`{data, page:{has_more, next_cursor}}`；首屏把 `data` 冻结进 `query_snapshots`/`query_snapshot_items`（kind=`admin:<kind>`）。
- **错误与合法下一步**：cursor 过期/跨 principal → `ApiError(400,"cursor_expired")`（`ERR-CURSOR`）；存储不可读 → `ERR-STORE`。
- **交互与生命周期**：首屏建 `query_snapshots` 冻结；TTL 10 分钟；后续页按 `ordinal` 读取。
- **实现与验证**：正常稳定分页；边界：旧页不受后续变更影响。`VRC-MGMT-004`；`admin.py`。

#### `AdminService.stats(from, to, group_by) -> dict`

```text
stats(from: str, to: str, group_by: str) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-STATS`；用量聚合；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `admin.py` `AdminService.stats`。
- **输入与前提**：`[from,to)`、`group_by ∈ {tier,deployment}`。
- **成功输出与保证**：`{from,to,group_by,data:[...]}`（按最高 record version 聚合 calls/tokens）。
- **错误与合法下一步**：非法 `group_by`/缺时间 → `ApiError(400,"invalid_request")`（`ERR-REQ-VALIDATION`）。
- **交互与生命周期**：同步只读；请求级。
- **实现与验证**：正常聚合；边界：measured/unknown 分列。`VRC-MGMT-004`；`admin.py`。

#### `AdminService.probe(actor, body, request_id) -> dict` / `apply_probe_result(registry, deployment_id, status, request_id, detail=None) -> dict`

```text
probe(actor: str, body: dict, request_id: str) -> dict
apply_probe_result(registry, deployment_id: str, status: str, request_id: str, detail: str | None = None) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-PROBES`；deployment 探测与落库；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `admin.py` `AdminService.probe` + `http_api/health.py` `apply_probe_result`。
- **输入与前提**：`probe` 输入 `actor`、`body={deployment_id, confirm_external_call:true}`、`request_id`；`apply_probe_result` 的 `status ∈ {healthy,degraded,unhealthy,unknown}`。
- **成功输出与保证**：`probe` → `{deployment_id, status, checked_at, may_have_incurred_cost}`；`apply_probe_result` → `{deployment_id, status, checked_at, request_id, detail}`；落库 `deployments.health` + `probe_results`。
- **错误与合法下一步**：缺确认 → `ApiError(400,"confirmation_required")`（`ERR-CONFIRM`）；未知 deployment → 404 `not_found`；探测 false → `unhealthy`；非法 status → 400 `invalid_request`。
- **交互与生命周期**：同步；适配器 5 s 超时；请求级。
- **实现与验证**：正常落库；边界：未确认不触网 → 400。`VRC-MGMT-005`；`admin.py`/`health.py`。

#### `AccountUsageService.latest(provider_id) -> AccountUsageSnapshot` / `refresh(provider_id, confirm_external_call) -> AccountUsageSnapshot`

```text
latest(provider_id: str) -> dict
refresh(provider_id: str, confirm_external_call: bool) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MGMT-ACCOUNT-USAGE`；账号用量读取/刷新；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `account_usage.py`。
- **输入与前提**：`provider_id`；`refresh` 需 `confirm_external_call=true`。
- **成功输出与保证**：`AccountUsageSnapshot` dict（§6.2.6）。
- **错误与合法下一步**：缺确认 → `ApiError(400,"confirmation_required")`（`ERR-CONFIRM`）；未知 provider → 404 `not_found`；上游失败 → 快照 `status=unavailable` + `source=provider_api_error` + `error`。
- **交互与生命周期**：`latest` 只读不触网；`refresh` 显式外部 HTTP（15 s）；持久覆盖。
- **实现与验证**：正常读/刷新；边界：GET 不触网；未确认 POST → 400。`VRC-MGMT-006`；`account_usage.py`。

#### `UsageRecorder.page(principal, cursor, limit, admin, since, until, model, request_id) -> dict` / `reset_usage(model=None, deployment_id=None, conn=None) -> dict`

```text
page(principal: str, cursor: str | None, limit: int = 50, admin: bool = False, since: str | None = None, until: str | None = None, model: str | None = None, request_id: str | None = None) -> dict
reset_usage(model: str | None = None, deployment_id: str | None = None, conn=None) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-USAGE`；账本分页/清空；M003（`UsageRecorder`）提供、M004 消费；状态=Implemented；唯一契约=M003 设计 `IF-INF-USAGE`；文件·symbol `src/inference/usage.py` `UsageRecorder`。
- **输入与前提**：查询范围（`since`/`until` 必需）/cursor；清空范围。
- **成功输出与保证**：冻结分页 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`（§6.2.8）/ `{deleted}`。
- **错误与合法下一步**：400 `ERR-REQ-VALIDATION`/`ERR-CURSOR`；403 `ERR-AUTH-DENIED`；503 `ERR-STORE`。
- **交互与生命周期**：同步；清空单事务删义务/版本/head/绑定；经审计。
- **实现与验证**：正常分页/清空；边界：同 request 只取最高版本。`VRC-MGMT-004`；`src/inference/usage.py`。

#### `AuditLog.record(actor, action, target, result, request_id, conn=None) -> None` / `AuditLog.page(limit=50) -> dict`

```text
record(actor: str, action: str, target: str, result: str, request_id: str | None = None, conn=None) -> None
page(limit: int = 50) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-AUDIT-LOGS`；审计写入/查询；M004 提供；状态=Implemented；唯一契约=本设计；文件·symbol `src/management/audit.py` `AuditLog`。
- **输入与前提**：审计字段 / 分页；可选 `conn`（`mutate` 传入同一事务连接）。
- **成功输出与保证**：无 / 脱敏分页 `{data,page:{has_more,next_cursor}}`（`audit_events`，§6.2.4）。
- **错误与合法下一步**：存储错误 → `ERR-STORE`（503）。
- **交互与生命周期**：同步；只追加；按时间倒序。
- **实现与验证**：正常 success/failed；边界：不含正文/Secret。`VRC-MGMT-003`；`audit.py`。

#### `OperationalLog.page(limit, level, module, request_id, since, until) -> dict`（消费 M008）

```text
page(limit: int = 50, level: str | None = None, module: str | None = None, request_id: str | None = None, since: str | None = None, until: str | None = None) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-AUDIT-LOGS`（消费侧）；运行日志分页查询；M008 提供、M004 消费；状态=Implemented；唯一契约=M008 §9.1 `IF-LOG-QUERY`；文件·symbol `src/log/logs.py`。
- **输入与前提**：`since`/`until` **必需**（缺失 → 400 `invalid_request`）；可选 `level`/`module`/`request_id`。
- **成功输出与保证**：脱敏 `LogPage`（§6.2.7）。
- **错误与合法下一步**：缺时间 → `ApiError(400,"invalid_request")`（`ERR-REQ-VALIDATION`）；存储不可读 → `ERR-STORE`（503）。
- **交互与生命周期**：同步只读；请求级。
- **实现与验证**：正常脱敏列表；边界：无匹配 `data=[]`。`VRC-MGMT-003`；`src/log/logs.py`。

### 9.2 消息与数据流接口（适用时）

不适用（同步服务方法；无独立事件/队列/流；审计/日志经同步写入；tailoring：M004 只向 M001 提供可调用能力）。

### 9.3 硬件与固件接口（适用时）

不适用（无连接器/总线/寄存器/FPGA 端口）。

### 9.4 人机与维护接口（适用时）

不适用（管理面入口归 M001、呈现归 M002；本模块不拥有 UI/CLI）。

## 10. 并发、失败与恢复

#### 10.1 `F-MGMT-ETAG` · 并发编辑冲突
- **初始条件 / 并发交错 / 失败点**：两 operator 同时 PATCH
- **检测事实 / authority / 期限**：ETag `If-Match`（§8.2）
- **处理行为 / 副作用边界**：412 + `current_version`；不覆盖
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：重新 GET 后重试
- **最终状态 / 资源归属 / 后续合法入口**：旧版本保留
- **验证项 / 组合责任**：`VRC-MGMT-002`

#### 10.2 `F-MGMT-REF` · 删除被引用
- **初始条件 / 并发交错 / 失败点**：provider/deployment 在用
- **检测事实 / authority / 期限**：引用查询（§8.3）
- **处理行为 / 副作用边界**：409 `resource_in_use`；不级联
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：先解绑
- **最终状态 / 资源归属 / 后续合法入口**：资源保留
- **验证项 / 组合责任**：`VRC-MGMT-002`

#### 10.3 `F-MGMT-BOOT` · 引导失败
- **初始条件 / 并发交错 / 失败点**：settings 不可读/非法/SECRET 不可达
- **检测事实 / authority / 期限**：校验结果（§8）
- **处理行为 / 副作用边界**：回滚；置 `bootstrap_error`
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：修正后重启
- **最终状态 / 资源归属 / 后续合法入口**：not_ready（`/readyz` 503）
- **验证项 / 组合责任**：`VRC-MGMT-003`

#### 10.4 `F-MGMT-STORE` · 存储不可用
- **初始条件 / 并发交错 / 失败点**：查询/写入存储失败
- **检测事实 / authority / 期限**：Store 异常
- **处理行为 / 副作用边界**：读 → 503（不返回空页）；写 → 回滚
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：稍后重试
- **最终状态 / 资源归属 / 后续合法入口**：503
- **验证项 / 组合责任**：`VRC-MGMT-004`

#### 10.5 `F-MGMT-USAGE-REFRESH` · 账号用量刷新失败
- **初始条件 / 并发交错 / 失败点**：provider usage API 报错/超时
- **检测事实 / authority / 期限**：HTTPError/OSError（§5.3.5）
- **处理行为 / 副作用边界**：快照标 `unavailable`+`error`；不影响推理
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：稍后重新刷新
- **最终状态 / 资源归属 / 后续合法入口**：快照持久
- **验证项 / 组合责任**：`VRC-MGMT-006`

## 11. 安全、权限与可观测性

- **权限**：不鉴权（入口单点，M-TRUST CON-TRUST-001）；M001 传 `actor=principal_id` 用于审计
- **Secret**：只存引用；`registry` 校验 `env:`/`file:`；账号用量凭据经 `secret_ref` 解析，不入库不回显
- **审计/日志**：`mutate` 统一记审计；日志写入前脱敏；禁止 prompt/output/Secret 进入
- **不泄露存在性**：401/403 语义由 M001 统一

## 12. 容量、性能与运行限制

#### 12.1 `CAP-MGMT-CONFIG` · 配置规模
- **目标 / 限制 / 单位**：provider/deployment/level 数量小（数十）；变更低频
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：SQLite 单文件
- **负载、数据规模与并发口径**：operator 顺序操作
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：无专门限流
- **超限行为 / 责任出口**：—
- **验证项 / Evidence**：`VRC-MGMT-002`；NOT_RUN

#### 12.2 `CAP-MGMT-PAGE` · 分页上限
- **目标 / 限制 / 单位**：`limit ≤ 200`；snapshot TTL 10 分钟
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`query_snapshots`
- **负载、数据规模与并发口径**：单查询
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：400 cursor 过期
- **验证项 / Evidence**：`VRC-MGMT-004`；NOT_RUN

#### 12.3 `CAP-MGMT-PROBE` · 探测超时
- **目标 / 限制 / 单位**：5 s（GET `/models`）
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：适配器
- **负载、数据规模与并发口径**：单次
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：`unhealthy`
- **验证项 / Evidence**：`VRC-MGMT-005`；NOT_RUN

## 13. 实现步骤与文件清单

### 13.1 文件分解（设计 → 代码文件）

#### 13.1.1 `src/management/registry.py`
- **职责 / 非职责**：I1 配置权威 + I3 引导 + 候选查询；不做管理动作审计
- **关键 symbol / 导出范围**：`Registry.bootstrap_settings/ensure_fixed_tiers/create_*/get_*/list_*/update_*/delete_*/candidates`
- **承接 Function / Rule / Constraint / Interface ID**：`F-MGMT-BOOTSTRAP`、`F-MGMT-CRUD`、`RULE-MGMT-CAPS/ETAG/REF`、`CON-CFG-001/2/3/4/5`、`IF-PROVIDERS/DEPLOYMENTS/LEVELS`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`；依赖 Store
- **实现状态**：Implemented
- **验证入口**：`VRC-MGMT-001/002/003`

#### 13.1.2 `src/management/admin.py`
- **职责 / 非职责**：I2 管理动作编排（mutate/分页/统计）+ I4 探测 + 列模型；不做具体 CRUD
- **关键 symbol / 导出范围**：`AdminService.mutate/page/stats/probe/list_provider_models`
- **承接 Function / Rule / Constraint / Interface ID**：`F-MGMT-CRUD/PROBE/STATS`、`RULE-MGMT-PROBE/SNAPSHOT`、`IF-MGMT-02/04`、`IF-PROBES`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-MGMT-002/004/005`

#### 13.1.3 `src/management/account_usage.py`
- **职责 / 非职责**：I7 账号用量只读/显式刷新；不自动轮询/不 cookie
- **关键 symbol / 导出范围**：`AccountUsageService.latest/refresh`（`_minimax`/`_volc`/`_volc_request`）
- **承接 Function / Rule / Constraint / Interface ID**：`F-MGMT-ACCOUNT-USAGE`、`RULE-MGMT-USAGE-REFRESH`、`IF-MGMT-05`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-MGMT-006`

#### 13.1.4 `src/management/audit.py`
- **职责 / 非职责**：I5 审计写入/查询；不含正文
- **关键 symbol / 导出范围**：`AuditLog.record/page`
- **承接 Function / Rule / Constraint / Interface ID**：`F-MGMT-AUDIT`、`IF-MGMT-03`、`IF-AUDIT-LOGS`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-MGMT-003`

#### 13.1.5 `src/log/logs.py`
- **职责 / 非职责**：I6 写前脱敏 + 结构化查询；不含原始日志
- **关键 symbol / 导出范围**：`OperationalLog.record/page`、`_SENSITIVE`
- **承接 Function / Rule / Constraint / Interface ID**：`F-MGMT-LOGS`、`IF-MGMT-03`、`IF-AUDIT-LOGS`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`
- **实现状态**：Implemented
- **验证入口**：`VRC-MGMT-003`

#### 13.1.6 `src/http_api/health.py`
- **职责 / 非职责**：健康/就绪视图 + 探测结果落库；不做主动收费探测
- **关键 symbol / 导出范围**：`health_view`、`readiness_view`、`apply_probe_result`
- **承接 Function / Rule / Constraint / Interface ID**：`F-MGMT-PROBE`、`RULE-MGMT-PROBE`、`IF-MGMT-04`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`；由 M001 路由
- **实现状态**：Implemented
- **验证入口**：`VRC-MGMT-005`

### 13.2 实现步骤

#### 13.2.1 配置权威与引导
- **前置输入 / 依赖**：settings schema；固定 Tier 集合
- **新增 / 修改文件与 symbol**：`registry.py`、`app.py` 装配
- **固定语义 / 可自行决定范围**：能力交集/引用/ETag 固定；实现可自选
- **交付结果**：可查询 Registry
- **完成检查**：`VRC-MGMT-001/002`

#### 13.2.2 管理动作编排与审计
- **前置输入 / 依赖**：`mutate` 包裹语义
- **新增 / 修改文件与 symbol**：`admin.py`、`audit.py`、`logs.py`
- **固定语义 / 可自行决定范围**：审计必写固定；实现可自选
- **交付结果**：结果 + 审计
- **完成检查**：`VRC-MGMT-003`

#### 13.2.3 探测与账号用量
- **前置输入 / 依赖**：适配器、provider usage API
- **新增 / 修改文件与 symbol**：`admin.py`、`health.py`、`account_usage.py`
- **固定语义 / 可自行决定范围**：确认语义固定；实现可自选
- **交付结果**：健康行 / 快照
- **完成检查**：`VRC-MGMT-005/006`

#### 13.2.4 分页与清空
- **前置输入 / 依赖**：`query_snapshots`；M-METER 语义
- **新增 / 修改文件与 symbol**：`admin.py`、`usage.py`
- **固定语义 / 可自行决定范围**：冻结/TTL/只追加固定；实现可自选
- **交付结果**：冻结页 / `{deleted}`
- **完成检查**：`VRC-MGMT-004`

## 14. 测试与验收

#### 14.1 `VRC-MGMT-001` · 引导与 Secret 引用
- **覆盖 Function / Rule / Constraint / Interface**：`F-MGMT-BOOTSTRAP`、`CON-CFG-001/2`、`IF-PROVIDERS`
- **Case / 正常、边界与失败输入**：合法 settings；重复启动；缺节；`env:` 空/`file:` 不存在
- **环境 / 配置 / 隔离与复位**：独立临时库
- **独立 Oracle / Expected**：Registry 与 hash 一致；503 + 回滚 + not_ready
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：启动/M001

#### 14.2 `VRC-MGMT-002` · CRUD 与不变量
- **覆盖 Function / Rule / Constraint / Interface**：`F-MGMT-CRUD`、`RULE-MGMT-CAPS/ETAG/REF`、`IF-DEPLOYMENTS/LEVELS`
- **Case**：并发 PATCH；删除被引用；能力不兼容；`Embedding-v1` 冻结
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：412/409/`capability_conflict`/`embedding_space_conflict`
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003（候选）

#### 14.3 `VRC-MGMT-003` · 审计与日志
- **覆盖 Function / Rule / Constraint / Interface**：`F-MGMT-AUDIT`、`F-MGMT-LOGS`、`IF-AUDIT-LOGS`
- **Case**：成功/失败管理动作；含 Authorization/Secret 的消息
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：审计 success/failed；日志脱敏为 `[REDACTED]`
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M002（日志页）

#### 14.4 `VRC-MGMT-004` · 分页与清空
- **覆盖 Function / Rule / Constraint / Interface**：`F-MGMT-USAGE-QUERY/RESET`、`F-MGMT-STATS`、`RULE-MGMT-SNAPSHOT`、`CON-METER-004`
- **Case**：首屏后更正；cursor 过期/跨 principal；范围清空
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：旧页冻结；400/403；计数一致
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M-METER

#### 14.5 `VRC-MGMT-005` · 探测
- **覆盖 Function / Rule / Constraint / Interface**：`F-MGMT-PROBE`、`RULE-MGMT-PROBE`、`IF-PROBES`
- **Case**：未确认；正常探测；不可达
- **环境 / 配置 / 隔离与复位**：隔离库 + 上游可达/不可达
- **独立 Oracle / Expected**：400；`healthy`/`unhealthy` 落库
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M003 适配器

#### 14.6 `VRC-MGMT-006` · 账号用量
- **覆盖 Function / Rule / Constraint / Interface**：`F-MGMT-ACCOUNT-USAGE`、`RULE-MGMT-USAGE-REFRESH`、`IF-MGMT-05`
- **Case**：GET 不触网；未确认 POST；凭据缺失；provider 报错
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：`not_refreshed`/`unavailable`+`error`；快照持久
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M002（Providers 页）

## 15. 风险、未决问题与引用

#### 15.ISD · 实现规格采用方式
- **采用模式**：`separate`（模块设计不兼作 ISD）
- **模块对象 ID**：M004
- **实现规格 Document ID**：`management-isd`
- **metadata 覆盖映射入口**：`management-isd` 的 `implementation_specification.coverage_mapping`
- **理由 / 决定引用**：模块设计不兼作 ISD；独立 ISD 见 `docs/50_implementation_design/management-isd.md`（Planned）

#### 15.1 `RISK-MGMT-1` · 离线迁移误操作
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 `CON-CFG-001`
- **事实缺口 / 触发条件**：operator 误用迁移命令
- **影响 / 阻塞边界**：配置损坏；不阻塞设计
- **Owner / 最晚关闭 Gate**：LLMTier / 运维流程
- **选项 / 推荐 / 下一步取证**：备份 + 单一命令 + 不双写
- **关闭条件 / 决定或当前状态**：观察

#### 15.2 `RISK-MGMT-2` · 账号用量字段缺失
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 `F-MGMT-ACCOUNT-USAGE`
- **事实缺口 / 触发条件**：provider 返回窗口字段缺省
- **影响 / 阻塞边界**：显示 Unknown；不阻塞
- **Owner / 最晚关闭 Gate**：LLMTier / —
- **选项 / 推荐 / 下一步取证**：缺字段保持 Unknown，不填 0
- **关闭条件 / 决定或当前状态**：已接受

引用：系统设计 §3.2/§10；机制 M-CONFIG §14.4（`R-CFG-01/02/03`）、M-METER §14.4（`R-MET-02/03`）、M-OBS §14.4（`R-OBS-02`）；`interfaces/openapi/llmtier.openapi.json`。

## 附录 A. 机制承接表

#### A.1 `llmtier-config-lifecycle-mechanism` / `R-CFG-01` · 配置权威与发布
- **来源 Capability / Step / Constraint / 接口成员**：CON-CFG-001/2/3/4、Step 3/4/6、`bootstrap_settings`/CRUD/`candidates`/`get_service_level`
- **本模块必须负责的行为与保证**：唯一权威、发布事务、能力不变量、审计
- **本模块提供 / 消费的接口**：`bootstrap_settings`、CRUD、`candidates`、`get_service_level`
- **本文落实位置**：§5.1.1、§5.1.2、§8.1–8.3、§9.1–9.3
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`registry.py`、`admin.py`
- **允许自行决定的范围**：存储/算法实现
- **本地验证 / 组合验证交接**：`VRC-MGMT-001/002`

#### A.2 `llmtier-config-lifecycle-mechanism` / `R-CFG-02` · 引导
- **来源 Capability / Step / Constraint / 接口成员**：CON-CFG-005、Step 1/2/5
- **本模块必须负责的行为与保证**：迁移、引导、not_ready
- **本模块提供 / 消费的接口**：启动流程
- **本文落实位置**：§5.1.3、§10.3
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`registry.py` `bootstrap_settings` + `app.py`
- **允许自行决定的范围**：引导实现
- **本地验证 / 组合验证交接**：`VRC-MGMT-001/003`

#### A.3 `llmtier-config-lifecycle-mechanism` / `R-CFG-03` · Store 事务
- **来源 Capability / Step / Constraint / 接口成员**：Step 1/4、`transaction`
- **本模块必须负责的行为与保证**：原子事务与版本
- **本模块提供 / 消费的接口**：`transaction`
- **本文落实位置**：§5.3.1、§10.4
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`registry.py`（消费方）+ `store.py`[M007]
- **允许自行决定的范围**：存储实现
- **本地验证 / 组合验证交接**：M007

#### A.4 `llmtier-usage-metering-mechanism` / `R-MET-02` · 用量查询
- **来源 Capability / Step / Constraint / 接口成员**：CON-METER-004、Step 4/5、`page`
- **本模块必须负责的行为与保证**：snapshot 冻结分页、cursor 复核 principal/filter
- **本模块提供 / 消费的接口**：`page()`
- **本文落实位置**：§5.1.8、§8.5、§9.5
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`usage.py`
- **允许自行决定的范围**：分页实现
- **本地验证 / 组合验证交接**：`VRC-MGMT-004`

#### A.5 `llmtier-usage-metering-mechanism` / `R-MET-03` · 范围清空
- **来源 Capability / Step / Constraint / 接口成员**：CAP-METER-RESET、Step 6、`reset_usage`
- **本模块必须负责的行为与保证**：范围清空 + 审计
- **本模块提供 / 消费的接口**：`reset_usage()`
- **本文落实位置**：§5.1.8、§7.1、§9.5
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`usage.py` + `admin.py`
- **允许自行决定的范围**：范围实现
- **本地验证 / 组合验证交接**：`VRC-MGMT-004`

（说明：诊断开关/注入的**呈现与路由**是机制 M-OBS §14.4 `R-OBS-02` 对 **M005** 的要求；M004 只提供 `mutate` 审计包裹，不在本附录重复承接。）
