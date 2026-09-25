<!-- STD_DOCUMENT_COVER_BEGIN -->
# Slinky ↔ LLMTier Usage and Embeddings Interface Control

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-slinky-capacity-observation-control` |
| Document Version | `0.3.2-draft.3` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Slinky |
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
| Canonical Path | `docs/60_interfaces/slinky-capacity-observation-control.md` |
| Supersedes | `docs/99_reference/contracts/slinky-capacity-observation-contract-v0.3.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 接口目的、范围与双方 authority

Slinky Memory只消费标准Embeddings与token Usage。Slinky拥有材料分块、向量库、索引、检索、正式记忆和业务验收；LLMTier只做向量化和模型服务。文件名保留以维持文档引用，但“capacity observation”旧范围已经退出current authority。

- **提供方**：LLMTier（M001 HTTP、M003 Inference）；**消费者**：Slinky Memory。
- **唯一字段级 authority**：`interfaces/openapi/llmtier.openapi.json`（version `0.3-simplified-candidate.8`，sha256 `b34428126390056e3eb7927ccb219e5185962a3c5483abb6d9f4fab7ed9a417a`）。
- **本文拥有**：Embeddings/Usage 交接边界、向量空间稳定性、错误与版本约定；不定义 Slinky 内部索引机制。
- **ID/错误**：复用系统设计 §8/§9 的 `D-*`/`IF-*` 与 §8.8 的 `ERR-*`；`interfaces/error-codes/` 未建立 → **Proposed**。
- **部署条件**：HTTPS/JSON/Bearer auth。`runtime_activation=false`。

## 2. 接口设计（接口注册表）

> 按 STD `design-data-interface-format` 1.2.0 §3 按**接口形态分类**；分类适用性：2.1 软件接口 ✓（HTTP）｜2.2 消息与数据流接口 ✗（无事件/流）｜2.3 硬件与固件接口 ✗（纯软件）｜2.4 人机与维护接口 ✗（无 UI/CLI）。

### 2.0 接口注册表

| Interface ID | Method | Path | Purpose | Status |
|---|---|---|---|---|
| `IF-DP-EMBEDDINGS` | POST | `/v1/embeddings` | 标准向量化 | Implemented |
| `IF-DP-MODELS` | GET | `/v1/models` / `{model}` | 选择 `capabilities.embeddings=true` 的 exact model | Implemented |
| `IF-ADM-USAGE` | GET | `/v1/usage` | 只读 token 事实 | Implemented |
| `IF-HEALTH` | GET | `/healthz` / `/readyz` | 环境检查 | Implemented |

没有 capacity snapshot、Seat、Invocation、recovery、Cost 或 compatibility endpoint。编目范围=`selected_members`。

### 2.1 软件接口（适用时）

#### `POST /v1/embeddings`

```text
POST /v1/embeddings
  Authorization: Bearer <data-token>
  body: EmbeddingRequest {model, input, encoding_format?("float"|"base64"), dimensions?, user?}
  -> 200: EmbeddingResponse {object:"list", data:[EmbeddingItem], model, usage:{prompt_tokens,total_tokens}}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-EMBEDDINGS`；规格已定、Implemented；唯一契约=`openapi` candidate.8；`src/http_api/app.py` → `src/inference/embeddings.py`。
- **输入**：`EmbeddingRequest`（§4.2）——exact `model`、`input`（string/string[]）、可选 `encoding_format`/`dimensions`/`user`；Data Bearer；Memory 只发送标准 embedding request 内容，不传 Project/Memory 对象。
- **成功输出**：`EmbeddingResponse`（§4.2）向量、model 与标准 `prompt_tokens/total_tokens` usage。
- **错误与异常**：标准 `ERR-REQ-VALIDATION`（400，含维数/数量/索引/未知字段）、`ERR-AUTH-REQUIRED`/`ERR-AUTH-DENIED`（401/403）、`ERR-MODEL-NOTFOUND`（404 非 embedding model）、`ERR-RATE-LIMIT`（429）、`ERR-PROVIDER-FAIL`/`ERR-PROVIDER-UNAVAIL`（502/503）、`ERR-STORE`（503）。
- **交互与生命周期**：每个 embedding POST 独立；重试由 Slinky Memory 按标准 HTTP/client policy 决定；无 custom Idempotency、Invocation、202 active、410 tombstone 或 Responses GET recovery。
- **实例与验证**：正例 float/base64、batch index/数量/有限数；负例非 embedding model/维数不支持/同 ID 空间漂移。`openai-surface-fixtures.json`；`VRC-INF-001`。

#### `GET /v1/models` / `GET /v1/models/{model}`

