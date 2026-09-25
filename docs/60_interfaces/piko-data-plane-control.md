<!-- STD_DOCUMENT_COVER_BEGIN -->
# Piko ↔ LLMTier Data Plane Interface Control

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-piko-data-plane-control` |
| Document Version | `0.3.2-draft.4` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko |
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
| Canonical Path | `docs/60_interfaces/piko-data-plane-control.md` |
| Supersedes | `docs/99_reference/contracts/piko-data-plane-contract-v0.3.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 接口目的、范围与双方 authority

Piko 拥有 Agent session、完整输入装配、压缩、tool loop、任务 deadline/budget 和执行内 retry。LLMTier 只提供标准 OpenAI-compatible 模型服务，不读取 Piko Run/Session/IR/STD，也不执行工具或管理 backend KV identity。

- **提供方**：LLMTier（M001 HTTP/SSE、M003 Inference）；**消费者**：Piko。
- **唯一字段级 authority**：`interfaces/openapi/llmtier.openapi.json`（version `0.3-simplified-candidate.8`，sha256 `b34428126390056e3eb7927ccb219e5185962a3c5483abb6d9f4fab7ed9a417a`）。
- **本文拥有**：双方交接边界、标准 Responses/SSE 路径、Usage 消费口径与错误/版本约定；不定义 LLMTier 内部算法。
- **ID/错误**：复用系统设计 §8/§9 的 `D-*`/`IF-*` 与 §8.8 的 `ERR-*`；`interfaces/error-codes/` 未建立 → **Proposed**。
- **部署条件**：HTTPS + JSON + Bearer auth；production TLS/auth 尚未激活。`runtime_activation=false`。

## 2. 接口设计（接口注册表）

> 按 STD `design-data-interface-format` 1.2.0 §3 按**接口形态分类**；分类适用性：2.1 软件接口 ✓（HTTP）｜2.2 消息与数据流接口 ✓（SSE）｜2.3 硬件与固件接口 ✗（纯软件）｜2.4 人机与维护接口 ✗（无 UI/CLI）。

### 2.0 接口注册表

| Interface ID | Method | Path | Purpose | Status |
|---|---|---|---|---|
| `IF-DP-RESPONSES` | POST | `/v1/responses` | 完整输入的一次模型调用；固定 `stream:true/store:false` 标准 SSE | Implemented |
| `IF-DP-MODELS` | GET | `/v1/models` | 逻辑模型列表 | Implemented |
| `IF-DP-MODELS` | GET | `/v1/models/{model}` | exact-case 模型能力 | Implemented |
| `IF-ADM-USAGE` | GET | `/v1/usage` | 调用主体自己的 token Usage 查询；Piko 可按 request ID 汇总任务用量 | Implemented |
| `IF-MSG-SSE` | — | `text/event-stream` | 标准 Responses SSE 事件子集 | Implemented |

无 Invocation、response retrieval、custom recovery、capacity、compatibility 或 caller-management endpoint。编目范围=`selected_members`。

### 2.1 软件接口（适用时）

#### `POST /v1/responses`

