<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier API Reference

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-reference` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-25` |
| Template ID | `contracts.specification` |
| Template Version | `0.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-api-reference.md` |
| Supersedes | none |
| Reviewer | 待定 |
| Approver | 待定 |
| Approval Date | 待定 |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Contract scope 与 authority

**API 版本**: `0.3-simplified-candidate.8`

**机器契约权威源**: `interfaces/openapi/llmtier.openapi.json`（version `0.3-simplified-candidate.8`，sha256 `b34428126390056e3eb7927ccb219e5185962a3c5483abb6d9f4fab7ed9a417a`）；字段级 authority。本文是同一固定基线的**阅读视图**，记录用途、顺序、失败与合法下一步；冲突以机器源为准。

LLMTier 提供 OpenAI-compatible HTTP API，供局域网上的 consumer（如 Piko、Slinky）调用。`runtime_activation=false`，本候选不授权 runtime；字段/接口 ID 沿用系统设计 §8/§9 的 `D-*`/`IF-*`，错误码引用系统设计 §8.8 的 `ERR-*`。

### 1.1 接口分类

| 分类 | 说明 | Auth |
|------|------|------|
| **Data Plane** | `/v1/responses`, `/v1/embeddings`, `/v1/models` | Data Bearer Token |
| **Observation** | `/healthz`, `/readyz`, `/v1/usage` | Data Bearer Token |
| **Management** | `/v1/*` | Admin Bearer Token |

### 1.2 服务器信息

```
Base URL: http://<host>:<port>
示例: http://192.168.1.9:8765
```

生产环境应使用 HTTPS。

## 2. 接口设计（Operation / Message / Event Catalog）