```text
GET /v1/models         -> 200 ModelList {object, data:[Model]}
GET /v1/models/{model} -> 200 Model {id, availability, capabilities}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-DP-MODELS`；规格已定、Implemented；`openapi` candidate.8；`src/inference/models.py`。
- **输入**：路径 `model` exact 名；Data Bearer。
- **成功输出**：`D-MODEL`（§4.2）；Models 能力同时发布稳定的 `embedding_space_id`、输出维数、batch 与输入上限；同一个逻辑 model ID 在兼容期内必须保持同一向量空间，任何不兼容变化必须使用新逻辑 model ID。
- **错误与异常**：`ERR-AUTH-*`；未知 exact 名 → `ERR-MODEL-NOTFOUND`（404）。
- **交互与生命周期**：同步只读；Slinky 选择 `capabilities.embeddings=true` 的 exact model。
- **实例与验证**：正常返回带 embedding 能力；拒绝非 embedding model。`admin-model-fixtures.json`；`VRC-INF-001`。

#### `GET /v1/usage`

```text
GET /v1/usage?from=&to=&model=&request_id= -> 200 UsagePage
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-ADM-USAGE`；规格已定、Implemented；`openapi` candidate.8；`src/inference/usage.py`。
- **输入**：时间窗/过滤参数；调用主体自己的 token 事实。
- **成功输出**：`UsagePage`（§4.2）；`unknown` 时 token 均为 null、不得补零；更高 record version 替换较低版本。
- **错误与异常**：`ERR-AUTH-*`；`ERR-CURSOR`（400）；`ERR-STORE`（503，不用空页）。
- **交互与生命周期**：只读；Cost 不在 Schema 中。
- **实例与验证**：usage measured/estimated/unknown 与版本替换。`usage-fixtures.json`；`VRC-MGMT-006`。

#### `GET /healthz` / `GET /readyz`

```text
GET /healthz -> 200 HealthView {status, version}
GET /readyz  -> 200 ReadinessView {status, models:[{id, availability}]} / 503 not_ready
```

- **Interface/Member ID、状态、唯一契约、文件·symbol**：`IF-HEALTH`；规格已定、Implemented；`openapi` candidate.8；`src/http_api/health.py`。
- **输入**：无参数、无凭据。
- **成功输出**：`HealthView`/`ReadinessView`（§4.6）；环境检查。
- **错误与异常**：bootstrap/schema 失败 → 503 `not_ready`（`ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`）。
- **交互与生命周期**：同步只读。
- **实例与验证**：正常 READY；边界 not_ready。`VRC-UTIL-001/002`。

### 2.2 消息与数据流接口（适用时）

不适用：Slinky↔LLMTier 无事件/队列/流；Embeddings 为同步请求/响应。

### 2.3 硬件与固件接口（适用时）

不适用：纯软件，无连接器/总线/寄存器/FPGA 端口。

### 2.4 人机与维护接口（适用时）

不适用：无 UI/CLI 操作面。

## 3. 传输与物理边界

> 分类同 §2；逐接口端点/认证回写 §2 声明。

- **软件接口**：HTTPS/JSON/Bearer auth。Memory 调用不进入 Piko 的模型调用控制面，也不传 Project/Memory 对象给 LLMTier；只发送标准 embedding request 内容。
- **消息与数据流接口**：不适用。
- **硬件与固件接口**：不适用。
- **人机与维护接口**：不适用。

## 4. 数据结构设计（数据、命令与 Schema）

> 按 STD `design-data-interface-format` 1.2.0 §2 按**数据性质**分类；wire 字段以 §1 `openapi` 为机器权威，本节只给阅读视图与含义。

**类别适用性**：4.1 公共基础类型与枚举 ✓｜4.2 业务与操作数据结构 ✓｜4.3 配置与规则数据结构 ✓｜4.4 通信报文结构 ✓（机器源继承）｜4.5 设备与 FPGA 表项结构 ✗（纯软件）｜4.6 运行状态数据结构 ✓｜4.7 数据库表结构 ✓（authority `util/migrations/*.sql`）｜4.8 错误码与错误结构 ✓（引用系统 §8.8）。

### 4.1 公共基础类型与枚举

#### `encoding_format` / `measurement_status` / `source` / `availability`
- **定义、Data/Type ID 与唯一来源**：共享枚举；机器源 `openapi` `EmbeddingRequest`/`UsageRecord`/`Model`。
- **字段**：`encoding_format ∈ {float,base64}`（默认 `float`）；`measurement_status ∈ {measured,estimated,unknown}`；`source ∈ {provider,gateway_estimate,unavailable}`；`availability ∈ {available,degraded,unavailable}`。
- **约束 / 不变量**：`unknown ⇒ token 全 null`；base64 为连续 little-endian IEEE-754 float32。
- **状态 · 所有权 · 寿命**：内联于所属结构。
- **合法与拒绝实例**：合法 `float`/`measured`；边界 unknown 不补零。
- **验证**：`openapi`；`VRC-INF-001/004`。