```text
POST /v1/responses
  Authorization: Bearer <data-token>
  traceparent: string?          # 标准 trace context 可用于诊断
  X-Request-ID: string          # response 回填；只作关联
  body: ResponsesRequest {model, stream:true, store:false, input, tools?, tool_choice?, ...}
  -> 200 text/event-stream: ResponseStreamEvent (SSE 子集, §2.2.1)
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-RESPONSES`；规格已定、Implemented；唯一契约=`openapi` candidate.8；`src/http_api/app.py` → `src/inference/responses.py`。
- **输入**：Piko 每次发送 `ResponsesRequest.model`（exact service-level ID）、`stream:true`、`store:false` 和该轮所需的完整 `input`（§4.2）；Bearer auth。
- **成功输出**：标准 SSE（§2.2.1）；LLMTier 只透传/规范化，不保存 Agent conversation。
- **错误与异常**：`ERR-REQ-VALIDATION`/`ERR-REQ-FIELD`/`ERR-REQ-JSON`/`ERR-REQ-UNSUPPORTED`（400）、`ERR-REQ-TOO-LARGE`（413）、`ERR-AUTH-*`（401/403/503）、`ERR-MODEL-NOTFOUND`（404 exact model）、`ERR-RATE-LIMIT`（429，可带 `Retry-After`）、`ERR-PROVIDER-FAIL`/`ERR-PROVIDER-UNAVAIL`（502/503）、`ERR-MODEL-UNAVAIL`（503）、`ERR-INTERNAL`（500）。网络结果未知时不得由 LLMTier 推导 Piko 任务成功/失败。
- **交互与生命周期**：每次 HTTP request 独立：validate → internal admit → provider call → response/error（§5）；不是 Agent conversation 状态机；Piko 在自己的 deadline/budget 内决定 retry；V0.3 不承诺模型级 exactly-once，不定义 custom Idempotency-Key、Invocation、UnknownOutcome 或结果恢复协议（§6）。
- **实例与验证**：固定 Pi golden request（§10/§11）。`openai-surface-fixtures.json`；`VRC-INF-001/002`。

#### `GET /v1/models` / `GET /v1/models/{model}`

```text
GET /v1/models         -> 200 ModelList {object, data:[Model]}
GET /v1/models/{model} -> 200 Model {id, availability, capabilities}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-MODELS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/models.py`。
- **输入**：路径 `model` exact-case 名；Data Bearer；无 body。
- **成功输出**：`D-MODEL`（§4.2）；只发布逻辑等级与能力，不暴露物理账号/provider。
- **错误与异常**：`ERR-AUTH-*`（401/403）；detail 未知 exact 名 → `ERR-MODEL-NOTFOUND`（404）。
- **交互与生命周期**：同步只读；幂等；不提供运行时 compatibility 协商（§9）。
- **实例与验证**：正常固定 tier；拒绝未知名。`admin-model-fixtures.json`；`VRC-INF-001`。

#### `GET /v1/usage`

```text
GET /v1/usage?from=&to=&model=&request_id= -> 200 UsagePage
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/inference/usage.py`。
- **输入**：`from`/`to` 必填，可选 `model`/`request_id`/`cursor`/`limit`；调用主体自己的 token Usage。
- **成功输出**：`UsagePage`（§4.2）；同一 `request_id` 的较高 `record_version` 替换较低版本，不能和响应 usage 重复相加。
- **错误与异常**：`ERR-AUTH-*`；`ERR-CURSOR`（400）；`ERR-STORE`（503 typed，不用空页）。
- **交互与生命周期**：Piko 可按自身 task/run 聚合不同 request 的最新事实；LLMTier 不接收 task identity。
- **实例与验证**：正常分页与版本替换。`usage-fixtures.json`；`VRC-MGMT-006`。

### 2.2 消息与数据流接口（适用时）

#### `Responses SSE 事件子集`

```text
stream: text/event-stream
  event: response.created | response.output_item.added | response.output_text.delta
       | response.refusal.delta | response.refusal.done
       | response.reasoning_summary_text.delta | response.reasoning_text.delta
       | response.reasoning_summary_part.done
       | response.function_call_arguments.delta | response.function_call_arguments.done
       | response.output_item.done | response.completed | response.incomplete | response.failed
       | error
  data: ResponseStreamEvent (type/sequence_number)
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-MSG-SSE`；规格已定、Implemented；`openapi` `ResponseStreamEvent`；`src/http_api/sse.py`、`src/inference/responses.py`。
- **输入**：一次已受理的 `POST /v1/responses`。
- **成功输出**：必需事件 created、output item added/done、text delta、refusal delta/done、reasoning summary/text delta/done、function arguments delta/done、completed/incomplete/failed 与 error；成功流必须恰有一个 terminal，terminal response 携带可用 Usage。
- **错误与异常**：流内 `error`/`response.failed`；不伪造完成。
- **交互与生命周期**：同一 output item 的 `item.id`、`output_index` 必须一致；客户端断开结束本次调用并释放许可；不承诺可恢复 Invocation。
- **实例与验证**：固定 Pi golden request；SSE item identity/terminal。`openai-surface-fixtures.json`；`VRC-INF-002/005`。

