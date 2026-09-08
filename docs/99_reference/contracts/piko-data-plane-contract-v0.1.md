# llmtier 面向 Piko 的 Data Plane 契约提案 v0.1

Last Updated: 2026-09-06 14:15:00 +08:00

Status: Candidate；等待 Piko pinned SDK 行为证据与三方 review，不是冻结契约

## 1. 边界

Piko 只把 llmtier 视为 OpenAI-compatible 云模型服务。Piko 提供 `base_url`、在受控 Secret boundary 内解析的 Bearer credential，以及 exact `model=service_level_id`。Piko 不调用 Management/Observation API，也不理解 Provider、Account、Backend Pool、capacity group 或 physical model。

llmtier 只返回模型 output/tool call，不执行 Piko 的 file/process/git/browser Tool Loop。

## 2. Candidate surface

| Method | Path | 状态 | 用途 |
| --- | --- | --- | --- |
| POST | `/v1/responses` | Required | 唯一主 generation surface |
| GET | `/v1/models` | Required | 返回当前 credential 可见的 exact service level |
| GET | `/v1/models/{service_level_id}` | Required | 校验单一 exact service level |
| GET | `/v1/invocations/{invocation_id}` | Candidate extension | response/stream 丢失后的 scoped outcome query |
| POST | `/v1/chat/completions` | Conditional | 仅在 pinned Pi SDK 实测要求时启用；不是 fallback |

未列出的 endpoint 返回 `404 not_found`；已知但未启用的 endpoint 返回 `unsupported_endpoint`，不得透传到 Provider。

## 3. 请求 identity

以下名称尚待 Piko/Slinky 回信冻结；实现前作为 candidate：

- `Authorization: Bearer <resolved credential>`：认证 credential，不进入日志或邮箱 fixture。
- `Idempotency-Key`：Piko 每个 participant Tier invocation 的稳定 key。
- `X-Client-Request-Id`：Piko 生成的请求 correlation ID。
- `X-Tier-Source-Id`：canonical Source identity。
- `X-Tier-Source-Instance-Id`：当前 Piko instance identity。

服务端从 credential binding 得到 `client_id`，不能信任客户端自报 `client_id`。Source/Instance 必须在 credential scope 内注册或授权；缺失、越权或伪造 fail closed。

## 4. `/v1/responses`

最低 request fields：

- `model: string`，必填，大小写敏感，必须是当前 Client 有权访问的 `service_level_id`。
- `input: string | input_item[]`，必填。
- `instructions`、`tools`、`tool_choice`、`text.format`、`max_output_tokens`、`temperature`、`top_p`、`reasoning`、`parallel_tool_calls`、`stream`、`metadata`：仅按 compatibility manifest 接受。

字段处理：

- manifest 标记 supported：校验后接受。
- 已知但当前 service level 不支持：`capability_not_supported`。
- 已知但本版本未实现：`unsupported_parameter`。
- 未知字段：`unknown_parameter`，不得静默忽略。

Non-stream response 的 `id` 同时是 response identity；响应必须带 `x-tier-invocation-id`。`model` 回显请求的逻辑 service level，不泄漏 physical model。Usage 无证据时字段缺失或标记 unknown，不补零。

## 5. Tool 与 structured output

`tools` 仅接受 `type=function`。每个 Tool schema、`tool_choice`、parallel support、call ID 和 result correlation 必须由 manifest 声明。llmtier 不执行 Tool；Piko 执行并把 Tool result 作为后续 input 交回。

`text.format=json_schema` 的支持 keyword、strictness、refusal 和 incomplete 语义必须由 manifest/service-level override 声明。Provider 原生支持声明不能代替 llmtier contract test。

## 6. Streaming

SSE 事件的精确集合等待 pinned Pi SDK capture 后冻结。无论事件名如何，必须满足：

- 连接前完成 admission，不能无限占用连接等待 capacity。
- Tool call argument delta 可按 call ID 有序重组。
- 正常结束有且只有一个 terminal event/marker。
- disconnect 后服务端按 manifest policy cancel 或继续，并持久化 terminal/unknown outcome。
- 断流不代表 Failed；Client 通过 invocation ID 查询，无法确认时保留 `UnknownOutcome`。

## 7. Error 与 retry

统一 error body 至少包含 `error.type`、`error.code`、`error.message`、`error.param`、`error.retryable`；响应带 request/invocation correlation header。

- `400`：invalid/unknown/unsupported parameter。
- `401`：missing/invalid credential。
- `403`：credential 有效但 Source/Service Level 越权。
- `404`：model 或 scoped invocation 不存在；不存在与无权访问不可区分。
- `409`：idempotency conflict。
- `422`：请求合法但 capability 不支持。
- `429`：admission/capacity/quota，按可用证据返回 `Retry-After`。
- `5xx`：llmtier/backend failure；是否 retry 由 typed code 和 deadline 决定。

Piko 不因网络异常自动切换 endpoint、service level 或 physical Provider。

## 8. Outcome query candidate

`GET /v1/invocations/{invocation_id}` 归属 Data Plane recovery extension，不授予 Observation authority。它只返回当前 credential/client/source 可见的单一 invocation：`Queued | Running | Succeeded | Failed | Cancelled | UnknownOutcome`、response ref、usage evidence、typed error 和 record version；不返回 physical routing。

如果 Client 在收到 invocation ID 前丢失 acknowledgment，需以 `Idempotency-Key` 重发同一 digest，由幂等语义返回既有 invocation；不同 digest 返回 `409 idempotency_conflict`。Retention 必须覆盖双方冻结的恢复窗口。

该方案需要 Piko/Slinky review。若不接受或无法验证，Piko 必须保留 `UnknownOutcome`，不得调用 Observation API 或盲目重派。

## 9. 证据状态

- 设计拟支持：本文件列出的 Candidate surface。
- 已实现：当前仅有旧 Tier 私有 HTTP API 和第一阶段独立配置/状态边界。
- 已验证：独立 package/import 与 runtime boundary tests；尚无 OpenAI/Pi SDK、Tool、stream 或 outcome conformance 证据。