> 按 STD `design-data-interface-format` 1.2.0 §3：按**接口形态分类**逐接口完整记录；标题为真实路由，标题下给完整接口声明与六项。分类适用性：2.1 API ✓｜2.2 消息与数据流接口 ✓（SSE）｜2.3 硬件与固件接口 ✗（纯软件）｜2.4 人机与维护接口 ✗（Admin Web UI 归管理控制文档）。完整逐字段错误与数据定义见 `llmtier-contract-specification` §2/§4。

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

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DP-RESPONSES`；规格已定、Implemented；唯一契约=`openapi` candidate.8；`src/http_api/app.py` → `src/inference/responses.py`。
- **输入与前提**：`ResponsesRequest`（§3.4）——`model` exact 逻辑等级名、`input`、`stream:true`、`store:false`、可选工具/采样/推理字段；Data Bearer 授权；校验顺序 鉴权→JSON/schema→形态→模型→准入。
- **成功输出与保证**：标准 SSE 流（§2.2.1）；每请求恰一 terminal，`usage` 仅 terminal。
- **错误与合法下一步**：`ERR-REQ-VALIDATION`/`ERR-REQ-FIELD`/`ERR-REQ-JSON`/`ERR-REQ-UNSUPPORTED`（400）、`ERR-REQ-TOO-LARGE`（413）、`ERR-AUTH-*`（401/403/503）、`ERR-MODEL-NOTFOUND`（404）、`ERR-RATE-LIMIT`（429）、`ERR-PROVIDER-*`/`ERR-MODEL-UNAVAIL`（502/503）。
- **交互与生命周期**：同步建连后流式；单请求独立；断开=结果未知并释放许可；不承诺 exactly-once。
- **实现与验证**：正常 exact tier→200 SSE；拒绝 `stream=false`→400。`openai-surface-fixtures.json`；`VRC-INF-001/002`。

#### `POST /v1/embeddings`

```text
POST /v1/embeddings
  body: EmbeddingRequest {model, input, encoding_format?, dimensions?, user?}
  -> 200: EmbeddingResponse {object, data:[EmbeddingItem], model, usage}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DP-EMBEDDINGS`；规格已定、Implemented；`openapi` candidate.8；`src/http_api/app.py` → `src/inference/embeddings.py`。
- **输入与前提**：`EmbeddingRequest`（§3.4）——`model` exact embedding tier、`input` string/array、`encoding_format` 默认 `float`、`dimensions`、`user`；Data Bearer。
- **成功输出与保证**：`EmbeddingResponse` 向量 + `usage`；base64 为连续 little-endian float32。
- **错误与合法下一步**：`ERR-REQ-VALIDATION`/`ERR-REQ-TOO-LARGE`（400/413）、`ERR-MODEL-NOTFOUND`（404）、`ERR-RATE-LIMIT`（429）、`ERR-PROVIDER-*`（502/503）、`ERR-STORE`（503）。
- **交互与生命周期**：同步；同一逻辑 model 只绑定同一 `embedding_space_id`；非兼容变更须新 model ID。
- **实现与验证**：正常 float/base64；拒绝不兼容维数。`openai-surface-fixtures.json`；`VRC-INF-001`。

#### `GET /v1/models` / `GET /v1/models/{model}`

```text
GET /v1/models         -> 200 ModelList {object, data:[Model]}
GET /v1/models/{model} -> 200 Model {id, object, created, owned_by, availability, capabilities}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-DP-MODELS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/models.py`。
- **输入与前提**：路径 `model` exact-case 名；Data Bearer；无 body。
- **成功输出与保证**：`Model`/`ModelList`（§3.2）；不暴露物理账号。
- **错误与合法下一步**：`ERR-AUTH-*`（401/403）；未知 exact 名→`ERR-MODEL-NOTFOUND`（404）。
- **交互与生命周期**：同步只读、幂等；模型列表不分页。
- **实现与验证**：正常固定 tier；拒绝未知名。`admin-model-fixtures.json`；`VRC-INF-001`。

#### `GET /healthz` / `GET /readyz`

```text
GET /healthz -> 200 HealthView {status, version}          # 无凭据
GET /readyz  -> 200 ReadinessView {status, models:[...]}  # schema+bootstrap+固定等级
             -> 503 (not_ready)
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-HEALTH`；规格已定、Implemented；`openapi` candidate.8；`src/http_api/health.py`。
- **输入与前提**：无参数、无凭据。
- **成功输出与保证**：`HealthView`/`ReadinessView`（§3.6）。
- **错误与合法下一步**：bootstrap/schema/path 失败→503 `not_ready`（`ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`）。
- **交互与生命周期**：同步只读、无副作用。
- **实现与验证**：正常 READY；边界 bootstrap 失败 not_ready。`VRC-UTIL-001/002`。

#### `GET/POST /v1/providers`；`GET/PATCH/DELETE /v1/providers/{provider_id}`

```text
GET    /v1/providers?cursor=&limit=            -> 200 ProviderPage {data:[ProviderView], page}
POST   /v1/providers {ProviderWrite}           -> 201 ProviderView (ETag)
GET    /v1/providers/{provider_id}             -> 200 ProviderView (ETag)
PATCH  /v1/providers/{provider_id} {ProviderPatch} If-Match -> 200 ProviderView (ETag)
DELETE /v1/providers/{provider_id} If-Match    -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-PROVIDERS`；规格已定、Implemented；`openapi` candidate.8；`src/management/registry.py`。
- **输入与前提**：`ProviderWrite`/`ProviderPatch`（§3.2）；`provider_id`；PATCH/DELETE 必带 `If-Match`；Admin Bearer。
- **成功输出与保证**：`ProviderView`（§3.2）+ 强 ETag；`secret_ref` 只写不回显；同事务审计。
- **错误与合法下一步**：`ERR-AUTH-*`；重名→`ERR-CONFLICT`（409）；被引用删除→`ERR-INUSE`（409）；`If-Match` 过期→`ERR-STALE`（412）；未知 ID→`ERR-NOTFOUND`（404）；`ERR-STORE`（503）。
- **交互与生命周期**：同步；partial PATCH；DELETE 幂等；ETag 乐观并发。
- **实现与验证**：正常 201+ETag；拒绝缺 `If-Match` 的 PATCH。`admin-model-fixtures.json`；`VRC-MGMT-001/002`。

#### `GET/POST /v1/providers/{provider_id}/usage`

```text
GET  /v1/providers/{provider_id}/usage                               -> 200 ProviderAccountUsageSnapshot
POST /v1/providers/{provider_id}/usage {confirm_external_call:true}  -> 200 ProviderAccountUsageSnapshot
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-PROVIDER-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/management/account_usage.py`。
- **输入与前提**：`provider_id`；POST 仅 `confirm_external_call`；Admin Bearer。
- **成功输出与保证**：`ProviderAccountUsageSnapshot`（§3.2）；POST 显式刷新并替换；不落 Secret。
- **错误与合法下一步**：缺确认→`ERR-CONFIRM`（400）；未知 provider→`ERR-NOTFOUND`（404）；上游失败记入快照 `status`。
- **交互与生命周期**：同步；GET 只读；POST 显式触网不自动轮询。
- **实现与验证**：正常带确认刷新；拒绝缺确认。`VRC-DIAG-004`。

#### `GET/POST /v1/deployments`；`GET/PATCH/DELETE /v1/deployments/{deployment_id}`

```text
GET    /v1/deployments?cursor=&limit=              -> 200 DeploymentPage {data:[DeploymentView], page}
POST   /v1/deployments {DeploymentWrite}           -> 201 DeploymentView (ETag)
GET    /v1/deployments/{deployment_id}             -> 200 DeploymentView (ETag)
PATCH  /v1/deployments/{deployment_id} {DeploymentPatch} If-Match -> 200 DeploymentView (ETag)
DELETE /v1/deployments/{deployment_id} If-Match    -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-DEPLOYMENTS`；规格已定、Implemented；`openapi` candidate.8；`src/management/registry.py`。
- **输入与前提**：`DeploymentWrite`/`DeploymentPatch`（§3.2）；`If-Match`；Admin Bearer。
- **成功输出与保证**：`DeploymentView`（§3.2）+ ETag；同事务审计；Pause/Resume 经 `enabled`。
- **错误与合法下一步**：未知 `provider_id`→`ERR-REQ-VALIDATION`（400）；重名→`ERR-CONFLICT`（409）；被 tier 引用→`ERR-INUSE`（409）；`ERR-STALE`（412）。
- **交互与生命周期**：同步；partial PATCH；ETag。
- **实现与验证**：正常引用已存在 provider；拒绝未知。`VRC-MGMT-001/002`。

#### `GET/POST /v1/service-levels`；`GET/PATCH/DELETE /v1/service-levels/{service_level_id}`

```text
GET    /v1/service-levels?cursor=&limit=               -> 200 ServiceLevelPage {data:[ServiceLevelView], page}
POST   /v1/service-levels {ServiceLevelWrite}          -> 201 ServiceLevelView (ETag)
GET    /v1/service-levels/{service_level_id}           -> 200 ServiceLevelView (ETag)
PATCH  /v1/service-levels/{service_level_id} {ServiceLevelPatch} If-Match -> 200 ServiceLevelView (ETag)
DELETE /v1/service-levels/{service_level_id} If-Match  -> 204
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-SERVICE-LEVELS`；规格已定、Implemented；`openapi` candidate.8；`src/management/registry.py`。
- **输入与前提**：`ServiceLevelWrite`/`ServiceLevelPatch`（§3.2）；`If-Match`；Admin Bearer。
- **成功输出与保证**：`ServiceLevelView`（§3.2）`capabilities` 为成员交集；同事务审计。
- **错误与合法下一步**：非固定 tier/非法交集→`ERR-REQ-VALIDATION`（400）；`ERR-CONFLICT`（409）；被引用→`ERR-INUSE`（409）；`ERR-STALE`（412）。
- **交互与生命周期**：同步；partial PATCH；成员顺序稳定。
- **实现与验证**：正常绑定有序成员；拒绝非固定 tier。`VRC-MGMT-001/002`。

#### `POST /v1/probes`

```text
POST /v1/probes {deployment_id, confirm_external_call:true} -> 200 ProbeResult
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-PROBES`；规格已定、Implemented；`openapi` candidate.8；`src/management/admin.py`。
- **输入与前提**：`ProbeRequest`；Admin Bearer + 二次确认。
- **成功输出与保证**：`ProbeResult`（§3.2）；可能产生费用。
- **错误与合法下一步**：缺确认→`ERR-CONFIRM`（400）；未知 deployment→`ERR-NOTFOUND`（404）；上游失败→`ERR-PROVIDER-*`（502）。
- **交互与生命周期**：同步显式触发，不自动轮询。
- **实现与验证**：正常带确认；拒绝缺确认。`VRC-DIAG-004`。

#### `GET/DELETE /v1/usage`

```text
GET    /v1/usage?cursor=&limit=&from=&to=&model=&request_id= -> 200 UsagePage
DELETE /v1/usage?model=&deployment_id=                        -> 200 object   # 仅 operator
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/inference/usage.py`。
- **输入与前提**：GET `from`/`to` 必填+可选过滤；DELETE 过滤参数且仅 `admin`；Data/Admin Bearer。
- **成功输出与保证**：`UsagePage`（§3.2，unknown 不填零）；DELETE 清空结果。
- **错误与合法下一步**：非 admin DELETE→`ERR-AUTH-DENIED`；`ERR-CURSOR`（400）；`ERR-STORE`（503 不空页）。
- **交互与生命周期**：GET 稳定快照（cursor 绑定 principal/授权/filter）；同 request 版本不累计。
- **实现与验证**：正常分页；拒绝过期 cursor/非 admin。`usage-fixtures.json`；`VRC-MGMT-006`。

#### `GET /v1/runtime` / `GET /v1/stats` / `GET /v1/audit` / `GET /v1/logs`

```text
GET /v1/runtime                            -> 200 object                    # 并发/队列快照
GET /v1/stats?from=&to=&group_by=tier      -> 200 object
GET /v1/audit?limit=                       -> 200 AuditPage {data:[AuditEvent], page}
GET /v1/logs?limit=&level=&module=&from=&to= -> 200 LogPage {data:[LogEntry], page}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-ADM-RUNTIME`、`IF-ADM-STATS`、`IF-ADM-AUDIT`、`IF-ADM-LOGS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/routing.py`、`src/management/admin.py`、`src/management/audit.py`、`src/log/logs.py`。
- **输入与前提**：各查询过滤/时间窗参数；Admin Bearer（`/v1/runtime` 等）。
- **成功输出与保证**：瞬时快照 / 聚合 / `AuditEvent` / `LogEntry`（均脱敏，§3.2）。
- **错误与合法下一步**：缺 `from`/`to`→`ERR-REQ-VALIDATION`（400）；`ERR-STORE`（503，不返回空页）。
- **交互与生命周期**：同步只读；日志 7 天保留；稳定快照与逐页授权。
- **实现与验证**：正常过滤；拒绝缺时间窗。`admin-model-fixtures.json`；`VRC-LOG-001`、`VRC-MGMT-006`。

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

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MSG-SSE`；规格已定、Implemented；`openapi` `ResponseStreamEvent`；`src/http_api/sse.py`、`src/inference/responses.py`。
- **输入与前提**：一次已受理的 `POST /v1/responses`；`X-Request-ID` 只作关联。
- **成功输出与保证**：标准 SSE 事件（§3.4）；每 output item 稳定 `id`/`output_index`；恰一 terminal。
- **错误与合法下一步**：流内 `error`/`response.failed`；不伪造完成；断开=结果未知。
- **交互与生命周期**：异步流；`sequence_number` 稳定顺序；`store:false` 不保留 conversation。
- **实现与验证**：正常以 terminal 结束；边界上游失败。`openai-surface-fixtures.json`；`VRC-INF-002/005`。

