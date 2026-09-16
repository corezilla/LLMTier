<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 系统设计

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-design` |
| Document Version | `0.3.2-draft.2` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | 待定 |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-06` |
| Last Modified Date | `2026-09-17` |
| Template Version | `8.3.0` |
| Template ID | `design.system` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/llmtier-system-design.md` |
| Supersedes | `docs/30_subsystem_design/llmtier-service-design.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 文档说明

本文定义 LLMTier 作为一个独立、单应用、单服务的软件系统。它描述 V0.3 的目标设计，不表示目标接口已经实现或激活。字段级 authority 是 `interfaces/openapi/llmtier-v0.3.openapi.json`；能力状态由 compatibility manifest 给出，始终保持 `runtime_activation=false`，直到实现与运行门禁另行批准。

本次设计以主流机制优先：没有已确认特殊需求时采用标准 OpenAI-compatible 请求/响应，不增加自定义 header、恢复端点、调用方层级、会话状态机或并行兼容路径。

## 2. 系统概览

LLMTier 是无 Agent 会话状态的模型网关：调用方在每次请求中提交完成该次推理所需的全部输入；LLMTier 认证、校验、按 exact `model` 选择逻辑等级、调用已配置的云端或本地模型，并返回标准响应与 token Usage。

LLMTier 不保存或补齐 Agent 历史，不做上下文压缩，不执行工具，不拥有 Agent Session/Conversation，不理解 Project、IR、STD、Matrix room/topic，也不创建或匹配后端 KV identity。provider/local runtime 的 cache/KV 是后端内部实现。

Piko 管理 Agent session、上下文、工具循环、模型调用与执行内重试；Slinky 管理业务任务、材料、记忆、流程和验收。Embedding 只提供向量化；分块、索引、向量库和检索属于 Slinky 记忆系统。

## 3. 产品应用与设计目标

| 目标 | 设计决定 |
|---|---|
| 标准模型调用 | 同一 `POST /v1/responses` 支持标准 JSON 与 SSE；Piko 固定 Pi adapter 使用 `stream:true` |
| 模型发现 | `GET /v1/models` 与 exact-case detail；`model` 是逻辑等级 ID，不暴露物理账号 |
| 向量化 | 标准 `POST /v1/embeddings`；使用明确配置的 embedding-capable deployment |
| 工具调用 | 模型可返回 function call；Piko 执行工具并在下一次完整请求中带回 tool result |
| Usage | 响应内返回本次 token Usage；最小只读 `/tier/v1/usage` 提供同一授权主体的统一查询 |
| 自主管理 | Admin API + 中文 Web UI 管理云模型、本地模型、逻辑等级、探测、Usage 与审计 |
| 运维 | 提供无副作用健康/就绪检查；有费用或改变状态的探测、reload、restart 必须获运维授权 |

不在范围：Cost/账单；SourceInstance；外部容量 snapshot/shared pool/Seat/claim；自定义 Idempotency/Invocation/result recovery；跨系统 close/drain/release；专用 compatibility negotiation；调用方或业务会话管理页面。

## 4. 功能与需求实现概览

| 用例 | LLMTier 行为 | 非职责 |
|---|---|---|
| Piko 请求推理 | 校验标准请求，按 exact model 路由，通过标准 SSE 返回文本/tool call/terminal Usage/error | Agent 历史、工具执行、任务重试策略 |
| Slinky 请求 embedding | 校验输入和 embedding 模型，返回向量与 Usage | chunk、索引、检索、正式记忆写入 |
| Consumer 查询模型 | 返回逻辑等级、能力、上下文/输出限制和 availability | 项目选人或业务计划决策 |
| Consumer 查询 Usage | 返回 measured/estimated/unknown token 事实 | 金额、币种、定价、结算 |
| Operator 管理模型 | CRUD provider/deployment/service level，探测并审计 | 调用方、Session、SourceInstance 管理 |

## 5. 总体结构

#### System Context（C4 Level 1）

```mermaid
flowchart LR
  P[Piko Agent Runtime] -->|OpenAI-compatible Responses| L[LLMTier]
  K[Slinky Memory] -->|OpenAI-compatible Embeddings| L
  O[Operator] -->|中文 Admin Web UI / Admin API| L
  L -->|provider-native API| C[Cloud Models]
  L -->|local inference API| M[Local Models]
```

