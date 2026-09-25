<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Cross-system Simplification Candidate

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-cross-system-finalization` |
| Document Version | `0.3.1-draft.6` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-16` |
| Last Modified Date | `2026-09-25` |
| Template ID | `contracts.specification` |
| Template Version | `0.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-cross-system-finalization.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. Contract scope 与 authority

Current candidate是`0.3-simplified-candidate.8`。OpenAPI和manifest是唯一current machine artifacts；旧candidate只作历史审计。

- **唯一字段级 authority**：`interfaces/openapi/llmtier.openapi.json`（version `0.3-simplified-candidate.8`，sha256 `b34428126390056e3eb7927ccb219e5185962a3c5483abb6d9f4fab7ed9a417a`）；本文是同一基线的阅读视图，记录跨系统定型决定与旧接口退役，不复制字段。
- **本文拥有**：跨系统（Piko/Slinky ↔ LLMTier）的操作边界、公共字段语义、旧接口退役与 A/B/C 收敛。
- **ID/错误**：沿用系统设计 §8/§9 的 `D-*`/`IF-*` 与 §8.8 的 `ERR-*`；`interfaces/error-codes/` 未建立 → 机器错误目录 **Proposed**。
- **runtime_activation=false**。

## 2. 接口设计（Operation / Message / Event Catalog）

> 按 STD `design-data-interface-format` 1.2.0 §3 按**接口形态分类**；分类适用性：2.1 软件接口 ✓（HTTP）｜2.2 消息与数据流接口 ✓（SSE）｜2.3 硬件与固件接口 ✗｜2.4 人机与维护接口 ✗（Admin UI 归管理控制文档）。

### 2.1 软件接口（适用时）

#### `POST /v1/responses`（跨系统 Responses）

```text
POST /v1/responses
  Authorization: Bearer <data-token>
  traceparent: string?          # 标准 trace context
  X-Request-ID: string          # response 回填；只作关联
  body: ResponsesRequest {model, input, stream:true, store:false, tools?, ...}
  -> 200 text/event-stream: ResponseStreamEvent
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-RESPONSES`；规格已定、Implemented；`openapi` candidate.8；`src/http_api/app.py` → `src/inference/responses.py`。
- **输入**：标准 Responses 请求（§3.1）；Bearer auth、标准 trace context 与 response `X-Request-ID`；`model` exact 逻辑等级名，LLMTier 不 alias/fallback。
- **成功输出**：标准 SSE（§3.1）；`store:false`，LLMTier 不形成 conversation。
- **错误与异常**：见 `llmtier-contract-specification` §4.1（`ERR-REQ-*`/`ERR-AUTH-*`/`ERR-MODEL-NOTFOUND`/`ERR-RATE-LIMIT`/`ERR-PROVIDER-*`）。
- **交互与生命周期**：每次调用完整输入；Piko 执行工具并在新请求提交 result；Request ID 不承担 task/session/recovery 语义。
- **实例与验证**：固定 Pi golden request；标准 SSE item identity/terminal。`openai-surface-fixtures.json`；`VRC-INF-001/002`。

#### `GET /v1/models` / `GET /v1/models/{model}`

```text
GET /v1/models         -> 200 ModelList {object, data:[Model]}
GET /v1/models/{model} -> 200 Model {id, availability, capabilities, ...}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-MODELS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/models.py`。
- **输入**：路径 `model` exact 名；Data Bearer。
- **成功输出**：`D-MODEL`（§3.2）；只发布 id、availability 及 responses/embeddings/tools/structured output/modalities/context/output limits；不暴露物理 provider/account。
- **错误与异常**：`ERR-AUTH-*`；未知 exact 名 → `ERR-MODEL-NOTFOUND`（404）。
- **交互与生命周期**：同步只读；compatibility 协商不是必需面。
- **实例与验证**：正常固定 tier；拒绝未知名。`admin-model-fixtures.json`；`VRC-INF-001`。

#### `GET/DELETE /v1/usage`

```text
GET    /v1/usage?from=&to=&model=&request_id= -> 200 UsagePage
DELETE /v1/usage?model=&deployment_id=        -> 200 object   # 仅 operator
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/inference/usage.py`。
- **输入**：过滤/分页参数；GET 按主体，DELETE 仅 admin。
- **成功输出**：`UsagePage`（§3.2）；同 request 更高 `record_version` 替换旧值，response 与 query 不得重复相加。
- **错误与异常**：`ERR-STORE`（503 typed，不用空页）；`ERR-CURSOR`（400）；非 admin DELETE → `ERR-AUTH-DENIED`。
- **交互与生命周期**：GET 稳定分页快照；dispatch 前持久 unknown Usage 义务。
- **实例与验证**：正常分页；拒绝过期 cursor。`usage-fixtures.json`；`VRC-MGMT-006`。

#### `POST /v1/embeddings`

```text
POST /v1/embeddings
  body: EmbeddingRequest {model, input, encoding_format?, dimensions?, user?}
  -> 200: EmbeddingResponse {object, data:[EmbeddingItem], model, usage}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-EMBEDDINGS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/embeddings.py`。
- **输入**：`EmbeddingRequest`（§3.4）；embedding tier 兼容性由 `embedding_space_id` 决定。
- **成功输出**：`EmbeddingResponse`；模型还发布稳定 space ID、维数、batch 和输入上限。
- **错误与异常**：`ERR-REQ-VALIDATION`/`ERR-MODEL-NOTFOUND`/`ERR-RATE-LIMIT`/`ERR-PROVIDER-*`/`ERR-STORE`。
- **交互与生命周期**：标准 POST 成功/标准错误；无 202 active、Invocation ID、custom replay、410 tombstone 或 Responses GET；Memory 负责自己的输入和索引幂等。
- **实例与验证**：float/base64、batch index/数量/有限数、空间稳定。`openai-surface-fixtures.json`；`VRC-INF-001`。

### 2.2 消息与数据流接口（适用时）

#### `Responses SSE 事件子集`

```text
stream: text/event-stream
  event: response.created | response.output_item.added | response.output_text.delta
       | response.refusal.delta | reasoning events | response.function_call_arguments.delta|done
       | response.output_item.done | response.completed | response.incomplete | response.failed | error
  data: ResponseStreamEvent (type/sequence_number)
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-MSG-SSE`；规格已定、Implemented；`openapi` `ResponseStreamEvent`；`src/http_api/sse.py`、`src/inference/responses.py`。
- **输入**：一次已受理 `POST /v1/responses`。
- **成功输出**：保留 item identity（`item.id`/`output_index`）；恰一个 completed/incomplete/failed/error 终点。
- **错误与异常**：流内 `error`/`response.failed`；不伪造完成。
- **交互与生命周期**：Piko 只消费该标准 SSE 路径，不建立 non-stream fallback。
- **实例与验证**：`openai-surface-fixtures.json`；`VRC-INF-002/005`。

### 2.3 硬件与固件接口（适用时）

不适用：纯软件，无连接器/总线/寄存器/FPGA 端口。

### 2.4 人机与维护接口（适用时）

不适用：Admin/观测页面归 `llmtier-management-control`，不在跨系统契约内。

## 3. 数据结构设计（Request、Response、Event 与数据对象）

> 按 STD `design-data-interface-format` 1.2.0 §2 按**数据性质**分类；wire 字段以 §1 `openapi` 为机器权威。类别适用性：3.1 公共基础类型与枚举 ✓｜3.2 业务与操作数据结构 ✓｜3.3 配置与规则数据结构 ✓｜3.4 通信报文结构 ✓（机器源继承）｜3.5 设备与 FPGA 表项 ✗｜3.6 运行状态数据结构 ✓｜3.7 数据库表结构 ✓（authority `util/migrations/*.sql`）。错误见 §4.1。

### 3.1 通信报文结构（Responses 与 tool loop 逐字段表）

| Data/Type ID | Field | Producer | Consumer/Meaning |
|---|---|---|---|
| `D-MSG-RESPONSE.model` | model | Piko | exact logical model ID；LLMTier不alias/fallback |
| `D-MSG-RESPONSE.input` | input | Piko | 本次调用完整上下文；不由LLMTier补历史 |
| `D-MSG-RESPONSE.stream/store` | stream/store | Piko | 固定Pi首阶段固定`true/false`；只走标准SSE |
| `D-MSG-RESPONSE.tools` | tools/tool_choice | Piko | 可调用工具描述；LLMTier不执行 |
| `D-MSG-RESPONSE.history` | assistant/reasoning/function历史 | Piko | 保留标准item ID与opaque reasoning；LLMTier不形成conversation |
| `D-MSG-RESPONSE.output` | output function_call | Model/LLMTier | 保留item ID/call ID；Piko执行并在新请求提交result |
| `D-MSG-SSE.terminal` | SSE terminal | LLMTier | item identity一致，恰有一个completed/incomplete/failed/error终点 |
| `D-MSG-RESPONSE.usage` | usage | LLMTier | 标准token/details；缺失为Unknown，不把成功结果改失败 |

- **定义、Data/Type ID 与唯一来源**：OpenAI-compatible Responses 请求/响应/流；机器源 `openapi` `ResponsesRequest`/`ResponsesResponse`/`ResponseStreamEvent`。
- **字段**：见上表；完整字段见 `llmtier-contract-specification` §3.4。
- **约束 / 不变量**：`stream:true`/`store:false`；每请求恰一 terminal；item identity 稳定。
- **状态 · 所有权 · 寿命**：wire 载荷请求级；LLMTier 无 conversation 持久。
- **合法与拒绝实例**：合法标准请求→SSE+Usage；拒绝 `stream=false`→`ERR-REQ-UNSUPPORTED`。
- **验证**：`openai-surface-fixtures.json`；`VRC-INF-001/002`。

#### `EmbeddingRequest` / `EmbeddingResponse`（`D-MSG-EMBEDDING`）

- **定义、Data/Type ID 与唯一来源**：标准 Embeddings 请求/响应；机器源 `openapi`。
- **字段**：`{model,input(string|string[]),encoding_format?("float"|"base64"),dimensions?,user?}` → `{object:"list",data:[{object,index,embedding}],model,usage}`。
- **约束 / 不变量**：base64 为连续 little-endian IEEE-754 float32；标准 POST 成功/标准错误。
- **状态 · 所有权 · 寿命**：请求级；Memory 负责自己的输入和索引幂等。
- **合法与拒绝实例**：合法 float/base64；拒绝不兼容维数/数量/索引。
- **验证**：`openai-surface-fixtures.json`；`VRC-INF-001`。

### 3.2 业务与操作数据结构

#### `UsageRecord` / `UsagePage`（`D-USAGE-RECORD`）

- **定义、Data/Type ID 与唯一来源**：追加式用量事实版本与分页；机器源 `openapi` `UsageRecord`/`UsagePage`。
- **字段**：见 `llmtier-contract-specification` §3.2；含 `record_version`/`is_final`/`measurement_status`/`source`/token 字段与 `snapshot_id`/`snapshot_at`。
- **约束 / 不变量**：同 request 版本不累计；`unknown ⇒ token 全 null`；`has_more=false ⇒ next_cursor=null`。
- **状态 · 所有权 · 寿命**：账本追加式、按 principal 隔离。
- **合法与拒绝实例**：合法更高版本替换；边界 unknown 不补零。
- **验证**：`usage-fixtures.json`；`VRC-INF-004`、`VRC-MGMT-006`。

#### `Model` / `ModelList` / `ModelCapabilities`（`D-MODEL`/`D-CAPABILITY`）

- **定义、Data/Type ID 与唯一来源**：Registry 与 Models 字段；机器源 `openapi` `Model`/`ModelCapabilities`。
- **字段**：`Model{id,availability,capabilities}`；`ModelCapabilities` 12 键（见 `llmtier-contract-specification` §3.3）；Embedding model 还发布稳定 space ID、维数、batch 和输入上限。
- **约束 / 不变量**：不兼容空间必须新 model ID。
- **状态 · 所有权 · 寿命**：只读投影，随 Registry 变更。
- **合法与拒绝实例**：合法 exact model；拒绝未知名。
- **验证**：`admin-model-fixtures.json`；`VRC-INF-001`。

#### `ProviderView` / `DeploymentView` / `ServiceLevelView`

- **定义、Data/Type ID 与唯一来源**：管理面视图；机器源 `openapi`。
- **字段**：见 `llmtier-contract-specification` §3.2；物理 provider/account 不暴露。
- **约束 / 不变量**：`secret_ref` 只写不回显；capabilities 为成员交集。
- **状态 · 所有权 · 寿命**：SQLite 持久，带 `version`。
- **合法与拒绝实例**：合法引用；拒绝重名/未知引用。
- **验证**：`admin-model-fixtures.json`；`VRC-MGMT-001/002`。

### 3.3 配置与规则数据结构

- `ModelCapabilities`、`ProviderUsageProfile*`、`TrustedLanPolicy`/`AuthPolicy` 见 `llmtier-contract-specification` §3.3。
- **公共字段规则**：Bearer auth、标准 trace context 和 response `X-Request-ID`；没有 SourceInstance、custom deadline/idempotency/invocation headers；Request ID 不承担 task/session/recovery 语义。

### 3.5 设备与 FPGA 表项结构（适用时）

不适用：纯软件，无设备/RTL 表项。

### 3.6 运行状态数据结构

`D-USAGE-OBLIGATION`/`D-USAGE-HEAD`/`D-PROVIDER-BINDING`、`HealthView`/`ReadinessView` 见 `llmtier-contract-specification` §3.6；Usage 消费语义见 §5。

### 3.7 数据库表结构

Authority `util/migrations/*.sql`；公共可观察表见 `llmtier-contract-specification` §3.7。

## 4. 数据结构设计（状态、错误和 blocker catalog）

### 4.1 错误码与错误结构

标准错误：`ERR-REQ-VALIDATION`、`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`、`ERR-MODEL-NOTFOUND`、`ERR-RATE-LIMIT`、`ERR-PROVIDER-FAIL`/`ERR-PROVIDER-UNAVAIL`、`ERR-STORE`、`ERR-CONFLICT`（含义与映射见系统设计 §8.8 与 `llmtier-contract-specification` §4.1）。不存在 InvocationStatus、Seat 状态、RecoveryDisposition 或 compatibility status。`interfaces/error-codes/` 未建立 → **Proposed**。

### 4.2 Blocker / 剩余项 catalog

见 §11 A/B/C 分栏与 `llmtier-contract-specification` §4.2（`B-CONTRACT-01/02/03`）。

## 5. 接口设计（幂等、并发、事务与一致性）

> 分类同 §2（软件接口/消息与数据流接口适用）；Usage 与 Slinky/Piko 消费语义如下，逐接口结果回写 §2。

- Piko 主要聚合 response usage 形成任务 usage；必要时按 `request_id` 查询 `/v1/usage`。同 request 的更高 record version 替换旧值，response 和 query 不得重复相加；store 失败为 typed `ERR-STORE` 503。Slinky 可为 Memory/运维读取相同 token 事实。没有 Cost、capacity 或执行状态。
- 外部契约不承诺 custom idempotency/exactly-once；内部 admission/queue/concurrency 不暴露资源状态。
- 管理 CRUD（若适用）一致校验引用并审计；PATCH 原子局部更新；失败不得留下 partial write。

## 6. Pagination、filter、ordering 与 retention

Usage 按 `(recorded_at,request_id)` 稳定排序；`request_id` 选择 snapshot 冻结版本、绝不重复相加；retention 为 LLMTier 内部政策。详见 `llmtier-contract-specification` §6。

## 7. 身份、权限、Secret 与调用边界

Bearer auth、标准 trace context 和 response `X-Request-ID`；没有 SourceInstance、custom deadline/idempotency/invocation headers。Bearer credential 只用于授权，不形成 Client/Source/SourceInstance DTO；Admin credential 独立；Secret 只写引用、view 仅 `has_secret`。不传 Agent/Run/Project/IR/STD/Session。

## 8. 接口设计（版本、兼容性与迁移）

> 分类同 §2；逐接口结果回写 §2。

旧接口一次性退役版本：退出 current authority：SourceInstance；capacity/Seat/claim；custom Idempotency/Invocation/recovery/deadline；cross-system release；compatibility endpoint；clients/sources/entitlements/recovery admin；Cost；Topic/SID/RID 等业务字段。没有 deprecated acceptance 或 fallback。兼容基线 `interfaces/compatibility/compatibility-manifest-v0.3.json`。

## 9. Positive/Negative fixture 与 validator

静态 validator 检查 refs、fixtures 和旧 path/schema absence。提交后记录 commit/hash；当前文档不宣称实现或 activation。向量 `interfaces/vectors/v0.3/*`。

## 10. Requirement → Contract → Test traceability

见 `llmtier-contract-specification` §10。

## 11. Activation Gate 与未决项

- **A 跨系统**：标准 Responses SSE 沿用已接受 candidate.5 语义；candidate.6 只增加 LLMTier operator 主页与只读脱敏日志面，不改变 Piko/Slinky 模型消费字段。
- **B LLMTier 内部**：provider adapters、embedding deployment、queue/concurrency、Usage store、Admin UI、auth/TLS/runbook。
- **C 联调**：SDK capture、真实 token、429/5xx、embedding 维数、health/restart、UI 安全。

`runtime_activation=false`；以上 A/B/C 与 `interfaces/error-codes/` 建立是 activation gate。