### 2.3 硬件与固件接口（适用时）

不适用：纯软件，无连接器/总线/寄存器/FPGA 端口。

### 2.4 人机与维护接口（适用时）

不适用：Piko↔LLMTier 无 UI/CLI 操作面。

## 3. 传输与物理边界

> 分类同 §2；逐接口端点/认证回写 §2 声明。

- **软件接口**：HTTPS + JSON + Bearer auth；production TLS/auth 尚未激活。标准 `traceparent` 可用于诊断；响应 `X-Request-ID` 只作关联，不是 session、task、idempotency 或 recovery identity。
- **消息与数据流接口**：`text/event-stream`，标准 SSE 帧；`sequence_number` 稳定顺序。
- **硬件与固件接口**：不适用。
- **人机与维护接口**：不适用。

## 4. 数据结构设计（数据、命令与 Schema）

> 按 STD `design-data-interface-format` 1.2.0 §2 按**数据性质**分类；wire 字段以 §1 `openapi` 为机器权威，本节只给阅读视图与含义。

**类别适用性**：4.1 公共基础类型与枚举 ✓｜4.2 业务与操作数据结构 ✓｜4.3 配置与规则数据结构 ✓｜4.4 通信报文结构 ✓（机器源继承）｜4.5 设备与 FPGA 表项结构 ✗（纯软件）｜4.6 运行状态数据结构 ✓｜4.7 数据库表结构 ✓（authority `util/migrations/*.sql`）｜4.8 错误码与错误结构 ✓（引用系统 §8.8）。

### 4.1 公共基础类型与枚举

#### `ResponseStatus` / `availability` / `measurement_status` / `source` / `encoding_format`
- **定义、Data/Type ID 与唯一来源**：共享枚举；机器源 `openapi` `ResponsesResponse`/`Model`/`UsageRecord`/`EmbeddingRequest`。
- **字段**：见 `llmtier-contract-specification` §3.1。
- **约束 / 不变量**：`measurement_status=unknown ⇒ token 全 null`；`measured ⇒ source=provider`；`estimated ⇒ source=gateway_estimate`。
- **状态 · 所有权 · 寿命**：内联于所属结构。
- **合法与拒绝实例**：合法 `completed`/`measured`；边界 unknown 不补零。
- **验证**：`openapi`；`VRC-INF-004`。

### 4.2 业务与操作数据结构

#### `ResponsesRequest`（Piko 固定请求形状）
- **定义、Data/Type ID 与唯一来源**：Piko 每轮发送的完整输入；机器源 `openapi` `ResponsesRequest`；兼容证据=固定 Pi 0.85.1。
- **字段**：`model`（exact service-level ID）、`stream:true`、`store:false`、`input`；`input` 首轮 `system|developer|user` easy message 不要求 `type`；历史 assistant message 可带 `id/status/phase` 和 `output_text.annotations`；function call 同时保留 item `id` 与 `call_id`；`function_call_output.output` 可以是 string，或由 `input_text|input_image` 构成的数组；opaque reasoning item 原样进入下一轮历史。
- **约束 / 不变量**：模型输出 tool call 后，Piko 自行执行工具，并在新的完整请求中提交相同 `call_id` 的 result；LLMTier 只透传/规范化，不保存 Agent conversation。
- **状态 · 所有权 · 寿命**：请求级 wire 载荷；无 conversation 持久。
- **合法与拒绝实例**：合法固定 Pi 请求；拒绝 `stream=false`→`ERR-REQ-UNSUPPORTED`。
- **验证**：`openai-surface-fixtures.json`；`VRC-INF-001/002`。