### 5.1 Container View（C4 Level 2）

```mermaid
flowchart TB
  subgraph LT[LLMTier software system]
    API[OpenAI-compatible API]
    ADM[Admin API + 中文 Web UI]
    REG[Logical Model Registry]
    ROUTER[Router and Provider Adapters]
    METER[Usage Meter]
    STORE[(Config / Runtime State / Usage / Audit)]
    API --> REG --> ROUTER
    API --> METER --> STORE
    ADM --> REG
    ADM --> ROUTER
    ADM --> STORE
  end
```

### 5.2 LLMTier Service Component View（C4 Level 3 / arc42 Level-1 Whitebox）

```mermaid
flowchart LR
  AUTH[Bearer Auth] --> VALIDATE[OpenAI Schema Validation]
  VALIDATE --> CATALOG[Logical Model Catalog]
  CATALOG --> SCHED[Internal Queue / Concurrency Guard]
  SCHED --> ADAPTER[Cloud / Local Adapter]
  ADAPTER --> NORMALIZE[Response + Usage Normalizer]
  NORMALIZE --> CLIENT[Caller]
  ADAPTER --> HEALTH[Health / Probe Facts]
```

这些是同一进程内的 logical building block，不是已拆分的子系统。当前没有内部 subsystem design；模块与 ISD 应在本系统设计下展开。

## 6. 工作模式与端到端流程

### 6.1 Responses 与 tool loop

```mermaid
sequenceDiagram
  participant P as Piko
  participant L as LLMTier
  participant B as Model Backend
  P->>L: POST /v1/responses (complete input, exact model)
  L->>L: auth + schema + exact model + internal admission
  L->>B: provider-native request
  B-->>L: text or function call + usage/error
  L-->>P: standard response + usage + X-Request-ID
  Note over P: Piko executes tool and submits a new complete request
```

Piko 固定依赖 `pi@9767ba275f3e9a5ee0f5c5342249b629ab1b2282` 的
`packages/ai/src/api/openai-responses.ts::buildParams` 固定生成 `stream:true`，并由
`processResponsesStream` 消费标准 Responses SSE。LLMTier 因此在同一 endpoint 上提供标准 SSE；
`stream:false` 仍是同一 OpenAI-compatible endpoint 的普通 JSON 模式，不是第二 inference path 或 fallback。

首版必需事件子集为 `response.created`、`response.output_item.added`、
`response.output_text.delta`、`response.function_call_arguments.delta|done`、
`response.output_item.done`、`response.completed|incomplete|failed` 和 `error`。
Usage 位于 terminal response；tool result 由 Piko 执行后以新请求中的 `function_call_output` 传回。

每个 HTTP 请求是独立模型调用。网络结果不明时，Piko 按标准 client retry policy 处理；V0.3 不承诺跨系统 exactly-once，也不提供 Invocation 查询或结果恢复。LLMTier 内部可保留防重、队列或 provider 可靠性机制，但不得形成对外会话或恢复契约。

### 6.2 Embeddings

```mermaid
sequenceDiagram
  participant K as Slinky Memory
  participant L as LLMTier
  participant E as Embedding Backend
  K->>L: POST /v1/embeddings (model, input)
  L->>E: provider-native embedding request
  E-->>L: vectors + token usage
  L-->>K: EmbeddingResponse + X-Request-ID
```

### 6.3 运维恢复

服务启动、reload、restart、backend probe 是环境运维，不是 Piko 任务或模型调用状态机。健康检查可自动读取；真实 provider probe 可能计费，配置变更和 restart 改变状态，必须通过受授权 operator 执行。恢复后以 health/readiness、配置版本、目标模型可用性及受控 smoke request 分层确认；环境恢复不等于上层任务成功。

## 7. 硬件实现方案

LLMTier 不规定专用硬件。部署可连接云 provider 或本地主机上的推理服务。本地 GPU/CPU、驱动、模型文件与资源限制由 deployment 配置和运行环境管理，不能从逻辑等级 ID 推断。

## 8. 软件实现方案