### 2.3 硬件与固件接口（适用时）

不适用：LLMTier 为纯软件，无连接器/总线/寄存器/FPGA 端口（tailoring `LT-TL-003`）。

### 2.4 人机与维护接口（适用时）

不适用：本文不定义 UI/CLI；中文 Admin Web UI 的同源 Admin API 调用见 `llmtier-management-control`。

## 3. 数据结构设计（Request、Response、Event 与数据对象）

> 按 STD `design-data-interface-format` 1.2.0 §2 按**数据性质**分类；wire 字段以 §1 `openapi` 为机器权威，本节只给阅读视图。类别适用性见 `llmtier-contract-specification` §3；本条保留原 Data Objects 示例。

### 3.1 公共基础类型与枚举

见 `llmtier-contract-specification` §3.1（`ErrorType`/`ErrorCode`、`ResponseStatus`/`availability`/`measurement_status`/`source`、`TierId`/`encoding_format`）；ID 与机器源相同，不重复定义。

### 3.2 业务与操作数据结构

`ProviderView`/`ProviderWrite`/`ProviderPatch`、`DeploymentView`/`Write`/`Patch`、`ServiceLevelView`/`Write`/`Patch`、`UsageRecord`/`UsagePage`、`ProviderAccountUsageSnapshot`、`ProbeResult`、`AuditEvent`/`AuditPage`、`LogEntry`/`LogPage` 的字段、约束、所有权与验证见 `llmtier-contract-specification` §3.2；本节仅给公开 JSON 示例。