#### `TokenUsage` / `UsageRecord` / `UsagePage`
- **定义、Data/Type ID 与唯一来源**：响应与查询的 token 事实；`D-MSG-RESPONSE.usage`/`D-USAGE-RECORD`；机器源 `openapi`。
- **字段**：`ResponsesResponse.usage` 使用标准 `input_tokens/output_tokens/total_tokens`，存在时保留 `input_tokens_details.cached_tokens/cache_write_tokens` 与 `output_tokens_details.reasoning_tokens`；`UsageRecord` 含 `request_id/record_version/is_final/model/endpoint/recorded_at/updated_at/measurement_status/source` 与 token 字段。
- **约束 / 不变量**：`input_tokens` 包含 cached token，`cached_tokens` 是其子集；`cache_write_tokens` 是额外观测细分，不再加进 `input_tokens` 或 `total_tokens`；`reasoning_tokens` 是 `output_tokens` 子集；缺失 usage 不会把成功模型结果改成失败，Piko 将该调用记为 Unknown；同 request 高版本替换低版本、不重复相加。
- **状态 · 所有权 · 寿命**：请求级响应 + 追加式账本，按 principal 隔离。
- **合法与拒绝实例**：合法 measured 带 details；边界 missing usage → Unknown（不失败、不补零）。
- **验证**：`usage-fixtures.json`；`VRC-INF-004`、`VRC-MGMT-006`。

#### `Model` / `ModelList` / `ModelCapabilities`
- **定义、Data/Type ID 与唯一来源**：逻辑模型目录与能力；`D-MODEL`/`D-CAPABILITY`；机器源 `openapi`。
- **字段**：见 `llmtier-contract-specification` §3.2/§3.3。
- **约束 / 不变量**：`id` exact-case；不暴露物理 provider/account。
- **状态 · 所有权 · 寿命**：只读投影。
- **合法与拒绝实例**：合法固定 tier；拒绝未知名。
- **验证**：`admin-model-fixtures.json`；`VRC-INF-001`。

### 4.3 配置与规则数据结构

`ModelCapabilities`、`AuthPolicy`/`TrustedLanPolicy` 见 `llmtier-contract-specification` §3.3；Piko 侧规则（session 装配、tool loop、deadline/budget、retry）由 Piko 拥有，本文只约束 LLMTier 不读取这些对象。

### 4.4 通信报文结构（机器源继承）

`ResponsesRequest`、`ResponsesResponse`、`ResponseStreamEvent`、`ErrorEnvelope`、`Model`/`ModelList`、`UsagePage` 均为 JSON/SSE 报文；字段级 authority `openapi`；阅读视图见 `llmtier-contract-specification` §3.4。

### 4.5 设备与 FPGA 表项结构（适用时）

不适用：纯软件，无设备/RTL 表项。

### 4.6 运行状态数据结构

#### `D-USAGE-OBLIGATION` / `D-USAGE-HEAD` / `HealthView` / `ReadinessView`
- **定义、Data/Type ID 与唯一来源**：dispatch 前义务、单调 head 与就绪事实；本设计/系统设计；authority `util/migrations/*.sql`、`openapi`。
- **字段**：见 `llmtier-contract-specification` §3.6。
- **约束 / 不变量**：dispatch 前义务必须先存在；head 单调；`/readyz` 模型级 availability。
- **状态 · 所有权 · 寿命**：M003 写、请求级就绪。
- **合法与拒绝实例**：合法义务先于 dispatch；边界未登记即 dispatch 被业务禁止。
- **验证**：`VRC-INF-004`、`VRC-UTIL-001/002`。

### 4.7 数据库表结构

Authority `util/migrations/*.sql`；公共可观察表（usage_obligations/usage_record_versions/usage_heads 等）见 `llmtier-contract-specification` §3.7。

### 4.8 错误码与错误结构

400 validation、401 auth、404 exact model not found、429 rate limited、502 provider failure、503 unavailable；ID 与含义见系统设计 §8.8 与 `llmtier-contract-specification` §4.1。429 可携带 `Retry-After`。`interfaces/error-codes/` 未建立 → **Proposed**。