### 4.2 业务与操作数据结构

#### `EmbeddingRequest`
- **定义、Data/Type ID 与唯一来源**：标准向量化请求；`D-MSG-EMBEDDING`；机器源 `openapi` `EmbeddingRequest`。
- **字段**：`model`（必填，exact embedding tier）、`input`（string 或 string[]，必填）、`encoding_format`（可选，默认 `float`）、`dimensions`（可选）、`user`（可选）。
- **约束 / 不变量**：`encoding_format=float` 返回有限 JSON number array；`base64` 返回 RFC 4648 字符串，其内容固定为连续 little-endian IEEE-754 float32；请求与响应表示必须一致，严格核验解码、4 字节对齐、有限值和维数。
- **状态 · 所有权 · 寿命**：请求级 wire 载荷；不持久 conversation。
- **合法与拒绝实例**：合法 float/base64；拒绝未知 field/维数不支持/向量数量或索引错误。
- **验证**：`openai-surface-fixtures.json`；`VRC-INF-001`。

#### `EmbeddingResponse` / `EmbeddingItem` / `EmbeddingUsage`
- **定义、Data/Type ID 与唯一来源**：标准向量化响应；机器源 `openapi`。
- **字段**：`EmbeddingResponse{object:"list",data:[EmbeddingItem],model,usage:EmbeddingUsage?}`；`EmbeddingItem{object:"embedding",index≥0,embedding:number[]|base64}`；`EmbeddingUsage{prompt_tokens,total_tokens}`。
- **约束 / 不变量**：维数须在模型支持集合内；同一逻辑 model ID 保持同一 `embedding_space_id`。
- **状态 · 所有权 · 寿命**：请求级；向量输出的存储权限由 Slinky 管理。
- **合法与拒绝实例**：合法 batch index/数量/有限数正确；拒绝同 ID 空间漂移。
- **验证**：`openai-surface-fixtures.json`；`VRC-INF-001`。

#### `UsageRecord` / `UsagePage`
- **定义、Data/Type ID 与唯一来源**：token 事实版本与分页；`D-USAGE-RECORD`；机器源 `openapi`。
- **字段**：含 request/model/endpoint/time、record version/finality、measurement status/source 以及标准 token 字段和可用的 cached/cache-write/reasoning 细分。
- **约束 / 不变量**：`unknown` 时 token 均为 null，不得补零；更高 record version 替换较低版本；Cost 不在 Schema 中。
- **状态 · 所有权 · 寿命**：追加式账本，按 principal 隔离。
- **合法与拒绝实例**：合法 measured/estimated；边界 unknown null。
- **验证**：`usage-fixtures.json`；`VRC-MGMT-006`。

#### `Model` / `ModelList` / `ModelCapabilities`
- **定义、Data/Type ID 与唯一来源**：模型目录与 embedding 能力；`D-MODEL`/`D-CAPABILITY`；机器源 `openapi`。
- **字段**：见 `llmtier-contract-specification` §3.2/§3.3；embedding model 发布稳定 space ID、维数、batch 和输入上限。
- **约束 / 不变量**：`capabilities.embeddings=true` 才可选；不兼容空间必须新 model ID。
- **状态 · 所有权 · 寿命**：只读投影。
- **合法与拒绝实例**：合法 embedding exact model；拒绝非 embedding model。
- **验证**：`admin-model-fixtures.json`；`VRC-INF-001`。

### 4.3 配置与规则数据结构

#### `EmbeddingSpaceRule`
- **定义、Data/Type ID 与唯一来源**：向量空间稳定性规则；机器源 `openapi` `ModelCapabilities.embedding_space_id`；本文 §4.2/§5。
- **字段**：`embedding_space_id`、`embedding_dimensions`、`embedding_max_batch_inputs`、`embedding_max_input_tokens`。
- **约束 / 不变量**：同一个逻辑 model ID 在兼容期内必须保持同一向量空间；任何不兼容变化必须使用新逻辑 model ID 并由 Slinky 重建索引。
- **状态 · 所有权 · 寿命**：随 Models 能力发布/Registry。
- **合法与拒绝实例**：合法稳定 space；拒绝同 ID 空间漂移。
- **验证**：`VRC-INF-001`。

#### `ModelCapabilities` / `AuthPolicy`
- `ModelCapabilities`（12 键）与 `AuthPolicy` 见 `llmtier-contract-specification` §3.3。

### 4.4 通信报文结构（机器源继承）