### 3.3 配置与规则数据结构

`ModelCapabilities`（12 键）、`ProviderUsageProfileWrite`/`View`、`TrustedLanPolicy`/`AuthPolicy` 见 `llmtier-contract-specification` §3.3。

### 3.4 通信报文结构

**3.4.1 `Model`（通信报文结构，`D-MODEL`）**

```text
Model {
  id: string, object: "model", created: int, owned_by: "llmtier",
  availability: string∈{available,degraded,unavailable},
  capabilities: ModelCapabilities
}
```

- **Data/Type ID、用途与来源**：

  `D-MODEL`；逻辑模型目录条目的 wire 报文；机器源 `openapi` `Model`；字段全集见 `llmtier-contract-specification` §3.4。

- **字段与约束**：

  `id` 为 exact-case 逻辑等级名；`capabilities` 为 12 键能力（§3.3）；不暴露物理账号/provider。

- **跨字段与寿命**：

  只读投影，随 Registry 变更；请求级返回。

- **合法/拒绝实例**：

  合法为下方 `Model` JSON；拒绝未知 exact 名 → `ERR-MODEL-NOTFOUND`（404）。

- **验证**：

  `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-INF-001`。

```json
{
  "id": "Worker",
  "object": "model",
  "created": 1234567890,
  "owned_by": "llmtier",
  "availability": "available",
  "capabilities": {"responses": true, "embeddings": false, "tools": false, "structured_outputs": false,
    "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000,
    "max_output_tokens": 16384, "embedding_space_id": null, "embedding_dimensions": null,
    "embedding_max_batch_inputs": null, "embedding_max_input_tokens": null}
}
```

