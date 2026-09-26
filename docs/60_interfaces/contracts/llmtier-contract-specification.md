<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Contract Specification

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-contract-specification` |
| Document Version | `0.3.2-draft.6` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-25` |
| Template ID | `contracts.specification` |
| Template Version | `0.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-contract-specification.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. Contract scope 与 authority

唯一字段级 authority 是 `interfaces/openapi/llmtier.openapi.json` version `0.3-simplified-candidate.8`。Manifest只描述范围和activation，不复制字段。`runtime_activation=false`，本候选不授权runtime。

- **本文拥有的内容**：公共操作的用途、前后置、顺序、幂等、失败语义与调用方合法动作；请求/响应/事件的阅读视图与含义。
- **机器源拥有的内容**：字段名、类型、范围、`required`/`additionalProperties`、枚举值与 wire 编码。本文不手写第二套可漂移的完整结构，冲突以机器源为准。
- **契约基线**：`interfaces/openapi/llmtier.openapi.json`（version `0.3-simplified-candidate.8`，sha256 `b34428126390056e3eb7927ccb219e5185962a3c5483abb6d9f4fab7ed9a417a`）；负向/边界向量 `interfaces/vectors/v0.3/*`；兼容清单 `interfaces/compatibility/compatibility-manifest-v0.3.json`。
- **selector**：OpenAPI `paths` 与 `components.schemas`；本文标题即真实路由/事件名。
- **接口命名空间**：消费者面 `/v1/*`；管理/观测面契约前缀与实现别名同入口。Data Plane 与 Admin 使用独立 Bearer credential。
- **数据/接口身份**：沿用系统设计 §8.8 的 `D-*`/`ERR-*` Data/Error ID 与系统设计 §9 的 `IF-*` Interface/Member ID；本文不复用或回收已发布 ID。
- **Proposed 边界**：`interfaces/error-codes/` 机器 Error 目录尚未建立，故 §4 的错误码含义由系统设计 §8.8 决定、代码值暂以 OpenAPI response schema 为准并标 `Proposed`；`runtime_activation=false` 之外的消费签署仍未完成。

## 2. 接口设计（Operation / Message / Event Catalog）

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口设计用途**分类（面向使用方的 API 与组件/系统间协作的消息与数据流接口），逐接口完整记录，同一接口只定义一次；标题为真实路由/事件名，标题下先给完整接口声明，再就地说明输入/输出，最后按固定六项（Interface/Member ID、用途、提供责任与唯一来源 / 输入与前提 / 成功输出与保证 / 错误与合法下一步 / 交互与生命周期 / 实现与验证）写完。字段级 authority 见 §1。

**类别适用性**：2.1 API ✓（HTTP 路由）｜2.2 消息与数据流接口 ✓（Responses SSE）｜2.3 硬件与固件接口 ✗（纯软件、无连接器/总线/寄存器/FPGA 端口）｜2.4 人机与维护接口 ✗（无 UI/CLI 操作面；Admin Web UI 归管理控制文档，不在此另立接口）。

### 2.0 Operation / Message / Event Catalog

Current consumer operations：Responses、Embeddings、Models、token Usage、health/readiness。Current operator operations：Provider/Deployment/ServiceLevel CRUD、Probe、Provider账号用量显式刷新、Usage、Audit及只读Sanitized Logs。没有跨系统event或调用恢复operation。

| ID | Kind | Producer | Consumer | Sync/Async | Idempotency |
|---|---|---|---|---|---|
| `IF-DP-RESPONSES` | operation | LLMTier | Piko 等 consumer | Async(SSE) | 单请求独立，无自定义幂等键 |
| `IF-DP-EMBEDDINGS` | operation | LLMTier | Slinky 等 consumer | Sync | 同一输入可重放 |
| `IF-DP-MODELS` | operation | LLMTier | consumer | Sync | 只读幂等 |
| `IF-HEALTH` | operation | LLMTier | consumer/运维 | Sync | 只读幂等 |
| `IF-ADM-PROVIDERS` | operation | LLMTier operator | Admin UI | Sync | PATCH partial + ETag |
| `IF-ADM-PROVIDER-USAGE` | operation | LLMTier operator | Admin UI | Sync | GET 只读；POST 显式刷新 |
| `IF-ADM-DEPLOYMENTS` | operation | LLMTier operator | Admin UI | Sync | PATCH partial + ETag |
| `IF-ADM-SERVICE-LEVELS` | operation | LLMTier operator | Admin UI | Sync | PATCH partial + ETag |
| `IF-ADM-PROBES` | operation | LLMTier operator | Admin UI | Sync | 有费用，需确认 |
| `IF-ADM-USAGE` | operation | LLMTier | operator/consumer | Sync | GET 稳定快照；DELETE 显式 |
| `IF-ADM-RUNTIME` | operation | LLMTier | operator | Sync | 只读瞬时值 |
| `IF-ADM-STATS` | operation | LLMTier | operator | Sync | 只读 |
| `IF-ADM-AUDIT` | operation | LLMTier | operator | Sync | 只读 |
| `IF-ADM-LOGS` | operation | LLMTier | operator | Sync | 只读 |
| `IF-MSG-SSE` | event/stream | LLMTier | Piko 等 consumer | Async | 每请求恰一 terminal |

| 成员 ID / 类别 | 机器源 / selector / 版本/revision/hash | request/response/event/error 类型 ID | 正文稳定锚点 | 下游提供/消费 / 实现 / 设计 V → Case |
|---|---|---|---|---|
| `IF-DP-RESPONSES` | `openapi` `paths./v1/responses` @ candidate.8 | `ResponsesRequest` → `ResponseStreamEvent` / `ErrorEnvelope` | 本文 §2.1.1 | M001/M003；VRC-INF-001/002 |
| `IF-DP-EMBEDDINGS` | `openapi` `paths./v1/embeddings` | `EmbeddingRequest` → `EmbeddingResponse` / `ErrorEnvelope` | 本文 §2.1.2 | M001/M003；VRC-INF-001 |
| `IF-MSG-SSE` | `openapi` `ResponseStreamEvent` | `ResponseStreamEvent` | 本文 §2.2.1 | M003 产出、M001 传输；VRC-INF-002/005 |

### 2.1 API（适用时）

#### `POST /v1/responses`

```text
POST /v1/responses
  Content-Type: application/json
  X-Request-ID: string          # client 可缺省；服务端始终回填
  body: ResponsesRequest        # stream 恒 true; store 恒 false
  -> 200 text/event-stream: ResponseStreamEvent (SSE 子集, §2.2.1)
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DP-RESPONSES`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/http_api/app.py` → `src/inference/responses.py`。
- **输入与前提**：`ResponsesRequest`（§3.4 `D-MSG-RESPONSE`）——`model`（必填，exact 逻辑等级名）、`input`（必填）、`stream`（必须 true）、`store`（必须 false）、`tools`/`tool_choice`/`temperature`/`max_output_tokens`/`reasoning`/`include`/`service_tier`/`metadata`；授权=`data` 角色凭据；校验顺序=鉴权→JSON/schema→形态（stream/store）→模型存在→准入。字段全集见 `openapi` `ResponsesRequest`。
- **成功输出与保证**：`ResponseStreamEvent` 流（§2.2.1/§3.4）；`response.created … response.completed|incomplete|failed`，每请求恰好一个 terminal，`usage` 仅 terminal 给出；副作用=登记用量义务→落账本（§3.6）。
- **错误与合法下一步**：`ERR-REQ-VALIDATION`/`ERR-REQ-FIELD`/`ERR-REQ-JSON`（400，未受理）；`ERR-REQ-UNSUPPORTED`（400，`stream=false`）；`ERR-REQ-TOO-LARGE`（413）；`ERR-AUTH-*`（401/403/503）；`ERR-MODEL-NOTFOUND`（404）；`ERR-RATE-LIMIT`（429 + `Retry-After`）；`ERR-MODEL-UNAVAIL`（503）；`ERR-PROVIDER-UNAVAIL`/`ERR-PROVIDER-FAIL`（502/503）；`ERR-PROVIDER-CONTRACT`（502）；`ERR-INTERNAL`（500）。已建连后断开=结果未知，不创建可恢复 Invocation。
- **交互与生命周期**：同步建连后流式；单请求独立模型调用，无 Agent 会话/工具执行；客户端断开结束本次调用并释放许可；不承诺跨系统 exactly-once；版本固定 candidate.8，无 alias/fallback（§8）。
- **实现与验证**：正常 exact tier → 200 SSE + terminal Usage；拒绝 `stream=false` → 400 `unsupported_request`。向量 `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-001/002/003/004`。

#### `POST /v1/embeddings`

```text
POST /v1/embeddings
  body: EmbeddingRequest {model, input, encoding_format?: "float"|"base64", dimensions?: int, user?: str}
  -> 200: EmbeddingResponse {object, data:[EmbeddingItem], model, usage:EmbeddingUsage}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DP-EMBEDDINGS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/http_api/app.py` → `src/inference/embeddings.py`。
- **输入与前提**：`EmbeddingRequest`（§3.4 `D-MSG-EMBEDDING`）——`model`（必填，exact embedding tier）、`input`（必填，string 或 string array）、`encoding_format`（默认 `float`）、`dimensions`、`user`；授权=`data` 角色；校验顺序=鉴权→schema→embedding 模型路由（`embedding_space_id` 兼容）→输入/维数/批上限。
- **成功输出与保证**：`EmbeddingResponse` 向量 `data[]` + `usage{prompt_tokens,total_tokens}`；`encoding_format=base64` 时 `embedding` 固定为连续 little-endian IEEE-754 float32 的 RFC 4648 字符串；副作用=登记用量义务→落账本。
- **错误与合法下一步**：`ERR-REQ-VALIDATION`/`ERR-REQ-TOO-LARGE`（400/413）；`ERR-MODEL-NOTFOUND`（404）；`ERR-RATE-LIMIT`（429）；`ERR-PROVIDER-UNAVAIL`/`ERR-PROVIDER-FAIL`（502/503）；`ERR-STORE`（503）。
- **交互与生命周期**：同步；单请求。同一 embedding 逻辑 model 只绑定同一 `embedding_space_id`、模型版本与预处理契约；非兼容变更必须新建逻辑 model ID，由 Slinky 重建索引。
- **实现与验证**：正常 float/base64 返回向量与 Usage；拒绝不兼容维度/数量/索引 → `ERR-REQ-VALIDATION`。向量 `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-001`。

#### `GET /v1/models` / `GET /v1/models/{model}`

```text
GET /v1/models                    -> 200 ModelList {object, data:[Model]}
GET /v1/models/{model}            -> 200 Model {id, object, created, owned_by, availability, capabilities}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DP-MODELS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/inference/models.py`。
- **输入与前提**：路径 `model`（exact-case 逻辑等级名）；授权=`data` 角色；无 body。
- **成功输出与保证**：`D-MODEL`（§3.2）——目录返回 `ModelList`，detail 返回单个 `Model`；只暴露逻辑等级、`availability` 与 `capabilities`（§3.3），不暴露物理账号/provider。
- **错误与合法下一步**：`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）；detail 未知 exact 名 → `ERR-MODEL-NOTFOUND`（404）。
- **交互与生命周期**：同步只读；幂等；随 Registry 变更反映；模型列表不分页。
- **实现与验证**：正常返回固定 tier 集合；拒绝未知 exact 名 → 404。向量 `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-INF-001`。

#### `GET /healthz` / `GET /readyz`

```text
GET /healthz -> 200 HealthView {status, version}          # 进程存活，无凭据
GET /readyz  -> 200 ReadinessView {status, models:[...]}  # schema+bootstrap+固定等级就绪
             -> 503 (not_ready)
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-HEALTH`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/http_api/health.py`。
- **输入与前提**：无参数、无凭据。
- **成功输出与保证**：`HealthView`/`ReadinessView`（§3.6）；`/readyz` 由 schema、bootstrap 与固定等级共同决定；副作用=无。
- **错误与合法下一步**：bootstrap/schema 失败 → `/readyz` 503 `not_ready`（不接流量）；对应 `ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`。
- **交互与生命周期**：同步只读；无副作用健康/就绪检查。
- **实现与验证**：正常 READY；边界：bootstrap 失败保持 not_ready。`VRC-UTIL-001/002`、`VRC-MGMT-003`。

#### `GET/POST /v1/providers`；`GET/PATCH/DELETE /v1/providers/{provider_id}`

```text
GET    /v1/providers?cursor=&limit=            -> 200 ProviderPage {data:[ProviderView], page:AdminPageMeta}
POST   /v1/providers {ProviderWrite}           -> 201 ProviderView (ETag)
GET    /v1/providers/{provider_id}             -> 200 ProviderView (ETag)
PATCH  /v1/providers/{provider_id} {ProviderPatch} If-Match -> 200 ProviderView (ETag)
DELETE /v1/providers/{provider_id} If-Match    -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-PROVIDERS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/registry.py`。
- **输入与前提**：`ProviderWrite`（`name`/`kind`/`endpoint`/`secret_ref`/`enabled`/`usage`）；`ProviderPatch`（全字段可选，partial）；路径 `provider_id`；`If-Match`（PATCH/DELETE 必填）；授权=`admin` 角色。
- **成功输出与保证**：`ProviderView`（§3.2）+ 强 `ETag`；`secret_ref` 只写不回显（view 只给 `has_secret`）；副作用=同事务写审计（§3.6 `D-AUDIT-EVENT`）。
- **错误与合法下一步**：`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）；重名/唯一冲突 → `ERR-CONFLICT`（409）；被引用删除 → `ERR-INUSE`（409）；`If-Match` 过期 → `ERR-STALE`（412）；未知 ID → `ERR-NOTFOUND`（404）；`ERR-STORE`（503）。
- **交互与生命周期**：同步；PATCH 为 partial（只更新出现字段，省略保持原值，显式 null 仅在 Schema 允许时清空）；DELETE 幂等；ETag 乐观并发。
- **实现与验证**：正常建 provider 返回 201+ETag；拒绝缺 `If-Match` 的 PATCH → `ERR-STALE`。向量 `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-MGMT-001/002`。

#### `GET/POST /v1/providers/{provider_id}/usage`

```text
GET  /v1/providers/{provider_id}/usage                                 -> 200 ProviderAccountUsageSnapshot
POST /v1/providers/{provider_id}/usage {confirm_external_call: true}   -> 200 ProviderAccountUsageSnapshot
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-PROVIDER-USAGE`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/account_usage.py`。
- **输入与前提**：路径 `provider_id`；POST body 仅 `{confirm_external_call: bool}`；授权=`admin` 角色。
- **成功输出与保证**：`ProviderAccountUsageSnapshot`（§3.2）——window/percent/used/quota/reset/source/status/checked_at；POST 显式刷新并替换快照；不落 Secret、不回显 credential。
- **错误与合法下一步**：缺二次确认 → `ERR-CONFIRM`（400）；未知 provider → `ERR-NOTFOUND`（404）；`ERR-AUTH-*`（401/403）；上游失败记入快照 `status`（HTTP 200 返回快照事实）。
- **交互与生命周期**：同步；GET 只读幂等；POST 仅在显式确认后触发外部调用（不自动轮询）；MiniMax 用 Provider API Key 或独立引用，火山用独立 OpenAPI AK/SK。
- **实现与验证**：正常带确认刷新；拒绝缺确认 → 400。`VRC-MGMT-*`、`VRC-DIAG-004`。

#### `GET/POST /v1/deployments`；`GET/PATCH/DELETE /v1/deployments/{deployment_id}`

```text
GET    /v1/deployments?cursor=&limit=              -> 200 DeploymentPage {data:[DeploymentView], page}
POST   /v1/deployments {DeploymentWrite}           -> 201 DeploymentView (ETag)
GET    /v1/deployments/{deployment_id}             -> 200 DeploymentView (ETag)
PATCH  /v1/deployments/{deployment_id} {DeploymentPatch} If-Match -> 200 DeploymentView (ETag)
DELETE /v1/deployments/{deployment_id} If-Match    -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-DEPLOYMENTS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/registry.py`。
- **输入与前提**：`DeploymentWrite`（`name`/`provider_id`/`backend_model`/`capabilities`/`enabled`）；`DeploymentPatch`（全字段可选）；`If-Match`；授权=`admin`。
- **成功输出与保证**：`DeploymentView`（§3.2）+ ETag；`capabilities` 为 §3.3 `D-CAPABILITY` 12 键；副作用=同事务审计。
- **错误与合法下一步**：未知 `provider_id` → `ERR-REQ-VALIDATION`（400）；重名 → `ERR-CONFLICT`（409）；被 tier 引用删除 → `ERR-INUSE`（409）；`ERR-STALE`（412）；`ERR-AUTH-*`。
- **交互与生命周期**：同步；partial PATCH；ETag 乐观并发；Pause/Resume 经 `enabled`。
- **实现与验证**：正常引用已存在 provider；拒绝未知 provider。`VRC-MGMT-001/002`。

#### `GET/POST /v1/service-levels`；`GET/PATCH/DELETE /v1/service-levels/{service_level_id}`

```text
GET    /v1/service-levels?cursor=&limit=               -> 200 ServiceLevelPage {data:[ServiceLevelView], page}
POST   /v1/service-levels {ServiceLevelWrite}          -> 201 ServiceLevelView (ETag)
GET    /v1/service-levels/{service_level_id}           -> 200 ServiceLevelView (ETag)
PATCH  /v1/service-levels/{service_level_id} {ServiceLevelPatch} If-Match -> 200 ServiceLevelView (ETag)
DELETE /v1/service-levels/{service_level_id} If-Match  -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-SERVICE-LEVELS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/registry.py`。
- **输入与前提**：`ServiceLevelWrite`（`id` 固定 tier 名/`deployment_ids[]` 有序/`enabled`）；`ServiceLevelPatch`（`deployment_ids`/`enabled`）；`If-Match`；授权=`admin`。
- **成功输出与保证**：`ServiceLevelView`（§3.2）+ ETag；`capabilities` 为成员交集；副作用=同事务审计。
- **错误与合法下一步**：非固定 tier / 非法成员交集 → `ERR-REQ-VALIDATION`（400）；`ERR-CONFLICT`（409）；被引用 → `ERR-INUSE`（409）；`ERR-STALE`（412）。
- **交互与生命周期**：同步；partial PATCH；ETag；成员顺序稳定。
- **实现与验证**：正常绑定有序成员；拒绝非固定 tier 名。`VRC-MGMT-001/002`。

#### `POST /v1/probes`

```text
POST /v1/probes {deployment_id, confirm_external_call: true} -> 200 ProbeResult
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-PROBES`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/admin.py`。
- **输入与前提**：`ProbeRequest {deployment_id, confirm_external_call}`；授权=`admin` + 二次确认。
- **成功输出与保证**：`ProbeResult {deployment_id,status,checked_at,may_have_incurred_cost}`；副作用=可能产生上游调用费用（由 `may_have_incurred_cost` 声明）。
- **错误与合法下一步**：缺确认 → `ERR-CONFIRM`（400）；未知 deployment → `ERR-NOTFOUND`（404）；上游失败 → `ERR-PROVIDER-*`（502）。
- **交互与生命周期**：同步；显式触发，不自动轮询；reload/restart/delete 属于状态变更操作。
- **实现与验证**：正常带确认探测；拒绝缺确认 → 400。`VRC-DIAG-004`。

#### `GET/DELETE /v1/usage`

```text
GET    /v1/usage?cursor=&limit=&from=&to=&model=&request_id= -> 200 UsagePage
DELETE /v1/usage?model=&deployment_id=                        -> 200 object   # 仅 operator
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-USAGE`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/inference/usage.py`。
- **输入与前提**：GET `from`/`to` 必填，可选 `model`/`request_id`/`cursor`/`limit`；DELETE 过滤参数；GET 可按主体或全部，DELETE 仅 `admin`。
- **成功输出与保证**：`UsagePage`（§3.2，含 `snapshot_id`/`snapshot_at`；measured/estimated/unknown 可区分，unknown 不填零）；DELETE 返回清空结果；副作用=DELETE 改变账本（仅显式 operator 操作）。
- **错误与合法下一步**：`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403，非 admin DELETE 拒绝）；`ERR-CURSOR`（400）；`ERR-REQ-VALIDATION`（400）；`ERR-STORE`（503，不用空页冒充无记录）；`ERR-REQ-VALIDATION`（400）。
- **交互与生命周期**：GET 稳定分页快照（cursor 绑定 principal/授权/原 filter，不跨 filter 复用）；同 request 只选择 snapshot 冻结版本、绝不重复相加；dispatch 前必须先有持久 unknown Usage 义务，terminal 后写失败/崩溃重启仍返回 unknown；DELETE 显式。
- **实现与验证**：正常分页；拒绝非 admin 清空；拒绝过期 cursor。向量 `interfaces/vectors/v0.3/usage-fixtures.json`；`VRC-MGMT-006`。

#### `GET /v1/runtime`

```text
GET /v1/runtime -> 200 object    # 并发/队列快照
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-RUNTIME`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/inference/routing.py`。
- **输入与前提**：无参数；授权=`admin`。
- **成功输出与保证**：各 deployment 的 in-flight/许可与各 tier FIFO 队列深度快照；副作用=无。
- **错误与合法下一步**：`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）。
- **交互与生命周期**：同步只读；瞬时值，不构成 Slinky capacity/Seat contract。
- **实现与验证**：正常返回快照。`VRC-INF-004`。

#### `GET /v1/stats`

```text
GET /v1/stats?from=&to=&group_by=tier -> 200 object
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-STATS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/admin.py`。
- **输入与前提**：`from`/`to`（必填，RFC3339，`[from,to)`）、`group_by`（默认 `tier`）；授权=`admin`。
- **成功输出与保证**：聚合结果；副作用=无。
- **错误与合法下一步**：缺 `from`/`to` 或非法 → `ERR-REQ-VALIDATION`（400）；`ERR-STORE`（503）。
- **交互与生命周期**：同步只读；窗口稳定。
- **实现与验证**：正常窗口聚合；拒绝缺参数 → 400。`VRC-MGMT-006`。

#### `GET /v1/audit`

```text
GET /v1/audit?limit= -> 200 AuditPage {data:[AuditEvent], page}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-AUDIT`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/management/audit.py`。
- **输入与前提**：`limit`；授权=`admin`。
- **成功输出与保证**：`D-AUDIT-EVENT`（§3.2）列表；不含 prompt/output/Secret。
- **错误与合法下一步**：`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）；`ERR-STORE`（503）。
- **交互与生命周期**：同步只读；按审计策略保留。
- **实现与验证**：正常返回脱敏审计。`VRC-MGMT-*`。

#### `GET /v1/logs`

```text
GET /v1/logs?limit=&level=&module=&request_id=&from=&to= -> 200 LogPage {data:[LogEntry], page}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-LOGS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；文件·symbol `src/log/logs.py`。
- **输入与前提**：`limit`/`level`/`module`/`request_id`/`from`/`to`；授权=`admin`。
- **成功输出与保证**：`D-LOG-EVENT`（§3.2）列表（写前脱敏）；不含 Secret/凭据/完整正文；只读，与管理动作 Audit 分离。
- **错误与合法下一步**：缺 `from`/`to` → `ERR-REQ-VALIDATION`（400）；`ERR-STORE`（503，返回 503 而非空页）。
- **交互与生命周期**：同步只读；7 天保留；稳定快照与逐页授权；store 不可读返回 503。
- **实现与验证**：正常过滤查询；拒绝缺时间窗。向量 `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-LOG-001`。

### 2.2 消息与数据流接口（适用时）

#### `Responses SSE 事件子集`

```text
stream: text/event-stream
  event: response.created | response.output_item.added | response.output_text.delta
       | response.refusal.delta | response.reasoning_summary_part.done
       | response.reasoning_summary_text.delta | response.reasoning_text.delta
       | response.function_call_arguments.delta | response.function_call_arguments.done
       | response.output_item.done | response.completed | response.incomplete | response.failed
       | error
  data: ResponseStreamEvent (每事件带 type/sequence_number)
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MSG-SSE`；规格已定、Implemented；唯一契约=`openapi` `ResponseStreamEvent`；文件·symbol `src/http_api/sse.py`、`src/inference/responses.py`。
- **输入与前提**：一次已受理的 `IF-DP-RESPONSES`（§2.1.1）；输出=SSE 帧；`X-Request-ID` 为 task 头，可接收标准 `traceparent`/correlation context。
- **成功输出与保证**：标准 SSE 事件子集（§3.4 `D-MSG-SSE`）；每 output item 稳定 `id` 与 `output_index`；每请求恰好一个 terminal（`completed|incomplete|failed`）；成功流 terminal response 携带可用 `usage`。
- **错误与合法下一步**：流内失败发 `error` 事件或 `response.failed` terminal；上游失败不伪造完成；客户端断开=结果未知、释放许可（§8）。
- **交互与生命周期**：异步流；从受理到 terminal 的顺序由 `sequence_number` 稳定；`store:false` 不保留 conversation；无 custom recovery/Invocation。
- **实现与验证**：正常完整流以 terminal 结束；边界：上游失败发 `error`/`failed`。向量 `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-002/005`。

### 2.3 硬件与固件接口（适用时）

不适用：LLMTier 为纯软件、单进程、单服务，无连接器、总线、寄存器或 FPGA 端口（tailoring `LT-TL-003`）。

### 2.4 人机与维护接口（适用时）

不适用：本契约不定义 UI 页面或 CLI；中文 Admin Web UI 的同源 Admin API 调用由 `llmtier-management-control` 记录，运维 runbook 由运维文档维护。

## 3. 数据结构设计（Request、Response、Event 与数据对象）

> 按 STD `design-data-interface-format` 1.2.0 §2：主章“数据结构设计”，章内按**数据性质**分类。wire/机器类型以 §1 的 `openapi` 与 `interfaces/vectors/v0.3/*` 为机器权威，本节只给阅读视图与含义，不复制字段权威。继承结构只定位原定义。

**类别适用性**：3.1 公共基础类型与枚举 ✓｜3.2 业务与操作数据结构 ✓｜3.3 配置与规则数据结构 ✓｜3.4 通信报文结构 ✓（机器源继承）｜3.5 设备与 FPGA 表项结构 ✗（纯软件）｜3.6 运行状态数据结构 ✓｜3.7 数据库表结构 ✓（authority = `util/migrations/*.sql`）。错误码与错误结构见 §4.1。

### 3.1 公共基础类型与枚举

**3.1.1 `ErrorType` / `ErrorCode`（公共基础类型与枚举）**

```text
`type` ∈ {`invalid_request_error`,`authentication_error`,`permission_error`,`not_found_error`,`conflict_error`,`rate_limit_error`,`provider_error`,`service_unavailable_error`,`internal_error`}；`code` ∈ {`invalid_request`,`authentication_failed`,`permission_denied`,`model_not_found`,`resource_not_found`,`resource_in_use`,`version_conflict`,`rate_limit_exceeded`,`provider_failure`,`service_unavailable`,`usage_store_unavailable`,`internal_error`}。
```

- **Data/Type ID、用途与来源**：

  统一错误信封中的机器分类与公共码值；`D-ERROR-ENVELOPE` 的内层字段；机器源 `openapi` `ErrorDetail`，公共含义由系统设计 §8.8 决定。

- **字段与约束**：

  `additionalProperties:false`；`code` 与 `type` 成对；`ERR-*` 公共 ID 与 wire `code` 的映射见 §4.1；不得自定义未列码。

- **跨字段与寿命**：

  无状态枚举；随错误响应请求级返回。

- **合法/拒绝实例**：

  合法 `{type:"provider_error",code:"provider_failure"}`；拒绝未知 `type`/`code` 值。

- **验证**：

  `openapi` `ErrorDetail`；`VRC-API-002`。

**3.1.2 `ResponseStatus` / `availability` / `measurement_status` / `source`（公共基础类型与枚举）**

```text
`ResponseStatus` ∈ {`completed`,`failed`,`incomplete`}（流内可 `in_progress`）；`availability` ∈ {`available`,`degraded`,`unavailable`}（`ReadinessView` 与 `Model`）；`measurement_status` ∈ {`measured`,`estimated`,`unknown`}；`source` ∈ {`provider`,`gateway_estimate`,`unavailable`}。
```

- **Data/Type ID、用途与来源**：

  跨结构的共享枚举；机器源 `openapi` `ResponsesResponse`、`Model`、`ReadinessView`、`UsageRecord`。

- **字段与约束**：

  `measurement_status=unknown ⇒ source=unavailable 且 token 全 null`；`measured ⇒ source=provider`；`estimated ⇒ source=gateway_estimate`。

- **跨字段与寿命**：

  内联于所属结构，随其持久/请求级存在。

- **合法/拒绝实例**：

  合法 `measurement_status=measured,source=provider`；边界 `unknown` 且 token 全 null（不补零）。

- **验证**：

  `openapi`；`VRC-INF-004`。

**3.1.3 `TierId` / `encoding_format`（公共基础类型与枚举）**

```text
`TierId` = 固定集合 {`Senior`,`Junior`,`Worker`,`Associate`,`Engineer`,`Executor`,`Embedding-v1`}；`encoding_format` ∈ {`float`,`base64`}，默认 `float`。
```

- **Data/Type ID、用途与来源**：

  固定逻辑等级名与 embedding 编码选项；本设计 §3.3/§3.4；机器源 `openapi` `EmbeddingRequest`、`ServiceLevelView`。

- **字段与约束**：

  tier `id` 为 exact-case；`base64` 内容固定为连续 little-endian IEEE-754 float32。

- **跨字段与寿命**：

  tier 名持久于 `service_levels`；`encoding_format` 请求级。

- **合法/拒绝实例**：

  合法 `Worker`、`float`；拒绝非固定 tier 名或未知 `encoding_format`。

- **验证**：

  `openapi`；`VRC-INF-001`、`VRC-MGMT-001`。

### 3.2 业务与操作数据结构

**3.2.1 `ProviderView` / `ProviderWrite` / `ProviderPatch`（业务与操作数据结构）**

```text
`ProviderWrite{name,kind∈{cloud,local},endpoint(uri),secret_ref:str?,enabled,usage?}`；`ProviderPatch` 同字段全可选且 `minProperties:1`；`ProviderView{id,name,kind,endpoint,has_secret,enabled,usage:ProviderUsageProfileView,request_usage:ProviderRequestUsageView,version:int≥1}`。
```

- **Data/Type ID、用途与来源**：

  provider 资源的写模型与视图；`D-PROVIDER` 的 wire 投影；机器源 `openapi` `ProviderWrite`/`ProviderPatch`/`ProviderView`。

- **字段与约束**：

  `secret_ref` 只写不回显；`name` 唯一；`reply` 中只有 `has_secret`。

- **跨字段与寿命**：

  SQLite 持久，operator 经 Registry 拥有，带 `version` 乐观并发。

- **合法/拒绝实例**：

  合法 `{name,kind:cloud,endpoint,secret_ref:"file:/run/secrets/x",enabled:true}`；拒绝明文 `secret_ref="sk-..."` 或重名。

- **验证**：

  `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-MGMT-001/002`。

**3.2.2 `DeploymentView` / `DeploymentWrite` / `DeploymentPatch`（业务与操作数据结构）**

```text
`DeploymentWrite{name,provider_id,backend_model,capabilities:ModelCapabilities,enabled}`；`DeploymentView` 增 `id,health∈{unknown,healthy,degraded,unhealthy},version`。
```

- **Data/Type ID、用途与来源**：

  deployment 资源模型；`D-DEPLOYMENT`；机器源 `openapi` `DeploymentWrite`/`DeploymentPatch`/`DeploymentView`。

- **字段与约束**：

  `provider_id` 必须存在；`capabilities` 为 12 键（§3.3）。

- **跨字段与寿命**：

  SQLite 持久；operator 经 Registry 拥有。

- **合法/拒绝实例**：

  合法引用已存在 provider；拒绝未知 `provider_id` → `ERR-REQ-VALIDATION`。

- **验证**：

  `openapi`；`VRC-MGMT-001/002`。

**3.2.3 `ServiceLevelView` / `ServiceLevelWrite` / `ServiceLevelPatch`（业务与操作数据结构）**

```text
`ServiceLevelWrite{id,deployment_ids[≥1],enabled}`；`ServiceLevelPatch{deployment_ids?,enabled?}`；`ServiceLevelView` 增 `capabilities,version`。
```

- **Data/Type ID、用途与来源**：

  逻辑 tier 资源模型；`D-SERVICE-LEVEL`；机器源 `openapi`。

- **字段与约束**：

  `id ∈ 7 固定 tier`；`capabilities` = 成员交集；`deployment_ids` 有序。

- **跨字段与寿命**：

  SQLite 持久，带 `version`。

- **合法/拒绝实例**：

  合法绑定有序成员；拒绝非固定 tier 名/非法交集。

- **验证**：

  `openapi`；`VRC-MGMT-001/002`。

**3.2.4 `UsageRecord` / `UsagePage` / `ProviderAccountUsageSnapshot` / `ProbeResult`（业务与操作数据结构）**

```text
`UsageRecord{request_id,record_version≥1,is_final,model,endpoint∈{/v1/responses,/v1/embeddings},recorded_at,updated_at,measurement_status,source,input_tokens:int?,output_tokens:int?,total_tokens:int?,cached_input_tokens:int?,cache_write_tokens:int?,reasoning_tokens:int?}`；`UsagePage{data[],next_cursor:str?,has_more,snapshot_id,snapshot_at}`；`ProviderAccountUsageSnapshot{provider,source,status∈{ok,unavailable,unsupported,unlimited,not_refreshed},used,quota,remaining,percent,reset_at,window,windows,checked_at,error}`；`ProbeResult{deployment_id,status,checked_at,may_have_incurred_cost}`。
```

- **Data/Type ID、用途与来源**：

  用量与探测的返回结构；`D-USAGE-RECORD`/`D-PROVIDER-SNAPSHOT`；机器源 `openapi` `UsageRecord`/`UsagePage`/`ProviderAccountUsageSnapshot`/`ProbeResult`。

- **字段与约束**：

  `unknown ⇒ token 全 null`；`has_more=false ⇒ next_cursor=null`；同 request 版本绝不累计。

- **跨字段与寿命**：

  账本追加式、按 principal 隔离、按保留策略；快照 operator 显式刷新后替换。

- **合法/拒绝实例**：

  合法 `record_version=2,is_final=true,measurement_status=measured`；边界 `unknown` token 全 null。

- **验证**：

  `interfaces/vectors/v0.3/usage-fixtures.json`；`VRC-INF-004`、`VRC-MGMT-006`。

**3.2.5 `AuditEvent` / `AuditPage` / `LogEntry` / `LogPage`（业务与操作数据结构）**

```text
`AuditEvent{id,actor,action,target,result,created_at}`；`LogEntry{id(≤128),created_at,level∈{info,warning,error},module(≤64),event(≤128),message(≤512,写前脱敏),request_id:str?(≤128)}`。
```

- **Data/Type ID、用途与来源**：

  审计与脱敏日志结构；`D-AUDIT-EVENT`/`D-LOG-EVENT`；机器源 `openapi`。

- **字段与约束**：

  不含 Secret/prompt/output/reasoning/向量/credential/原始 header；`LogEntry.message` 上限 512。

- **跨字段与寿命**：

  SQLite 持久；审计随管理策略、日志 7 天。

- **合法/拒绝实例**：

  合法写前脱敏后落库；拒绝含 Secret 原文（须脱敏）。

- **验证**：

  `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-LOG-001`。

### 3.3 配置与规则数据结构

**3.3.1 `ModelCapabilities`（配置与规则数据结构）**

```text
`responses`/`embeddings`/`tools`/`structured_outputs`:bool；`input_modalities`/`output_modalities`:str[]；`context_window`/`max_output_tokens`:int?；`embedding_space_id`:str?；`embedding_dimensions`:int[]?；`embedding_max_batch_inputs`/`embedding_max_input_tokens`:int?。
```

- **Data/Type ID、用途与来源**：

  tier/deployment 的 12 键能力固定集合；机器源 `openapi` `ModelCapabilities`。

- **字段与约束**：

  12 键固定且必填；tier 能力 = 成员 deployment 交集。

- **跨字段与寿命**：

  内嵌 `ProviderView`/`DeploymentView`/`ServiceLevelView` 持久；operator 拥有。

- **合法/拒绝实例**：

  合法 12 键齐全；拒绝缺键或非交集。

- **验证**：

  `openapi` `ModelCapabilities`；`VRC-MGMT-*`。

**3.3.2 `ProviderUsageProfileWrite` / `ProviderUsageProfileView`（配置与规则数据结构）**

```text
Write{`usage_provider`∈{none,local,minimax,volc},`usage_api_key_ref`?/`usage_access_key_ref`?/`usage_secret_key_ref`?,`max_concurrent_requests`≥1,`min_request_interval_ms`≥0,`requests_per_minute`≥0}；View 以 `has_usage_*` 布尔替代引用值。
```

- **Data/Type ID、用途与来源**：

  provider 账号用量/并发 profile；机器源 `openapi`。

- **字段与约束**：

  引用只写不回显；`usage_provider=none` 时无外部调用。

- **跨字段与寿命**：

  SQLite 持久；operator 拥有。

- **合法/拒绝实例**：

  合法 `{usage_provider:minimax,max_concurrent_requests:2}`；拒绝回显 secret。

- **验证**：

  `openapi`；`VRC-MGMT-*`。

**3.3.3 `TrustedLanPolicy` / `AuthPolicy`（配置与规则数据结构）**

- **Data/Type ID、用途与来源**：

  访问策略规则；本设计 §7；机器源 `openapi` security（`BearerAuth`/`AdminBearerAuth`）。

- **字段与约束**：

  `DataBearer`/`AdminBearer`（独立）；`trustedLanMode`：客户端在 `192.168.1.0/24` 且开启时可免 Bearer 使用 `trusted-lan-consumer`/`trusted-lan-operator`。

  credential 只用于授权，不形成 Client/Source DTO；Admin 与 Data credential 分离；生产使用 TLS。

- **跨字段与寿命**：

  部署配置，运维拥有。

- **合法/拒绝实例**：

  合法 `Authorization: Bearer <data-token>`；拒绝缺/越权凭据 → `ERR-AUTH-*`。

- **验证**：

  `VRC-API-002`。

### 3.4 通信报文结构（机器源继承）

> 本类全部继承机器源（`openapi` + `interfaces/vectors/v0.3/*`），只给阅读视图与含义。

**3.4.1 `ResponsesRequest` / `ResponsesResponse` / `ResponseStreamEvent`（通信报文结构（机器源继承））**

- **Data/Type ID、用途与来源**：

  OpenAI-compatible Responses 请求/响应/流事件；机器源 `openapi` `ResponsesRequest`/`ResponsesResponse`/`ResponseStreamEvent`。

- **字段与约束**：

  `stream:true`、`store:false` 为受理前提；每请求恰一 terminal；`usage` 仅 terminal 给出；`input` 支持 string 或 item 数组（easy message、assistant 历史、opaque reasoning、function call/output、image tool result）。

- **跨字段与寿命**：

  wire 载荷请求级；机读 authority `openapi`。

- **合法/拒绝实例**：

  合法标准 Responses 请求 → SSE + terminal Usage；拒绝 `stream=false` → `ERR-REQ-UNSUPPORTED`。

- **验证**：

  `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-001/002`。

**3.4.2 `EmbeddingRequest` / `EmbeddingResponse` / `EmbeddingItem` / `EmbeddingUsage`（通信报文结构（机器源继承））**

- **Data/Type ID、用途与来源**：

  OpenAI-compatible Embeddings 请求/响应；机器源 `openapi`。

- **字段与约束**：

  请求与响应表示一致；base64 为连续 little-endian IEEE-754 float32；维数须在模型支持集合内；同一逻辑 model 保持同一 `embedding_space_id`。

- **跨字段与寿命**：

  wire 载荷请求级。

- **合法/拒绝实例**：

  合法 float/base64 返回向量与 Usage；拒绝不兼容维数/数量/索引。

- **验证**：

  `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-001`。

**3.4.3 `Model` / `ModelList`（通信报文结构（机器源继承））**

```text
`Model{id,object:"model",created,owned_by:"llmtier",availability,capabilities:ModelCapabilities}`。
```

- **Data/Type ID、用途与来源**：

  逻辑等级目录条目；机器源 `openapi` `Model`/`ModelList`。

- **字段与约束**：

  `id` exact-case；不暴露物理 provider/account。

- **跨字段与寿命**：

  只读投影，随 Registry 变更。

- **合法/拒绝实例**：

  合法返回固定 tier；拒绝未知 exact 名 → `ERR-MODEL-NOTFOUND`。

- **验证**：

  `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-INF-001`。

**3.4.4 `ErrorEnvelope`（通信报文结构（机器源继承））**

```text
`error.message:str`/`error.type:ErrorType`/`error.code:ErrorCode`/`error.param:str?`（4 字段全必填，`param` 可 null）。
```

- **Data/Type ID、用途与来源**：

  统一错误载荷 `{error:{message,type,code,param}}`；机器源 `openapi` `ErrorEnvelope`/`ErrorDetail`；含义见系统设计 §8.8。

- **字段与约束**：

  码值语义由 §4.1/系统 §8.8 决定；不含 Secret/凭据/完整正文；429 可带 `Retry-After`。

- **跨字段与寿命**：

  请求级返回。

- **合法/拒绝实例**：

  合法 `{error:{type:"model_not_found",code:"model_not_found",param:null}}`；边界：未知端点 → `ERR-NOTFOUND`。

- **验证**：

  `interfaces/vectors/v0.3/stateless-gateway-boundary-fixtures.json`；`VRC-API-*`。

### 3.5 设备与 FPGA 表项结构（适用时）

不适用：LLMTier 为纯软件、单进程、单服务，无连接器、总线、寄存器或 FPGA 端口（tailoring `LT-TL-003`）。

### 3.6 运行状态数据结构

**3.6.1 `D-USAGE-OBLIGATION` / `D-USAGE-HEAD` / `D-PROVIDER-BINDING`（运行状态数据结构）**

```text
`D-USAGE-OBLIGATION{principal_id,request_id,model,endpoint,recorded_at,dispatch_authorized_at}`；`D-USAGE-HEAD{principal_id,request_id,head_record_version,updated_at}`；`D-PROVIDER-BINDING{principal_id,request_id,provider_id,deployment_id,bound_at}`。
```

- **Data/Type ID、用途与来源**：

  dispatch 前的用量义务、单调 head 与请求-provider 绑定；本设计 §3.2/系统设计 §8.2；authority `util/migrations/*.sql`。

- **字段与约束**：

  义务 PK `(principal_id,request_id)` 且必须先于 dispatch；head 单调且 FK 指向存在版本；绑定至多一个。

- **跨字段与寿命**：

  M003 写；按 principal 隔离；追加式，随账本保留。

- **合法/拒绝实例**：

  合法：非流式外请求登记 unknown 义务后 dispatch；拒绝：`stream=false` → `ERR-REQ-UNSUPPORTED`（无义务副作用）。

- **验证**：

  `VRC-INF-004`、`VRC-MGMT-006`。

**3.6.2 `HealthView` / `ReadinessView`（运行状态数据结构）**

```text
`HealthView{status:"ok",version}`；`ReadinessView{status∈{ready,degraded,not_ready},models:[{id,availability∈{available,degraded,unavailable}}]}`。
```

- **Data/Type ID、用途与来源**：

  进程存活与就绪事实；机器源 `openapi`。

- **字段与约束**：

  `/readyz` 由 schema+bootstrap+固定等级共同决定；失败保持 `not_ready` 不接流量。

- **跨字段与寿命**：

  请求级只读瞬时值。

- **合法/拒绝实例**：

  正常 `ready`；边界 bootstrap 失败 → 503 `not_ready`。

- **验证**：

  `VRC-UTIL-001/002`、`VRC-MGMT-003`。

### 3.7 数据库表结构

**3.7.1 `providers` / `deployments` / `service_levels` / `usage_*` / `provider_*` / `audit_events` / `operational_logs`（数据库表结构）**

> authority = `util/migrations/*.sql`（由 M007 `migrate()` 执行）；本契约仅登记公共可观察表，列级定义见 `util.isd` §4.4。

| 表 | 主键 / 唯一 | 写入者 / 读者 | 寿命 |
|---|---|---|---|
| `providers` | `id` PK；`name` UNIQUE | M004 / M003 | 库寿命 |
| `deployments` | `id` PK；`name` UNIQUE；`provider_id` FK | M004 / M003 | 库寿命 |
| `service_levels` / `service_level_deployments` | `service_levels.id`；成员 `(service_level_id,deployment_id,ordinal)` 有序唯一 | M004 / M003 | 库寿命 |
| `usage_obligations` | `(principal_id,request_id)` | M003 / 查询 | 账本保留 |
| `usage_record_versions` | `(principal_id,request_id,record_version)` | M003 / 查询 | 账本保留 |
| `usage_heads` | `(principal_id,request_id)` | M003 / 查询 | 账本保留 |
| `provider_request_bindings` | `(principal_id,request_id)` | M003 / 查询 | 账本保留 |
| `provider_usage_snapshots` | `provider_id` | M004 / 查询 | operator 刷新 |
| `audit_events` | `id` PK | M004 / M005 | 审计策略 |
| `operational_logs` | `id` PK | M008 / M005 | 7 天 |

- **Data/Type ID、用途与来源**：

  Authority = `util/migrations/*.sql`（由 M007 `migrate()` 执行）；本契约登记下列公共可观察表，列级定义见 `util.isd` §4.4。

- **字段与约束**：

  配置带 `version` 乐观并发；账本追加式不可改、同 request 版本绝不累计；审计与 Registry 变更同事务。

- **跨字段与寿命**：

  `providers`/`deployments`/`service_levels` 库寿命；`usage_*` 账本保留；`provider_usage_snapshots` operator 刷新后替换；`audit_events` 按审计策略；`operational_logs` 7 天。

- **合法/拒绝实例**：

  合法：空库由 M007 一次性建表；拒绝：非空库 schema 版本不符 → `ERR-SCHEMA`，拒绝启动。

- **验证**：

  `util/migrations/*.sql`；`VRC-UTIL-001/002`、`VRC-MGMT-006`。

## 4. 数据结构设计（状态、错误和 blocker catalog）

### 4.1 错误码与错误结构

公共错误码含义由 `docs/20_system_design/llmtier-system-design.md` §8.8 决定，本文只引用其 `ERR-*` ID、逐个失败条件与调用方合法动作；不新增公共码。机器 Error 目录 `interfaces/error-codes/` 尚未建立 → **Proposed**；当前 wire 码值以 `openapi` `ErrorDetail.code` 为准，映射差异记录在“机器码值”列。

| Error ID（系统 §8.8） | 机器码值（`openapi`） | 触发事实 | 结果与副作用 | 调用方动作 | 禁用/边界 |
|---|---|---|---|---|---|
| `ERR-REQ-VALIDATION` | `invalid_request` | schema/字段/范围非法 | 未受理；无上游/义务副作用 | 修正 `param` 后重试 | 不含鉴权/形态失败 |
| `ERR-REQ-FIELD` | `invalid_request` | 未知字段（`additionalProperties:false`） | 未受理 | 移除未知字段重试 | — |
| `ERR-REQ-JSON` | `invalid_request` | body 非合法 JSON | 未受理 | 修正 JSON | — |
| `ERR-REQ-TOO-LARGE` | `invalid_request` | body 超 2 MB 上限 | 未受理 | 缩小 body；不得分片绕过 | §12.1 |
| `ERR-REQ-UNSUPPORTED` | `invalid_request` | 不支持形态（`stream=false`） | 未受理 | 改用标准 SSE | — |
| `ERR-AUTH-REQUIRED` | `authentication_failed` | 受保护端点缺凭据 | 未受理 | 携带 Bearer | 与 `ERR-AUTH-NOCFG` 区分 |
| `ERR-AUTH-DENIED` | `permission_denied` | 凭据无权 | 未受理；不泄露存在性 | 更换权限凭据 | — |
| `ERR-AUTH-NOCFG` | `authentication_failed` | 未配置鉴权却访问受保护端点 | 未受理；不可判定授权 | 联系运维配置；不得自行关闭 | — |
| `ERR-MODEL-NOTFOUND` | `model_not_found` | exact tier 无匹配 | 未受理；无上游/义务 | 用 `/v1/models` 的 exact 名 | — |
| `ERR-NOTFOUND` | `resource_not_found` | 路径/资源 ID 不存在 | 未受理 | 修正路径/ID | — |
| `ERR-CONFLICT` | `invalid_request`（Proposed） | 唯一性冲突（name 重复） | 写入未生效；事务回滚 | 改名后重试 | wire 无专用码，Proposed |
| `ERR-INUSE` | `resource_in_use` | 被引用资源不能删 | 删除未生效 | 先解除引用 | — |
| `ERR-STALE` | `version_conflict` | `If-Match` 过期 | 写入未生效 | 重新 GET 取 ETag | 不覆盖 |
| `ERR-CURSOR` | `invalid_request` | cursor 失效/不匹配 | 未返回页 | 从头重开查询 | — |
| `ERR-RATE-LIMIT` | `rate_limit_exceeded` | 队列满或排队超 30s | 未受理；带 `Retry-After` | 按 `Retry-After` 退避 | — |
| `ERR-PROVIDER-UNAVAIL` | `service_unavailable` | 建连/首字节/空闲超时或上游 5xx | 本次失败；义务按 measured/unknown 收敛 | 标准重试；不静默 fallback | — |
| `ERR-PROVIDER-FAIL` | `provider_failure` | 上游/注入故障 | 本次失败；失败事实可入快照 | 重试或换等级 | — |
| `ERR-PROVIDER-CONTRACT` | `provider_failure` | 上游响应无法归一 | 本次失败；无有效 Usage | 不重试（确定性），上报 | — |
| `ERR-MODEL-UNAVAIL` | `service_unavailable` | tier 全部候选不健康 | 未受理 | 稍后/换等级 | — |
| `ERR-STORE` | `usage_store_unavailable` | 存储不可用 | 本次查询/写入失败 | 稍后重试；权威查询核对 | 不用空页冒充无记录 |
| `ERR-INTERNAL` | `internal_error` | 未捕获异常 | 本次失败；副作用可能未知 | 上报；查询权威状态 | 不含栈/Secret |
| `ERR-BOOT` | `invalid_request`（Proposed） | 空库缺/非法 bootstrap | 回滚保持 `not_ready`；不接流量 | 修正配置重启 | 或以 `/readyz` 表达 |
| `ERR-SCHEMA` | `internal_error`（Proposed） | schema 版本不匹配/未知/完整性失败 | 拒绝启动，`not_ready` | 运维离线迁移；不并行双写 | 或以 `/readyz` 表达 |
| `ERR-PATH-UNSAFE` | `internal_error`（Proposed） | DB 路径 symlink 等不安全形态 | 拒绝启动 | 修正路径重启 | — |
| `ERR-INJECTION` | `invalid_request` | 注入类型/字段/范围非法 | 未写入；配置不变 | 修正注入项 | 归属 M006 |
| `ERR-CONFIRM` | `invalid_request` | 有费用/改状态操作缺二次确认 | 未执行；无副作用 | 补确认后重试 | — |

- **Data/Type ID、用途与来源**：

  `D-ERROR-ENVELOPE`；公共错误码含义由 `docs/20_system_design/llmtier-system-design.md` §8.8 决定，本文只引用其 `ERR-*` ID 与逐失败条件；机器 Error 目录 `interfaces/error-codes/` 未建立 → **Proposed**。

- **字段与约束**：

  接口逐失败条件只引用上表 `ERR-*`；同码异义、缺码或引用不存在码阻止本契约完成；不自行发明 wire 码。

- **跨字段与寿命**：

  错误响应请求级返回；`runtime_activation=false`，错误码机器核对由 `B-CONTRACT-01` 阻塞。

- **合法/拒绝实例**：

  见上表逐码“触发事实/结果与副作用/禁用边界”列。

- **验证**：

  拒绝 `stream=false` → 400 `unsupported_request`；拒绝未知 tier → 404 `model_not_found`。向量 `interfaces/vectors/v0.3/stateless-gateway-boundary-fixtures.json`；`VRC-INF-001`、`VRC-API-002`。

### 4.2 Blocker / 未决 catalog

| Blocker ID | 事实 | 阻塞范围 | 责任 / 关闭判据 |
|---|---|---|---|
| `B-CONTRACT-01` | `interfaces/error-codes/` 机器 Error 目录未建立 | 错误码机器核对（§4.1 Proposed 行） | LLMTier；建立目录并锚定 version/revision/hash |
| `B-CONTRACT-02` | `runtime_activation=false` | 生产启用 | Piko/Slinky 消费签署 + capture；见 §11 |
| `B-CONTRACT-03` | Provider 账号用量 refresh 依赖外部 API | `IF-ADM-PROVIDER-USAGE` POST 真实证据 | operator；真实 capture（不阻止设计候选） |

## 5. 接口设计（幂等、并发、事务与一致性）

> 本节为跨接口共同政策；逐接口适用条件与结果已回写各接口记录的“交互与生命周期”。分类同 §2：API（HTTP）与消息与数据流接口（SSE）适用；硬件/人机不适用。

- **API（HTTP）**：外部契约不承诺 custom idempotency/exactly-once。内部 admission/queue/concurrency 不暴露资源状态。管理 CRUD 须一致地校验引用并审计；PATCH 为原子局部更新，PATCH/DELETE 使用 ETag/`If-Match`，失败不得留下 partial write。实现并发控制不得扩展 consumer 协议。重复 DELETE 幂等；重复 POST 不保证去重。
- **消息与数据流接口（SSE）**：`IF-DP-RESPONSES` 单请求独立，`X-Request-ID` 只作关联、不承担 task/session/idempotency/recovery 语义；客户端断开结束本次调用并释放许可；不承诺可恢复 Invocation 或结果重放。
- **共同点**：任何请求在 provider dispatch 前必须先持久化 unknown Usage 义务；计量版本只追加并单调推进 head（§3.6）。

## 6. Pagination、filter、ordering 与 retention

Usage按from/to必填，可选model/request_id，按 `(recorded_at,request_id)` 稳定排序；首个页面固定有期限snapshot及每个request的具体record version，cursor绑定principal、当前授权和原filter且不跨filter复用。页间更正/插入只进入新snapshot；snapshot到期、权限缩小、签名或filter不符返回400 `invalid_request`。同一request只选择snapshot冻结版本，绝不重复相加。dispatch前必须已有持久unknown Usage义务；因此terminal后计量写失败或崩溃时，重启后仍能返回unknown而不是空页。store不可读返回typed 503。Admin列表同样冻结序列化view/ETag并逐页复核授权。模型列表不分页。Retention是LLMTier内部政策，未知不得伪造成零；不对消费者承诺旧M2-C窗口。

## 7. 身份、权限、Secret 与调用边界

`GET /v1/logs`按level/module/request ID过滤写入前已脱敏的运行事件，使用稳定快照与逐页授权；store不可读返回503。日志消息有长度上限，不得包含prompt、模型输出、reasoning、向量、credential、Secret或原始header。该接口只读，和管理动作Audit分离。

Bearer credential只用于授权，不形成Client/Source/SourceInstance DTO。Admin credential独立。Secret只写引用、view仅`has_secret`。不传Agent/Run/Project/IR/STD/Session。

Provider账号用量只在operator对`POST /v1/providers/{provider_id}/usage`提交`confirm_external_call=true`时触网；GET只返回最后持久快照。MiniMax使用Provider API Key或独立API Key reference调用官方Token Plan API，不接受console cookie；火山使用独立OpenAPI AK/SK调用`GetCodingPlanUsage`。响应只含窗口、用量/比例、reset、source/status/checked_at和脱敏错误，不回显credential。Provider profile同时承载本网关内部账号并发、最小请求间隔和RPM，不形成外部capacity/Seat产品。

## 8. 接口设计（版本、兼容性与迁移）

> 分类同 §2；逐接口版本结果回写各接口记录。本候选一次性替代`0.3-finalization-candidate.5`，旧custom endpoints/headers/schemas/fixtures成为历史，无runtime fallback或alias。legacy `/call`不属于current contract。

- **API（HTTP）**：consumer 面 `/v1/*` 与 admin 面随 `openapi`/manifest 显式版本变更；无运行时兼容协商 endpoint；破坏性变化由 LLMTier authority 决定，消费方按新固定基线迁移。
- **消息与数据流接口（SSE）**：固定支持该一条标准 Responses SSE 路径，不建立 non-stream fallback；新增完成状态不能假定旧消费者安全忽略。
- **兼容基线**：`interfaces/compatibility/compatibility-manifest-v0.3.json`；字段改名、枚举/错误变化、删除和替代对照旧基线（candidate.5）逐项记录，废弃 ID 不回收。

## 9. Positive/Negative fixture 与 validator

Current fixtures：`openai-surface-fixtures.json`、`usage-fixtures.json`、`admin-model-fixtures.json`、`stateless-gateway-boundary-fixtures.json`；Admin fixture同时覆盖脱敏日志页。Validator必须解析全部refs，执行SSE sequence/delta/done/terminal identity及refusal形状、Embedding float/base64表示与维数、Usage unknown/source/subset/单调版本、分页snapshot及崩溃顺序、Admin并发条件、LogPage/禁入内容和旧custom术语/path absence检查；不能用“文件可解析”冒充语义通过。向量基线 `interfaces/vectors/v0.3/*`（见 §1 hash 表）。

## 10. Requirement → Contract → Test traceability

CT-DP-001、CT-MODEL-001、CT-EMB-001、CT-USAGE-001、CT-ADMIN-001、CT-OPS-001、CT-BOUNDARY-001、CT-SCOPE-001映射见requirements traceability。

| 需求/Constraint | 规则/成员 ID | 设计 V | 承接方/backend | Case / 环境 | Run/状态/缺口 |
|---|---|---|---|---|---|
| CT-DP-001 | `IF-DP-RESPONSES`/`IF-MSG-SSE` | VRC-INF-001/002 | M001/M003 | `openai-surface-fixtures.json` | NOT_RUN |
| CT-MODEL-001 | `IF-DP-MODELS` | VRC-INF-001 | M003 | `admin-model-fixtures.json` | NOT_RUN |
| CT-EMB-001 | `IF-DP-EMBEDDINGS` | VRC-INF-001 | M003 | `openai-surface-fixtures.json` | NOT_RUN |
| CT-USAGE-001 | `IF-ADM-USAGE` | VRC-MGMT-006 | M003/M007 | `usage-fixtures.json` | NOT_RUN |
| CT-ADMIN-001 | `IF-ADM-PROVIDERS`/`-DEPLOYMENTS`/`-SERVICE-LEVELS` | VRC-MGMT-001/002 | M004 | `admin-model-fixtures.json` | NOT_RUN |
| CT-OPS-001 | `IF-ADM-PROBES`/`-PROVIDER-USAGE` | VRC-DIAG-004 | M004 | `admin-model-fixtures.json` | NOT_RUN |
| CT-BOUNDARY-001 | `D-ERROR-ENVELOPE`/§4.1 | VRC-API-002 | M001 | `stateless-gateway-boundary-fixtures.json` | NOT_RUN |
| CT-SCOPE-001 | §7/§8 旧术语/path absence | — | M001 | `stateless-gateway-boundary-fixtures.json` | NOT_RUN |

## 11. Activation Gate 与未决项

需要实现、provider capture、Piko对标准SSE事件子集的消费签署、Embedding consumer test、auth/TLS/operations、Admin UI test。streaming设计范围不再待决。设计可用≠实现完成≠运行许可；本轮 `runtime_activation=false`，`interfaces/error-codes/` 与真实 capture 见 §4.2 blocker。
