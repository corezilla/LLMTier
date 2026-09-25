<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier Management Interface Control

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-management-control` |
| Document Version | `0.3.3-draft.5` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-25` |
| Template ID | `interfaces.control` |
| Template Version | `0.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/llmtier-management-control.md` |
| Supersedes | `docs/99_reference/contracts/llmtier-management-contract-v0.3.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 接口目的、范围与双方 authority

Management是LLMTier自己的operator面，不是Slinky/Piko控制面。只管理云/本地模型、deployment、逻辑等级、健康探测、token Usage和审计，并提供只读的脱敏运行日志查询。

- **提供方**：LLMTier M001/M004/M005/M008；**消费者**：LLMTier operator（中文 Admin Web UI 同源调用）。
- **唯一字段级 authority**：`interfaces/openapi/llmtier.openapi.json`（version `0.3-simplified-candidate.8`，sha256 `b34428126390056e3eb7927ccb219e5185962a3c5483abb6d9f4fab7ed9a417a`）。
- **本文拥有**：管理面边界决定、状态/顺序、失败语义与运维约束；不复制机制正文。
- **ID/错误**：复用系统设计 §8/§9 的 `D-*`/`IF-*` 与 §8.8 的 `ERR-*`；`interfaces/error-codes/` 未建立 → **Proposed**。
- **部署条件**：Admin Bearer auth 与 Data Plane credential 分离；生产使用 TLS。

## 2. 接口设计（接口注册表）

> 按 STD `design-data-interface-format` 1.2.0 §3 按**接口形态分类**；分类适用性：2.1 软件接口 ✓（Admin HTTP）｜2.2 消息与数据流接口 ✗（无事件/流；日志为拉取查询）｜2.3 硬件与固件接口 ✗（纯软件）｜2.4 人机与维护接口 ✓（Admin Web UI 操作，同源调用 Admin API）。

### 2.0 接口注册表

| Interface ID | Provider | Consumer | 类型 | Version | Status |
|---|---|---|---|---|---|
| `IF-ADM-PROVIDERS` | LLMTier M004 | operator/UI | HTTP CRUD | candidate.8 | Implemented |
| `IF-ADM-DEPLOYMENTS` | LLMTier M004 | operator/UI | HTTP CRUD | candidate.8 | Implemented |
| `IF-ADM-SERVICE-LEVELS` | LLMTier M004 | operator/UI | HTTP CRUD | candidate.8 | Implemented |
| `IF-ADM-PROBES` | LLMTier M004 | operator/UI | HTTP op | candidate.8 | Implemented |
| `IF-ADM-PROVIDER-USAGE` | LLMTier M004 | operator/UI | HTTP GET/POST | candidate.8 | Implemented |
| `IF-ADM-USAGE` | LLMTier M003 | operator/consumer | HTTP GET/DELETE | candidate.8 | Implemented |
| `IF-ADM-RUNTIME` | LLMTier M003 | operator | HTTP GET | candidate.8 | Implemented |
| `IF-ADM-STATS` | LLMTier M004 | operator | HTTP GET | candidate.8 | Implemented |
| `IF-ADM-AUDIT` | LLMTier M004 | operator | HTTP GET | candidate.8 | Implemented |
| `IF-ADM-LOGS` | LLMTier M008/M005 | operator | HTTP GET | candidate.8 | Implemented |

编目范围=`selected_members`，分母为上述 Admin 面；不含 clients/sources/SourceInstance/entitlements/capacity-groups/recovery-items/Cost（§8）。状态不等于实现通过。

### 2.1 软件接口（适用时）

#### `GET/POST /v1/providers`；`GET/PATCH/DELETE /v1/providers/{provider_id}`

```text
GET    /v1/providers?cursor=&limit=            -> 200 ProviderPage {data:[ProviderView], page:AdminPageMeta}
POST   /v1/providers {ProviderWrite}           -> 201 ProviderView (ETag)
GET    /v1/providers/{provider_id}             -> 200 ProviderView (ETag)
PATCH  /v1/providers/{provider_id} {ProviderPatch} If-Match -> 200 ProviderView (ETag)
DELETE /v1/providers/{provider_id} If-Match    -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-PROVIDERS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；`src/management/registry.py`。
- **输入**：`ProviderWrite`/`ProviderPatch`（§4.2）；`If-Match`（PATCH/DELETE 必填）；授权=`admin`。
- **成功输出**：`ProviderView`（§4.2）+ 强 ETag；`secret_ref` 只写不回显；同事务写 `D-AUDIT-EVENT`。
- **错误与异常**：`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）；重名→`ERR-CONFLICT`（409）；被引用删除→`ERR-INUSE`（409）；`If-Match` 过期→`ERR-STALE`（412）；未知 ID→`ERR-NOTFOUND`（404）；`ERR-STORE`（503）。
- **交互与生命周期**：同步；PATCH partial；DELETE 幂等；ETag 乐观并发。
- **实例与验证**：正常 201+ETag；拒绝缺 `If-Match` 的 PATCH→412。`VRC-MGMT-001/002`。

#### `GET/POST /v1/providers/{provider_id}/usage`

```text
GET  /v1/providers/{provider_id}/usage                               -> 200 ProviderAccountUsageSnapshot
POST /v1/providers/{provider_id}/usage {confirm_external_call:true}  -> 200 ProviderAccountUsageSnapshot
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-PROVIDER-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/management/account_usage.py`。
- **输入**：`provider_id`；POST 仅 `confirm_external_call`；Admin Bearer。
- **成功输出**：`ProviderAccountUsageSnapshot`（§4.2）；POST 显式刷新并替换；不落 Secret。
- **错误与异常**：缺确认→`ERR-CONFIRM`（400）；未知 provider→`ERR-NOTFOUND`（404）；上游失败记入快照 `status`（HTTP 200）。
- **交互与生命周期**：同步；GET 只读；POST 显式触网、不自动轮询。
- **实例与验证**：正常带确认刷新；拒绝缺确认。`VRC-DIAG-004`。

#### `GET/POST /v1/deployments`；`GET/PATCH/DELETE /v1/deployments/{deployment_id}`

```text
GET    /v1/deployments?cursor=&limit=              -> 200 DeploymentPage {data:[DeploymentView], page}
POST   /v1/deployments {DeploymentWrite}           -> 201 DeploymentView (ETag)
GET    /v1/deployments/{deployment_id}             -> 200 DeploymentView (ETag)
PATCH  /v1/deployments/{deployment_id} {DeploymentPatch} If-Match -> 200 DeploymentView (ETag)
DELETE /v1/deployments/{deployment_id} If-Match    -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-DEPLOYMENTS`；规格已定、Implemented；`openapi` candidate.8；`src/management/registry.py`。
- **输入**：`DeploymentWrite`/`DeploymentPatch`（§4.2）；`If-Match`；Admin Bearer。
- **成功输出**：`DeploymentView`（§4.2）+ ETag；同事务审计；Pause/Resume 经 `enabled`。
- **错误与异常**：未知 `provider_id`→`ERR-REQ-VALIDATION`（400）；重名→`ERR-CONFLICT`（409）；被 tier 引用→`ERR-INUSE`（409）；`ERR-STALE`（412）。
- **交互与生命周期**：同步；partial PATCH；ETag。
- **实例与验证**：正常引用已存在 provider；拒绝未知。`VRC-MGMT-001/002`。

#### `GET/POST /v1/service-levels`；`GET/PATCH/DELETE /v1/service-levels/{service_level_id}`

```text
GET    /v1/service-levels?cursor=&limit=               -> 200 ServiceLevelPage {data:[ServiceLevelView], page}
POST   /v1/service-levels {ServiceLevelWrite}          -> 201 ServiceLevelView (ETag)
GET    /v1/service-levels/{service_level_id}           -> 200 ServiceLevelView (ETag)
PATCH  /v1/service-levels/{service_level_id} {ServiceLevelPatch} If-Match -> 200 ServiceLevelView (ETag)
DELETE /v1/service-levels/{service_level_id} If-Match  -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-SERVICE-LEVELS`；规格已定、Implemented；`openapi` candidate.8；`src/management/registry.py`。
- **输入**：`ServiceLevelWrite`/`ServiceLevelPatch`（§4.2）；`If-Match`；Admin Bearer。
- **成功输出**：`ServiceLevelView`（§4.2）`capabilities` 为成员交集；同事务审计。
- **错误与异常**：非固定 tier/非法交集→`ERR-REQ-VALIDATION`（400）；`ERR-CONFLICT`（409）；被引用→`ERR-INUSE`（409）；`ERR-STALE`（412）。
- **交互与生命周期**：同步；partial PATCH；成员顺序稳定。
- **实例与验证**：正常绑定有序成员；拒绝非固定 tier。`VRC-MGMT-001/002`。

#### `POST /v1/probes`

```text
POST /v1/probes {deployment_id, confirm_external_call:true} -> 200 ProbeResult
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-PROBES`；规格已定、Implemented；`openapi` candidate.8；`src/management/admin.py`。
- **输入**：`ProbeRequest`；Admin Bearer + 二次确认。
- **成功输出**：`ProbeResult`（§4.2）；可能产生费用（`may_have_incurred_cost`）。
- **错误与异常**：缺确认→`ERR-CONFIRM`（400）；未知 deployment→`ERR-NOTFOUND`（404）；上游失败→`ERR-PROVIDER-*`（502）。
- **交互与生命周期**：同步显式触发，不自动轮询。
- **实例与验证**：正常带确认；拒绝缺确认。`VRC-DIAG-004`。

#### `GET/DELETE /v1/usage`

```text
GET    /v1/usage?cursor=&limit=&from=&to=&model=&request_id= -> 200 UsagePage
DELETE /v1/usage?model=&deployment_id=                        -> 200 object   # 仅 operator
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/inference/usage.py`。
- **输入**：GET `from`/`to` 必填+可选过滤（data credential 仅见自身，admin 见全部）；DELETE 仅 admin。
- **成功输出**：`UsagePage`（§4.2，unknown 不填零）；DELETE 清空结果。
- **错误与异常**：非 admin DELETE→`ERR-AUTH-DENIED`；`ERR-CURSOR`（400）；`ERR-STORE`（503，不用空页）。
- **交互与生命周期**：GET 稳定快照（cursor 绑定 principal/授权/filter）；同 request 版本不累计。
- **实例与验证**：正常分页；拒绝非 admin/过期 cursor。`VRC-MGMT-006`。

#### `GET /v1/runtime` / `GET /v1/stats` / `GET /v1/audit` / `GET /v1/logs`

```text
GET /v1/runtime                            -> 200 object                    # 并发/队列快照
GET /v1/stats?from=&to=&group_by=tier      -> 200 object
GET /v1/audit?limit=                       -> 200 AuditPage {data:[AuditEvent], page}
GET /v1/logs?limit=&level=&module=&request_id=&from=&to= -> 200 LogPage {data:[LogEntry], page}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-RUNTIME`、`IF-ADM-STATS`、`IF-ADM-AUDIT`、`IF-ADM-LOGS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/routing.py`、`src/management/admin.py`、`src/management/audit.py`、`src/log/logs.py`。
- **输入**：过滤/时间窗参数；Admin Bearer。
- **成功输出**：瞬时快照 / 聚合 / `AuditEvent` / `LogEntry`（均脱敏，§4.2）；Logs 仅 level/module/event/message/request ID/time。
- **错误与异常**：缺 `from`/`to`→`ERR-REQ-VALIDATION`（400）；`ERR-STORE`（503，返回 503 而非空页）。
- **交互与生命周期**：同步只读；日志支持 level/module/request ID 过滤，7 天保留。
- **实例与验证**：正常过滤；拒绝缺时间窗。`VRC-LOG-001`、`VRC-MGMT-006`。

#### Admin Web UI 操作（人机与维护）

```text
operator UI → same-origin Admin HTTP (Bearer via session)
  providers / deployments / service-levels 列表与编辑
  probes / usage / runtime / audit / logs 只读或显式操作
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-UI`；规格已定、Implemented；唯一契约=本文 §2.1 各 Admin 接口；`src/web_ui/`。
- **输入**：operator 交互（表单/按钮）；权限=`admin`；不直接读配置文件或 Secret。
- **成功输出**：调用 Admin API 的结果呈现；配置保存成功不得显示成 probe 成功。
- **错误与异常**：透传 Admin API 的 `ERR-*`（401/403/409/412 等）。
- **交互与生命周期**：同源；结果不明时先 GET 核对，不盲目重复 Secret/删除操作。
- **实例与验证**：Admin UI test（activation gate）。`VRC-MGMT-*`。

### 2.2 消息与数据流接口（适用时）

不适用：Management 面无事件/队列/流；日志/审计/用量均为拉取式 HTTP 查询（已记于 §2.1）。

### 2.3 硬件与固件接口（适用时）

不适用：纯软件，无连接器/总线/寄存器。

### 2.4 人机与维护接口（适用时）

见 §2.1 末“Admin Web UI 操作”；运维 runbook（backup/restore/restart）见运维文档。

## 3. 传输与物理边界

> 分类同 §2；逐接口端点/协议回写 §2 各声明。

- **软件接口（Admin HTTP）**：HTTPS + JSON + Bearer Auth；端点 `/v1/*`（Admin 面）。Admin Bearer auth 与 Data Plane credential 分离；生产使用 TLS。
- **人机与维护接口**：中文 Web UI 同源调用 Admin API，不直接读配置文件或 Secret。
- **硬件与固件接口**：不适用。
- **消息与数据流接口**：不适用。

## 4. 数据结构设计（数据、命令与 Schema）

> 按 STD `design-data-interface-format` 1.2.0 §2 按**数据性质**分类；wire 字段以 §1 `openapi` 为机器权威，本节只给阅读视图与含义。

**类别适用性**：4.1 公共基础类型与枚举 ✓｜4.2 业务与操作数据结构 ✓｜4.3 配置与规则数据结构 ✓｜4.4 通信报文结构 ✓（机器源继承）｜4.5 设备与 FPGA 表项结构 ✗（纯软件）｜4.6 运行状态数据结构 ✓｜4.7 数据库表结构 ✓（authority `util/migrations/*.sql`）｜4.8 错误码与错误结构 ✓（引用系统 §8.8）。

### 4.1 公共基础类型与枚举

#### `Kind` / `Health` / `LogLevel` / `TierId`
- **定义、Data/Type ID 与唯一来源**：管理面共享枚举；机器源 `openapi` `ProviderView`/`DeploymentView`/`LogEntry`/`ServiceLevelView`。
- **字段**：`kind ∈ {cloud,local}`；`health ∈ {unknown,healthy,degraded,unhealthy}`；`level ∈ {info,warning,error}`；`TierId` = 7 固定 tier。
- **约束 / 不变量**：枚举值固定，不得扩展；tier `id` exact-case。
- **状态 · 所有权 · 寿命**：随所属结构持久/返回。
- **合法与拒绝实例**：合法 `healthy`；拒绝未知枚举值。
- **验证**：`openapi`；`VRC-MGMT-*`。

### 4.2 业务与操作数据结构

#### `ProviderView` / `ProviderWrite` / `ProviderPatch`
- **定义、Data/Type ID 与唯一来源**：provider 写模型与视图；`D-PROVIDER`；机器源 `openapi`。
- **字段**：`ProviderWrite{name,kind,endpoint,secret_ref?,enabled,usage?}`；`ProviderPatch` 全可选 `minProperties:1`；`ProviderView{id,name,kind,endpoint,has_secret,enabled,usage:ProviderUsageProfileView,request_usage,version≥1}`。
- **约束 / 不变量**：Provider 区分 cloud/local，保存 OpenAI-compatible API root endpoint（适配器在其后使用 `/models`、`/responses`、`/embeddings`）和 Secret 引用；view 只返回 `has_secret`；`name` 唯一。
- **状态 · 所有权 · 寿命**：单个 SQLite 事务持久化资源版本与 Audit；operator 拥有。
- **合法与拒绝实例**：合法 `{name,kind:cloud,endpoint,secret_ref:"file:/run/secrets/x",enabled:true}`；拒绝明文 secret 或重名。
- **验证**：`admin-model-fixtures.json`；`VRC-MGMT-001/002`。

#### `DeploymentView` / `DeploymentWrite` / `DeploymentPatch`
- **定义、Data/Type ID 与唯一来源**：deployment 绑定 backend model 和能力；`D-DEPLOYMENT`；机器源 `openapi`。
- **字段**：`DeploymentWrite{name,provider_id,backend_model,capabilities,enabled}`；`DeploymentView` 增 `id,health,version`。
- **约束 / 不变量**：`provider_id` 必须存在；`capabilities` 12 键（§4.3）。
- **状态 · 所有权 · 寿命**：SQLite 持久；operator 拥有；带 `version`。
- **合法与拒绝实例**：合法引用已存在 provider；拒绝未知 `provider_id`→`ERR-REQ-VALIDATION`。
- **验证**：`openapi`；`VRC-MGMT-001/002`。

#### `ServiceLevelView` / `ServiceLevelWrite` / `ServiceLevelPatch`
- **定义、Data/Type ID 与唯一来源**：ServiceLevel 用 exact ID 绑定一个或多个同等级 deployment；`D-SERVICE-LEVEL`；机器源 `openapi`。
- **字段**：`ServiceLevelWrite{id,deployment_ids[≥1],enabled}`；`ServiceLevelView` 增 `capabilities,version`。
- **约束 / 不变量**：`id ∈ 7 固定 tier`；`capabilities` = 成员交集；成员有序。
- **状态 · 所有权 · 寿命**：SQLite 持久，带 `version`。
- **合法与拒绝实例**：合法绑定有序成员；拒绝非固定 tier/非法交集。
- **验证**：`openapi`；`VRC-MGMT-001/002`。

#### `ProviderAccountUsageSnapshot` / `ProbeResult` / `UsageRecord` / `UsagePage`
- **定义、Data/Type ID 与唯一来源**：账号用量快照、探测结果与 token 用量；`D-PROVIDER-SNAPSHOT`/`D-USAGE-RECORD`；机器源 `openapi`。
- **字段**：见 `llmtier-contract-specification` §3.2。
- **约束 / 不变量**：`unknown ⇒ token 全 null`；`has_more=false ⇒ next_cursor=null`；快照不落 Secret。
- **状态 · 所有权 · 寿命**：账本追加式；快照 operator 显式刷新后替换。
- **合法与拒绝实例**：合法带确认刷新；拒绝缺确认→`ERR-CONFIRM`。
- **验证**：`usage-fixtures.json`；`VRC-INF-004`、`VRC-MGMT-006`。

#### `AuditEvent` / `AuditPage` / `LogEntry` / `LogPage`
- **定义、Data/Type ID 与唯一来源**：审计与脱敏日志；`D-AUDIT-EVENT`/`D-LOG-EVENT`；机器源 `openapi`。
- **字段**：`AuditEvent{id,actor,action,target,result,created_at}`；`LogEntry{id,created_at,level,module,event,message(≤512),request_id?}`。
- **约束 / 不变量**：Secret 值只写不读、不回显、不进日志/audit/backup report；日志禁止 prompt、模型输出、reasoning、向量、Authorization 和原始 headers。
- **状态 · 所有权 · 寿命**：SQLite 持久；审计随策略、日志 7 天。
- **合法与拒绝实例**：合法脱敏写入；拒绝含 Secret 原文。
- **验证**：`admin-model-fixtures.json`；`VRC-LOG-001`。

### 4.3 配置与规则数据结构

#### `ModelCapabilities` / `ProviderUsageProfile*`
- **定义、Data/Type ID 与唯一来源**：能力 12 键与账号 profile；机器源 `openapi`。
- **字段**：见 `llmtier-contract-specification` §3.3。
- **约束 / 不变量**：`secret_ref`/`usage_*_ref` 只写引用；不形成外部 capacity/Seat 产品。
- **状态 · 所有权 · 寿命**：SQLite 持久，operator 拥有。
- **合法与拒绝实例**：合法引用；拒绝明文 secret。
- **验证**：`VRC-MGMT-*`。

#### `ETagPolicy` / `CursorPolicy`
- **定义、Data/Type ID 与唯一来源**：并发与分页规则；本文 §5/§7；机器源 `openapi` 响应 header/`AdminPageMeta`。
- **字段**：每个可变资源 GET/创建/修改成功返回强 `ETag`；PATCH/DELETE 必带 `If-Match`；列表 `limit`、opaque `cursor`、`has_more`/`next_cursor`，cursor 绑定 principal 及原 filter。
- **约束 / 不变量**：`If-Match` 过期→`ERR-STALE` 且不写入；`has_more=false ⇒ next_cursor=null`。
- **状态 · 所有权 · 寿命**：请求级/资源版本级。
- **合法与拒绝实例**：合法带正确 ETag；拒绝缺失/过期→412。
- **验证**：`VRC-MGMT-002`。

### 4.4 通信报文结构（机器源继承）

`ProviderWrite`/`Patch`/`View`、`DeploymentWrite`/`Patch`/`View`、`ServiceLevelWrite`/`Patch`/`View`、`AuditPage`、`LogPage`、`AdminPageMeta`、`ErrorEnvelope` 均为 JSON 报文；字段级 authority `openapi`；阅读视图见 `llmtier-contract-specification` §3。

### 4.5 设备与 FPGA 表项结构（适用时）

不适用：纯软件，无设备/RTL 表项。

### 4.6 运行状态数据结构

#### `RuntimeSnapshot` / `HealthView` / `ReadinessView`
- **定义、Data/Type ID 与唯一来源**：并发/队列快照与就绪事实；机器源 `openapi`；机制见 `mechanisms/access-trust.md`。
- **字段**：各 deployment 的 in-flight/许可与各 tier FIFO 队列深度；`ReadinessView{status,models:[{id,availability}]}`。
- **约束 / 不变量**：`GET /v1/runtime` 为瞬时值，不构成 Slinky capacity/Seat contract；`/readyz` 模型的可用性影响由创建/更新操作反映。
- **状态 · 所有权 · 寿命**：请求级只读。
- **合法与拒绝实例**：正常快照；边界 bootstrap 失败 not_ready。
- **验证**：`VRC-INF-004`、`VRC-UTIL-001/002`。

### 4.7 数据库表结构

Authority `util/migrations/*.sql`；公共可观察表（providers/deployments/service_levels/audit_events/operational_logs/usage_*）见 `llmtier-contract-specification` §3.7。

### 4.8 错误码与错误结构

使用 `ERR-REQ-VALIDATION`、`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`、`ERR-NOTFOUND`、`ERR-CONFLICT`、`ERR-INUSE`、`ERR-STALE`、`ERR-CURSOR`、`ERR-PROVIDER-*`、`ERR-STORE`、`ERR-CONFIRM`（含义与 wire 映射见系统设计 §8.8 与 `llmtier-contract-specification` §4.1）。`interfaces/error-codes/` 未建立 → **Proposed**。

## 5. 接口设计（状态机、顺序和时序）

> 分类同 §2；逐接口适用条件与结果回写 §2 声明。

- **软件接口（Admin HTTP）**：创建/更新先校验，再在单个 SQLite 事务中持久化资源版本与 Audit；对模型可用性的影响由 `/readyz` 反映。PATCH 是局部更新：省略字段保持原值，显式 null 只在 Schema 允许时清空；不得把未提交的 partial write 暴露为成功。
- **人机与维护接口**：UI 不得把配置保存成功显示成 probe 成功；结果不明时先 GET 核对。
- 每个变更操作在提交后才对外可见；`ERR-STALE` 时不写入。

## 6. 接口设计（错误、timeout、重试、幂等和恢复）

> 分类同 §2；逐接口 Error ID 回写 §2 声明。

- 使用 `ERR-REQ-VALIDATION`（400）、`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）、`ERR-NOTFOUND`（404）、`ERR-CONFLICT`/`ERR-INUSE`（409）、`ERR-STALE`（412）、`ERR-PROVIDER-*`（502）、`ERR-STORE`（503）。
- 每个可变资源的 GET/创建/修改成功返回 `ETag`；PATCH/DELETE 必须带 `If-Match`。版本不匹配返回 `ERR-STALE` 412 且不写入；引用冲突返回 `ERR-CONFLICT`/`ERR-INUSE` 409；权限不足返回 `ERR-AUTH-DENIED` 403。
- 管理 mutation 不提供 custom idempotency 状态机；UI 在结果不明时先 GET 核对，不盲目重复 Secret 或删除操作。备份/restore 和 restart 由运维 runbook 管理。
- `ERR-STORE` 503 不用空页冒充无记录。

## 7. 并发、流控、容量与性能

使用 ETag/If-Match/412 防止覆盖并发编辑；列表统一使用 `limit`、opaque `cursor`、稳定 snapshot 和 `has_more/next_cursor`，cursor 绑定 principal 及原 filter。日志支持 level/module/request ID 过滤，store 不可读返回 503。不得创建外部 capacity product。

## 8. 安全、身份、权限和隔离

Secret 值只写不读、不回显、不进日志/audit/backup report。运行日志还禁止 prompt、模型输出、reasoning、向量、Authorization 和原始 headers，message 最长 512 字符。probe 可能产生费用，必须 `confirm_external_call=true` 且由 operator 授权。reload/restart/delete 属于状态变更操作。Admin credential 与 Data Plane credential 分离；不引入 SourceInstance/capacity/Seat。

## 9. 接口设计（版本协商、兼容矩阵与弃用）

> 分类同 §2；逐接口版本结果回写 §2 声明。

Admin API 随 OpenAPI 显式版本变更；无运行时兼容协商。旧访问控制、容量、恢复和调用方管理页面全部退出 current authority。兼容基线 `interfaces/compatibility/compatibility-manifest-v0.3.json`；废弃 ID 不回收。

## 10. Contract fixture、验证与证据

验证 CRUD、If-Match 缺失/过期、partial PATCH 原子性、401/403/409/412、稳定分页、引用冲突、Secret 不回显、cloud/local 字段、exact model、probe 确认、Usage store 503、Usage 无 Cost、审计脱敏、LogPage/禁入内容/日志 store 503 和旧 path absence。向量 `interfaces/vectors/v0.3/admin-model-fixtures.json`、`usage-fixtures.json`、`stateless-gateway-boundary-fixtures.json`。

| 成员/规则 → 设计 V | 提供/消费与 backend | Case / 所需环境 | 实现/运行状态 | Run/证据或缺口 |
|---|---|---|---|---|
| `IF-ADM-PROVIDERS` → VRC-MGMT-001/002 | M004/M001 | admin-model-fixtures | NOT_RUN | — |
| `IF-ADM-USAGE` → VRC-MGMT-006 | M003/M007 | usage-fixtures | NOT_RUN | — |
| Secret/旧术语 absence → VRC-API-002 | M001 | boundary fixtures | NOT_RUN | — |

## 11. 未决项与双方批准

SQLite Operational Store 已经选定为初始化后的唯一运行配置 authority；JSON 只允许空库首次 bootstrap，之后不得覆盖 Store。auth/TLS 和 backup 的具体部署仍是 LLMTier 下游设计，不需要 Slinky/Piko 批准。`interfaces/error-codes/` 未建立（`B-CONTRACT-01`）；Admin UI test、auth/TLS 为 activation gate。