`EmbeddingRequest`/`EmbeddingResponse`/`EmbeddingItem`/`EmbeddingUsage`、`Model`/`ModelList`、`UsagePage`、`ErrorEnvelope` 均为 JSON 报文；字段级 authority `openapi`；阅读视图见 `llmtier-contract-specification` §3.4。

### 4.5 设备与 FPGA 表项结构（适用时）

不适用：纯软件，无设备/RTL 表项。

### 4.6 运行状态数据结构

#### `HealthView` / `ReadinessView` / `D-USAGE-OBLIGATION` / `D-USAGE-HEAD`
- **定义、Data/Type ID 与唯一来源**：环境检查与账本锚点；机器源 `openapi`、authority `util/migrations/*.sql`。
- **字段**：见 `llmtier-contract-specification` §3.6。
- **约束 / 不变量**：dispatch 前义务先存在；head 单调；就绪反映 schema/bootstrap。
- **状态 · 所有权 · 寿命**：请求级就绪 + 追加式账本。
- **合法与拒绝实例**：正常 ready；边界 not_ready。
- **验证**：`VRC-UTIL-001/002`、`VRC-INF-004`。

### 4.7 数据库表结构

Authority `util/migrations/*.sql`；公共可观察表见 `llmtier-contract-specification` §3.7。

### 4.8 错误码与错误结构

使用标准 `ERR-REQ-VALIDATION`、`ERR-AUTH-*`、`ERR-MODEL-NOTFOUND`、`ERR-RATE-LIMIT`、`ERR-PROVIDER-FAIL`/`ERR-PROVIDER-UNAVAIL`、`ERR-STORE`（含义与映射见系统设计 §8.8 与 `llmtier-contract-specification` §4.1）。`interfaces/error-codes/` 未建立 → **Proposed**。

## 5. 接口设计（状态机、顺序和时序）

> 分类同 §2；逐接口适用条件回写 §2 声明。

每个 embedding POST 独立。Slinky 在本地把有效结果原子关联到自己的 index generation；LLMTier 不持有 Memory generation 或索引状态。向量空间身份见 §4.3。

## 6. 接口设计（错误、timeout、重试、幂等和恢复）

> 分类同 §2；逐接口 Error ID 回写 §2 声明。

使用标准 `ERR-REQ-VALIDATION`/`ERR-AUTH-*`/`ERR-MODEL-NOTFOUND`/`ERR-RATE-LIMIT`/`ERR-PROVIDER-*`/`ERR-STORE`。重试由 Slinky Memory 按标准 HTTP/client policy 决定；无 custom Idempotency、Invocation、202 active、410 tombstone 或 Responses GET recovery。

## 7. 并发、流控、容量与性能

内部保护可返回 429/`Retry-After`。Slinky 不读取或计算 Tier Seat/capacity；向量维数、batch 限制和输入上限由 Models 能力与请求校验表达。

## 8. 安全、身份、权限和隔离

credential 只标识获授权调用主体；不引入 SourceInstance。Memory 内容不得进入普通日志；向量输出的存储权限由 Slinky 管理。

## 9. 接口设计（版本协商、兼容矩阵与弃用）

> 分类同 §2；逐接口版本结果回写 §2 声明。

无专用协商 endpoint。旧 Observation/Capacity/Cost contract 与 fixtures 退出 current authority；不作为 fallback。兼容基线 `interfaces/compatibility/compatibility-manifest-v0.3.json`。

## 10. Contract fixture、验证与证据

正例覆盖 float/base64、batch index/数量/有限数、向量空间稳定、usage measured/estimated/unknown 与版本替换；负例覆盖非 embedding model、维数不支持、向量数量/索引/维数错误、同 ID 空间漂移、unknown field、旧 path 不存在。production embedding deployment/capture 尚未完成。

| 成员/规则 → 设计 V | 提供/消费与 backend | Case / 所需环境 | 实现/运行状态 | Run/证据或缺口 |
|---|---|---|---|---|
| `IF-DP-EMBEDDINGS` → VRC-INF-001 | M001/M003 | openai-surface-fixtures | NOT_RUN | 真实 embedding deployment BLOCKED |
| 向量空间稳定 → VRC-INF-001 | M003 | admin-model-fixtures | NOT_RUN | — |
| 旧 Observation/Cost absence → VRC-API-002 | M001 | boundary fixtures | NOT_RUN | — |

## 11. 未决项与双方批准

LLMTier 内部待选择并配置 dedicated embedding deployment；Slinky 需在实现阶段验证实际维数、输入上限、空间 ID 和结果入库。字段与行为已经闭合，没有新的跨系统协议待定。`interfaces/error-codes/` 未建立（`B-CONTRACT-01`）；production embedding deployment/capture 为 activation gate，runtime activation=false。