**3.4.2 `Response` (SSE) 与 `ResponseStreamEvent`（通信报文结构，`D-MSG-RESPONSE`/`D-MSG-SSE`）**

```text
Response { id, object:"response", status, model, output[], usage:TokenUsage?, error:ErrorDetail? }
ResponseStreamEvent = SSE 子集（§2.2.1），每事件带 type/sequence_number
```

- **Data/Type ID、用途与来源**：

  `D-MSG-RESPONSE`/`D-MSG-SSE`；OpenAI-compatible Responses 响应与流事件；机器源 `openapi` `ResponsesResponse`/`ResponseStreamEvent`。

- **字段与约束**：

  `status ∈ {completed,failed,incomplete}`；`output[]` 保留 item identity；`usage` 仅 terminal 给出；每请求恰一 terminal。

- **跨字段与寿命**：

  wire 载荷请求级；`store:false` 不形成 conversation，无 custom recovery。

- **合法/拒绝实例**：

  合法为下方完整 `Response` JSON；拒绝 `stream=false` → `ERR-REQ-UNSUPPORTED`。

- **验证**：

  `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-002/005`。

```json
{
  "id": "resp_xxx", "object": "response", "status": "completed", "model": "Worker",
  "output": [{"type": "message", "id": "msg_xxx", "role": "assistant", "status": "completed",
    "content": [{"type": "output_text", "text": "Hello", "annotations": []}]}],
  "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
  "error": null
}
```