## 5. 接口设计（状态机、顺序和时序）

> 分类同 §2；逐接口适用条件回写 §2 声明。

- **软件接口**：每次 HTTP request 独立：validate → internal admit → provider call → response/error。它不是 Agent conversation 状态机。Piko task 与单次模型 request 的顺序、停止和继续由 Piko 管理。
- **消息与数据流接口**：complete/incomplete/failed 由恰好一个 terminal 事件表达；成功流必须恰有一个 terminal 且携带可用 Usage。

## 6. 接口设计（错误、timeout、重试、幂等和恢复）

> 分类同 §2；逐接口 Error ID 回写 §2 声明。

- Piko 在自己的 deadline/budget 内决定 retry；V0.3 不承诺模型级 exactly-once，不定义 custom Idempotency-Key、Invocation、UnknownOutcome 或结果恢复协议。
- 网络结果未知时不得由 LLMTier 推导 Piko 任务成功/失败；Piko 按标准 client/provider semantics 处理。具有副作用的工具不在 LLMTier 内执行。
- `ERR-RATE-LIMIT` 可带 `Retry-After`；`ERR-PROVIDER-*` 不静默跨等级 fallback。

## 7. 并发、流控、容量与性能

LLMTier 内部 queue/concurrency guard 可返回 429/503，但不暴露 Seat、claim、capacity snapshot、shared pool 或 quota composition。Piko 自身执行容量与 LLMTier 内部模型保护互不替代。

## 8. 安全、身份、权限和隔离

Bearer credential 控制 Data Plane 访问；不定义 Client/Source/SourceInstance 产品层级。普通响应/日志不回显 credential、Provider Secret 或 prompt/output。模型 ID 不能用于推导物理 provider/account。

## 9. 接口设计（版本协商、兼容矩阵与弃用）

> 分类同 §2；逐接口版本结果回写 §2 声明。

不提供运行时 compatibility negotiation endpoint。版本通过发布的 OpenAPI/manifest 和显式变更 review 管理。legacy `/call` 与旧 custom recovery contract 一次性退出 consumer authority，无 alias 或 fallback。兼容基线 `interfaces/compatibility/compatibility-manifest-v0.3.json`。

## 10. Contract fixture、验证与证据

验证：固定 Pi golden request（首轮 easy message、assistant 历史、function call/output、image tool result、opaque reasoning）、标准 SSE item identity 与 terminal、refusal/reasoning 事件、exact model、429/5xx、标准 usage 存在/缺失及查询替换、旧 path/header absence。真实 Pi/provider capture 属于实现 Gate，不阻止设计候选 review，但阻止 activation。

| 成员/规则 → 设计 V | 提供/消费与 backend | Case / 所需环境 | 实现/运行状态 | Run/证据或缺口 |
|---|---|---|---|---|
| `IF-DP-RESPONSES`/`IF-MSG-SSE` → VRC-INF-001/002 | M001/M003 | openai-surface-fixtures | NOT_RUN | 真实 Pi capture BLOCKED |
| Usage 替换 → VRC-MGMT-006 | M003/M007 | usage-fixtures | NOT_RUN | — |
| 旧 path/header absence → VRC-API-002 | M001 | boundary fixtures | NOT_RUN | — |

## 11. 定型候选与双方批准

固定 Pi 0.85.1、commit `9767ba275f3e9a5ee0f5c5342249b629ab1b2282` 的 `openai-responses.ts::buildParams` 固定发送 `stream:true` 与 `store:false`；契约据此只支持这一条标准 Responses SSE 路径，不建立 non-stream fallback。必需事件为 created、output item added/done、text delta、refusal delta/done、reasoning summary/text delta/done、function arguments delta/done、completed/incomplete/failed 与 error；同一 output item 的 `item.id`、`output_index` 必须一致，成功流必须恰有一个 terminal，terminal response 携带可用 Usage。Piko 消费签署与真实 capture 仍是 activation gate，runtime activation=false；`interfaces/error-codes/` 未建立（`B-CONTRACT-01`）。