| 路径 | 职责 |
|---|---|
| `src/` | 单服务 Python 源码 |
| `config/settings.json` | Git-ignored 默认配置；provider Secret 使用引用 |
| `state/` | Git-ignored runtime state、Usage 与 audit |
| `interfaces/openapi/` | 唯一当前机器接口候选 |
| `interfaces/compatibility/` | 候选能力与 activation 状态，不承担协商协议 |
| `interfaces/vectors/` | 当前正负 contract fixtures |

目标实现只保留一条 OpenAI-compatible inference path。现有 `/call`、Role routing、CLI/agent/mlexp backend 是 legacy implementation baseline，迁移完成后退出 consumer authority；不得作为 fallback。

## 9. 可编程逻辑与专用处理单元

不适用。LLMTier 不含 FPGA、ASIC 或自定义加速逻辑；本地模型服务器的加速实现属于外部 deployment。

## 10. 数据、描述符与存储结构

| 数据 | 最小内容 | 生命周期 |
|---|---|---|
| Provider | type、endpoint、secret reference、enabled | operator 管理 |
| Deployment | provider/local、model name、capabilities、health | operator 管理 |
| ServiceLevel | exact ID、deployment binding、limits/capabilities | operator 管理与 Models 发布 |
| UsageRecord | request ID、model、token values、measurement status/source、time | 按 LLMTier retention policy |
| AuditEvent | actor、action、target、result、time；不含 Secret/prompt/output | 按审计策略 |

不保存 Agent conversation、tool state、project/task content、正式记忆或后端 KV identity。Prompt/output 日志默认关闭；诊断只保存必要的脱敏关联信息。

## 11. 接口与通信协议

### 11.1 Consumer API

- `POST /v1/responses`
- `POST /v1/embeddings`
- `GET /v1/models`
- `GET /v1/models/{model}`
- `GET /tier/v1/usage`：标准 OpenAI API 没有统一跨请求 token 查询；这是唯一最小扩展，只返回 token 事实，不返回 Cost、容量或执行状态。
- `GET /healthz`、`GET /readyz`：环境探针，不参与模型协议协商。

Bearer credential 只标识获授权调用主体；不暴露 Client/Source/SourceInstance 产品模型。`X-Request-ID` 是服务端响应关联 ID，调用方可发送标准 trace context；它们不是幂等键或会话 ID。

### 11.2 Admin API 与中文 Web UI

```mermaid
flowchart LR
  NAV[侧栏] --> MODELS[模型与等级]
  NAV --> ADD[添加模型]
  NAV --> HEALTHUI[运行状态]
  NAV --> USAGEUI[用量]
  NAV --> AUDITUI[审计]
  MODELS -->|编辑 / 删除| MAPI[Admin API]
  ADD -->|云模型或本地模型| MAPI
  HEALTHUI -->|只读检查 / 授权探测| MAPI
```

页面保持短而单一职责：

1. **模型与等级**：表格列出逻辑等级、类型（云/本地）、后端模型、状态和能力；提供编辑、删除。
2. **添加模型**：选择云模型或本地模型，填写 endpoint/model、Secret 引用、能力和逻辑等级映射；保存前校验，Secret 不回显。
3. **运行状态**：展示服务、deployment 健康与最后探测；真实探测需二次确认并提示可能费用。
4. **用量**：按时间和逻辑等级展示 token measured/estimated/unknown；不显示 Cost。
5. **审计**：展示管理变更和探测结果；不含 prompt/output/credential。

不提供访问控制、容量、恢复、调用方、SourceInstance 或费用页面。

## 12. 可靠性、维护与升级

标准 HTTP 错误区分 validation/auth/model_not_found/rate_limit/provider_unavailable/internal_error。429 可带 `Retry-After`；调用方决定重试。未知 token 数用 `usage=null` 或字段 null + `measurement_status=unknown`，不得填零。

内部队列、并发保护、超时、provider failover 只能在同一 exact service level 的已配置后端集合内工作；不得静默跨等级。内部实现不得向 consumer 暴露 Seat、claim、Invocation 或恢复状态。

## 13. 性能、扩展与兼容性

V0.3 不承诺尚未测量的吞吐/延迟 SLO。扩展先增加同一 service level 的 deployment，再通过内部调度保护资源。兼容以标准 OpenAI shape 和显式版本变更为准，不提供专用 compatibility endpoint 或运行时协商。

## 14. 可测试性与验收设计