**3.4.3 `Embedding`（通信报文结构，`D-MSG-EMBEDDING`）**

```text
EmbeddingResponse { object:"list", data:[EmbeddingItem], model, usage:EmbeddingUsage? }
EmbeddingItem { object:"embedding", embedding: number[]|base64, index: int>=0 }
```

- **Data/Type ID、用途与来源**：

  `D-MSG-EMBEDDING`；标准向量化响应；机器源 `openapi` `EmbeddingResponse`。

- **字段与约束**：

  `encoding_format=base64` 内容为连续 little-endian IEEE-754 float32；维数须在模型支持集合内；同一逻辑 model 保持同一 `embedding_space_id`。

- **跨字段与寿命**：

  请求级 wire 载荷；向量输出存储权限由消费方管理。

- **合法/拒绝实例**：

  合法为下方 JSON；拒绝不兼容维数/数量/索引。

- **验证**：

  `interfaces/vectors/v0.3/openai-surface-fixtures.json`；`VRC-INF-001`。

```json
{
  "object": "list",
  "data": [{"object": "embedding", "embedding": [0.123, -0.456], "index": 0}],
  "model": "Embedding-v1",
  "usage": {"prompt_tokens": 5, "total_tokens": 5}
}
```

**3.4.4 `ErrorEnvelope`（通信报文结构，`D-ERROR-ENVELOPE`，系统拥有含义）**

```text
ErrorEnvelope { error: { message: string, type: ErrorType, code: ErrorCode, param: string? } }
```

- **Data/Type ID、用途与来源**：

  `D-ERROR-ENVELOPE`；统一错误载荷；机器源 `openapi` `ErrorEnvelope`/`ErrorDetail`；含义见系统设计 §8.8。

- **字段与约束**：

  4 字段全必填，`param` 可 null；不含 Secret/凭据/完整正文；429 可带 `Retry-After`。

- **跨字段与寿命**：

  请求级返回。

- **合法/拒绝实例**：

  合法为下方 JSON；拒绝未知端点 → `ERR-NOTFOUND`。

- **验证**：

  `interfaces/vectors/v0.3/stateless-gateway-boundary-fixtures.json`；`VRC-API-*`。

```json
{"error": {"message": "Human-readable error message", "type": "invalid_request_error",
  "code": "invalid_request", "param": null}}
```

### 3.5 设备与 FPGA 表项结构（适用时）

不适用：纯软件，无设备/RTL 表项。

### 3.6 运行状态数据结构

**3.6.1 `Provider` / `Deployment` / `Service Level`（运行状态数据结构）**

```text
Provider { id, name, kind∈{local,cloud}, endpoint, has_secret, enabled, usage, request_usage, version>=1 }
Deployment { id, name, provider_id, backend_model, capabilities, enabled, health, version>=1 }
ServiceLevel { id, deployment_ids[>=1], enabled, capabilities, version>=1 }
```

- **Data/Type ID、用途与来源**：

  `D-PROVIDER`/`D-DEPLOYMENT`/`D-SERVICE-LEVEL`；配置与运行视图示例；机器源 `openapi`。

- **字段与约束**：

  `has_secret` 只读布尔，不回显 `secret_ref`；`health ∈ {unknown,healthy,degraded,unhealthy}`；`capabilities` 为成员交集；tier `id` exact-case。

- **跨字段与寿命**：

  SQLite 持久，带 `version` 乐观并发；operator 拥有。

- **合法/拒绝实例**：

  合法为下方三例；拒绝未知 `provider_id` → `ERR-REQ-VALIDATION`。

- **验证**：

  `interfaces/vectors/v0.3/admin-model-fixtures.json`；`VRC-MGMT-001/002`。

```json
{
  "id": "provider_xxx", "name": "My Provider", "kind": "local",
  "endpoint": "http://192.168.1.8:9000/v1", "has_secret": true, "enabled": true,
  "usage": {}, "request_usage": {"calls": 0, "input_tokens": null, "output_tokens": null, "total_tokens": null},
  "version": 1
}
```

```json
{
  "id": "deployment_xxx", "name": "My Deployment", "provider_id": "provider_xxx",
  "backend_model": "gemma-4-12b-it",
  "capabilities": {"responses": true, "embeddings": false, "tools": false, "structured_outputs": false,
    "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000,
    "max_output_tokens": 16384, "embedding_space_id": null, "embedding_dimensions": null,
    "embedding_max_batch_inputs": null, "embedding_max_input_tokens": null},
  "enabled": true, "health": "healthy", "version": 1
}
```

```json
{"id": "Worker", "deployment_ids": ["deployment_xxx"], "enabled": true, "capabilities": {}, "version": 1}
```

`HealthView`/`ReadinessView` 的应用见 §2.1。

### 3.7 数据库表结构

Authority = `util/migrations/*.sql`；公共可观察表见 `llmtier-contract-specification` §3.7。

## 4. 数据结构设计（状态、错误和 blocker catalog）

### 4.1 错误码与错误结构

机器权威 `openapi` `ErrorDetail`；公共含义与 `ERR-*` ID 见系统设计 §8.8 与 `llmtier-contract-specification` §4.1；`interfaces/error-codes/` 未建立 → **Proposed**。HTTP 状态与 wire `code` 对照（原 Error Responses 表）：

| HTTP Status | Wire `code`（`openapi`） | 系统 Error ID（§8.8） | 说明 |
|-------------|----------------------|----------------------|------|
| `400` | `invalid_request` | `ERR-REQ-VALIDATION`/`ERR-REQ-FIELD`/`ERR-REQ-JSON`/`ERR-REQ-UNSUPPORTED` | 请求参数/形态错误 |
| `401` | `authentication_failed` | `ERR-AUTH-REQUIRED`/`ERR-AUTH-NOCFG` | 认证失败 |
| `403` | `permission_denied` | `ERR-AUTH-DENIED` | 权限不足 |
| `404` | `resource_not_found` | `ERR-NOTFOUND` | 资源不存在 |
| `404` | `model_not_found` | `ERR-MODEL-NOTFOUND` | 逻辑等级不存在 |
| `409` | `invalid_request`（Proposed） | `ERR-CONFLICT`/`ERR-INUSE` | 冲突/被引用 |
| `412` | `version_conflict` | `ERR-STALE` | ETag 版本不匹配 |
| `413` | `invalid_request`（Proposed） | `ERR-REQ-TOO-LARGE` | body 过大 |
| `429` | `rate_limit_exceeded` | `ERR-RATE-LIMIT` | 请求过于频繁（可带 `Retry-After`） |
| `502` | `provider_failure` | `ERR-PROVIDER-FAIL`/`ERR-PROVIDER-CONTRACT` | 上游 provider 返回错误 |
| `503` | `service_unavailable` | `ERR-PROVIDER-UNAVAIL`/`ERR-MODEL-UNAVAIL`/`ERR-STORE` | provider/存储不可用 |

错误响应格式：

```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "request_error",
    "code": "invalid_request",
    "param": null,
    "retryable": false
  }
}
```

> 注：`openapi` `ErrorDetail` 实际 `type`/`code` 枚举与上表示例行不同（无 `retryable` 字段）；以 §1 机器源为准，上表保留原阅读视图并标 `Proposed`。

### 4.2 Blocker / 未决 catalog

见 `llmtier-contract-specification` §4.2（`B-CONTRACT-01/02/03`）。

## 5. 接口设计（幂等、并发、事务与一致性）

> 分类同 §2（API/消息与数据流接口适用）。逐接口结果已回写 §2 各记录的“交互与生命周期”。ETag / Concurrency Control（原 §6）：可变更资源（Provider、Deployment、Service Level）使用 ETag 进行并发控制：

- GET 返回 `ETag` header
- PATCH/DELETE 必须发送 `If-Match: <etag>` header
- 版本不匹配返回 `412` `ERR-STALE`