静态验收覆盖：OpenAPI 引用解析、Responses/tool-call/tool-result、Embeddings、Models、Usage unknown、429/5xx、Admin CRUD/Secret 不回显、旧路径不存在。运行验收另覆盖 provider capture、token truth、健康/重启、探测授权和 Web UI。

静态 Contract PASS 不代表实现上线；production capture、故障注入和部署证据属于后续 Gate。

## 15. 信息安全架构

Data Plane 与 Admin 使用不同 credential/权限。Provider Secret 只通过 secret reference 解析，不进入普通响应、日志或 UI 回显。默认 bind 为 loopback/private network；production TLS、认证、Secret store、rotation 和审计保留仍需实现证据。

## 16. 结构、热、工艺与安全设计

硬件结构、热与工艺不适用。软件安全依赖资源限制、请求大小限制、timeout、进程隔离和本地模型部署边界；不得因本节不适用而省略信息安全架构。

## 17. 实现计划

1. 以固定 Pi adapter 的标准 Responses SSE 子集实现 Piko 调用，并保留同 endpoint 的标准 JSON 模式。
2. 实现 OpenAI-compatible Responses/Models 和 exact service-level routing。
3. 实现 dedicated Embeddings deployment 与 `/v1/embeddings`。
4. 实现统一 token Usage 记录/查询，明确 measured/estimated/unknown。
5. 将 legacy `/call` 从 consumer authority 退役。
6. 实现精简 Admin API/中文 Web UI 和安全运维流程。
7. 完成 provider/Piko/Knowledge capture 后另行决定 runtime activation。

## 18. 设计决策、风险与未决项

| ID | 状态 | 决策/问题 |
|---|---|---|
| LT-ADR-01 | decided | 无 Agent 会话状态的 OpenAI-compatible gateway |
| LT-ADR-02 | decided | Cost、SourceInstance、外部容量/Seat、Invocation recovery 退出 V0.3 外部契约 |
| LT-ADR-03 | decided | Usage 只提供 token 事实与来源状态；未知不补零 |
| LT-ADR-04 | decided | 固定 Pi adapter 使用 `stream:true`；同一 Responses endpoint 支持标准 SSE 与 JSON，不增加 fallback |
| LT-OPEN-02 | implementation | 选择并配置至少一个 dedicated embedding-capable deployment |
| LT-OPEN-03 | implementation | production auth/TLS/service manager/restart/backup/runbook |

## A. 数据模型与状态机

核心资源只有 Provider、Deployment、ServiceLevel、UsageRecord、AuditEvent。请求生命周期仅为 HTTP request → validate → internal admit → backend call → response/error；内部状态不作为跨系统状态机。

## B. API、Schema、Event、寄存器与错误契约

OpenAPI 是唯一字段级 authority。错误统一为 `{error:{message,type,code,param}}`。没有寄存器或跨系统 event bus。

## C. 持久化、一致性、幂等与恢复

V0.3 不承诺跨系统调用幂等或结果恢复。配置与 Usage/Audit 使用 LLMTier 自身存储；内部可靠性不得改变标准 API 语义。环境恢复只恢复服务配置和内部状态，不恢复 Piko Agent session。

## D. 安全、隐私、Secret 与审计

最小权限、Secret 引用、脱敏 audit、prompt/output 默认不落日志。管理变更记录 actor/action/target/result；Secret 值永不记录。

## E. 可观测性、容量、性能、资源与 SLO

外部只发布 health/readiness、Models、token Usage 和标准错误。内部可观察 queue/concurrency/provider quota，但不形成 Slinky capacity/Seat contract。SLO 需实测后批准。

## F. 测试设计与需求 traceability

需求 ID、OpenAPI operation、fixture 和测试 case 在 traceability 文档中一对一映射。删除的旧扩展必须有“path/schema absent”负例。

## G. 集成、部署、迁移、回滚与发布 Gate

迁移为一次性 authority 替换：旧 candidate 和 legacy `/call` 可留作历史/实现迁移输入，但不作为运行 fallback。runtime activation 独立审批。

## H. 未决问题、外部依赖和后续版本

Responses streaming 范围已按固定 Pi 调用方式选择标准 SSE。剩余是 LLMTier 内部实现：embedding deployment、provider adapter、Web UI、auth/TLS、service manager、测量与运维证据；Piko仍需对同一机器 candidate 完成消费签署。