管理 CRUD 须一致地校验引用并审计；PATCH 为原子局部更新，失败不得留下 partial write。外部契约不承诺 custom idempotency/exactly-once。

## 6. Pagination、filter、ordering 与 retention

列表接口使用游标分页：

```
GET /v1/providers?limit=10&cursor=xxx
```

响应：

```json
{
  "data": [],
  "page": {"has_more": true, "next_cursor": "cursor_value"}
}
```

Usage 分页要求见 `llmtier-contract-specification` §6；模型列表不分页；retention 为 LLMTier 内部政策。

## 7. 身份、权限、Secret 与调用边界

### 7.1 Data Plane Auth

使用 `Authorization: Bearer <token>` header。`LLMTIER_DATA_TOKEN` 环境变量配置。

### 7.2 Admin Auth

使用 `Authorization: Bearer <token>` header。`LLMTIER_ADMIN_TOKEN` 环境变量配置。

### 7.3 Trusted LAN Mode

当 `LLMTIER_TRUSTED_LAN_MODE=1` 且客户端 IP 在 `192.168.1.0/24` 时：可使用 `trusted-lan-consumer` / `trusted-lan-operator` 角色，不需要 Bearer Token。

### 7.4 Common Headers

| Header | 说明 |
|--------|------|
| `Authorization` | `Bearer <token>` |
| `Content-Type` | `application/json` |
| `If-Match` | ETag for concurrency control |
| `X-Request-ID` | 请求追踪 ID（只作关联，不承担 session/task/recovery 语义） |

credential 只用于授权，不形成 Client/Source/SourceInstance DTO；Secret 只写引用、view 仅 `has_secret`；生产使用 TLS。

## 8. 接口设计（版本、兼容性与迁移）

> 分类同 §2；逐接口版本结果回写 §2 各记录。Admin API 与 Data Plane 随 `openapi`/manifest 显式版本变更，无运行时兼容协商。本候选替代 `0.3-finalization-candidate.5`，旧 custom endpoints/headers/schemas/fixtures 退出 current authority，无 alias/fallback；legacy `/call` 不属于 current contract。兼容基线 `interfaces/compatibility/compatibility-manifest-v0.3.json`。

## 9. Positive/Negative fixture 与 validator

向量 `interfaces/vectors/v0.3/*`（`openai-surface-fixtures.json`、`usage-fixtures.json`、`admin-model-fixtures.json`、`stateless-gateway-boundary-fixtures.json`）；validator 要求见 `llmtier-contract-specification` §9。静态可解析不等于语义通过。

## 10. Requirement → Contract → Test traceability

见 `llmtier-contract-specification` §10（CT-DP-001、CT-MODEL-001、CT-EMB-001、CT-USAGE-001、CT-ADMIN-001、CT-OPS-001、CT-BOUNDARY-001、CT-SCOPE-001）。

## 11. Activation Gate 与未决项

`runtime_activation=false`；需实现、provider capture、Piko 消费签署、Embedding consumer test、auth/TLS/operations、Admin UI test。`interfaces/error-codes/` 未建立 → `B-CONTRACT-01`；见 `llmtier-contract-specification` §4.2/§11。

## 附录 A. Service Tiers (Service Levels) 与 Environment Variables

LLMTier 预定义了以下服务等级（`TierId`，§3.1）：

| Tier ID | 说明 |
|---------|------|
| `Senior` | 最高优先级 |
| `Junior` | 高优先级 |
| `Worker` | 标准优先级 |
| `Associate` | 中优先级 |
| `Engineer` | 工程优先级 |
| `Executor` | 执行优先级 |
| `Embedding-v1` | Embedding 专用 |

| Variable | 说明 |
|----------|------|
| `LLMTIER_ADMIN_TOKEN` | Admin API 认证 token |
| `LLMTIER_DATA_TOKEN` | Data API 认证 token |
| `LLMTIER_TRUSTED_LAN_MODE` | 启用信任局域网模式（1=on） |
| `LLMTIER_DEV_MODE` | 开发模式（1=on） |
