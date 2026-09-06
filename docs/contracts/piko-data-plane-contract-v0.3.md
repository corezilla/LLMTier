# LLMTier 面向 Piko 的 Data Plane 契约提案 v0.3

Last Updated: 2026-09-06

Status: Candidate Amendment 2；已纳入 Piko pinned baseline/capture，scope 冲突待 Slinky/用户裁决，未激活

## 1. Authority 与唯一调用路径

Piko 只把 LLMTier 视为 OpenAI-compatible 模型服务。唯一 IR-backed inference 路径是 `Runtime -> Piko -> LLMTier`。Piko 提供受控 credential、canonical Source identity、稳定 idempotency key，并以 exact、大小写敏感的 `model=service_level_id` 调用；`Worker` 与 `Junior` 是示例合法 ID，`worker`、`junior`、alias 或 fallback selector 都不是同一 ID。

Piko 不调用 LLMTier Management/Observation API，不理解 Provider、Account、Deployment、Pool 或 Capacity Group。LLMTier 不执行 Piko 的 Agent Tool Loop，也不接受 Role/IR selector 或跨 Service Level fallback。

## 2. 唯一 V0.3 Data Plane surface

以下是一个统一的 V0.3 scope，不存在“Responses-only”或其他并行兼容路径：

| Method | Path | V0.3 责任 | Stock OpenAI SDK 边界 |
| --- | --- | --- | --- |
| POST | `/v1/responses` | non-stream 与 SSE | 首次标准成功/错误及 SSE 形状必须由 pinned capture 验证；active replay `202` 必须由 Piko recovery adapter 处理 |
| POST | `/v1/chat/completions` | non-stream 与 SSE | 首次标准成功/错误及 SSE 形状必须由 pinned capture 验证；不是 Responses fallback |
| POST | `/v1/embeddings` | 标准 embedding request/response | 首次和 completed replay 保持标准 body；恢复扩展仍需 adapter |
| GET | `/v1/models` | credential 可见的 exact Service Level 列表 | 来自与 admission/Observation 相同的 Registry；目标是 stock SDK models API |
| GET | `/v1/models/{service_level_id}` | exact Service Level 查询 | 大小写敏感；不存在或大小写不符为 `model_not_found` |
| GET | `/v1/invocations/{invocation_id}` | `llmtier_recovery_extension_v1` | 非 OpenAI 标准 endpoint，必须由 Piko recovery adapter 显式调用 |
| GET | `/v1/responses/{response_id}` | canonical Responses 恢复读取 | 只用于 Responses；恢复策略和 `202` 仍由 Piko adapter 编排 |

“stock SDK”只描述标准 endpoint 的请求/响应形状。Piko 生产调用还必须配置 LLMTier 要求的 Source/idempotency headers；仅替换 `base_url/api_key` 不会自动处理 active replay `202`、Invocation 查询、lost-response recovery 或 `UnknownOutcome`。所有标准 surface 在 pinned SDK/provider adapter 的真实 capture 通过前保持 candidate，但不得从 V0.3 scope 删除或另建降级路径。

未列出的 endpoint 返回 `404 not_found`；列入但尚未通过 activation gate 的能力整体不可对生产声明为 supported，不能静默透传到 Provider。

## 3. Service Level Registry

LLMTier 是 Service Level catalog authority。`GET /v1/models`、`GET /v1/models/{id}`、`/tier/v1/service-levels`、admission 和 Compatibility Manifest 必须读取同一个 authoritative Registry。

- `service_level_id` exact、大小写敏感且唯一；禁止 lowercase normalization、alias、Role selector 和跨等级 fallback。
- Provider/account/pool mapping 与同等级 Backend override 属于 LLMTier，可以在 Contract/SLO 不变时替换 physical mapping 而不改变 ID。
- 破坏兼容性的语义变化必须使用新 Service Level ID 或新 API major。
- catalog version、强 ETag、`effective_at`、`valid_until`、唯一 ID、capacity membership 和 manifest 必须通过三方 Contract Test 才能激活。

## 4. Identity、请求与 Schema

- `Authorization: Bearer <credential>`：服务端由 credential binding 得到 `client_id`，不得信任请求自报 Client。
- `X-Tier-Source-Id`：canonical、已授权的稳定 Source identity。
- `X-Tier-Source-Instance-Id`：运行实例 correlation，不作为重启恢复隔离边界。
- `Idempotency-Key`：同一 logical invocation 的稳定 key。
- `X-Client-Request-Id`：Piko correlation ID。

Responses 的 idempotency namespace 冻结为：

```text
llmtier-responses/v0.3
  + canonical client_id
  + canonical source_id
  + Idempotency-Key
```

canonical request digest 至少覆盖 exact `service_level_id`、完整规范化请求 body 和所有影响推理语义的 header。相同 namespace/key 不同 digest 返回不可重试的 `409 idempotency_conflict`。Piko 在首次 dispatch 前持久化 key、digest、invocation reference 和 recovery obligation；transport retry、agent-level retry 与 restart recovery 必须复用同一 key。

Responses、Chat Completions、Embeddings、Models 和 Error 的候选 Schema 位于 `schemas/llmtier-data-plane-v0.3.schema.json`；recovery Schema 位于 `schemas/llmtier-recovery-v0.3.schema.json`。未知参数拒绝；Metadata 最多 16 对，key/value 权威限制分别为 64/512 UTF-8 encoded bytes，不得按 code point 放宽或静默截断。

Piko V0.3 capture 基线：Pi source `9767ba275f3e9a5ee0f5c5342249b629ab1b2282`；`@earendil-works/pi-coding-agent@0.85.1`；`@earendil-works/pi-ai@0.85.1`；`openai@6.40.0`；provider=`llmtier`；adapter=`piko-llmtier-responses-v0.3`。这些版本只冻结 conformance matrix，不表示 production activation。

## 5. 首次、重复与 lost-response 协议

LLMTier 在调用 Backend 前持久化 idempotency record、Invocation 和 dispatch intent。相同 namespace/key/digest 永不产生第二次 dispatch；相同 key、不同 digest 返回 `409` OpenAI-compatible Error envelope。

| 情形 | POST 返回 | dispatch |
| --- | --- | --- |
| 首次成功 | endpoint 对应的标准 `200` body；SSE 为 `200 text/event-stream` | 一次 |
| active replay：Pending/Queued/Running | `202 InvocationAccepted`，带 `Location`、`X-LLMTier-Invocation-Id` 与 `Retry-After` | 零次 |
| completed replay：Succeeded | endpoint 对应的原标准成功 body；不得换成 InvocationView | 零次 |
| terminal replay：Failed | `502 TerminalErrorEnvelope`，code=`invocation_failed`、`retryable=false` | 零次 |
| terminal replay：Cancelled | `409 ErrorEnvelope`，code=`invocation_cancelled` | 零次 |
| terminal replay：UnknownOutcome | `503 ErrorEnvelope`，code=`invocation_outcome_unknown`、`retryable=false` | 零次 |

Failed/Cancelled/UnknownOutcome 的详细状态只通过 `GET /v1/invocations/{id}` 查询。POST 的 HTTP 200 只表示 endpoint 的标准成功结果，绝不返回 `InvocationView`。

一旦 Invocation 已建立，active `202` 与 terminal replay 非 2xx 都必须返回 `Location: /v1/invocations/{id}` 和 `X-LLMTier-Invocation-Id: {id}`；active `202` 还必须返回 `Retry-After`。请求在建立 Invocation 前即因 auth/schema/model/digest conflict 失败时不得伪造 Invocation header 或 Location。Headers Schema 为 `llmtier-recovery-v0.3.schema.json#/$defs/RecoveryHeaders`，terminal body 为 `llmtier-data-plane-v0.3.schema.json#/$defs/TerminalErrorEnvelope`。

active replay 的 `202` 和两个 recovery GET 都是显式扩展；Compatibility Manifest 必须标记 `explicit_piko_recovery_adapter_required=true`，并由 pinned adapter capture 验证。SDK 不接受 `202` 时由 adapter 截获和查询，不建立另一条 Data Plane。

## 6. Invocation 与 response recovery

Invocation 状态为 `Pending | Queued | Running | Succeeded | Failed | Cancelled | UnknownOutcome`。只有 Responses 的 `Succeeded` Invocation 发布唯一 `response_ref=/v1/responses/{response_id}`；Chat/Embeddings completed replay 由同一 ledger/canonical result store 返回原 endpoint 标准 body，不伪装为 Responses object。

`GET /v1/invocations/{id}` 的 readiness 信号是机器字段而不是 HTTP 状态猜测：

- Pending/Queued/Running：`recovery_ready=false`、`recovery_disposition=wait`、`retry_after_ms>=0`。
- Succeeded Responses：`recovery_ready=true`、`recovery_disposition=retrieve_response`。
- Succeeded Chat/Embeddings：`recovery_ready=true`、`recovery_disposition=replay_same_request`，同 key/digest replay 返回保存的标准成功 body，零 dispatch。
- Failed/Cancelled：`recovery_ready=true`、`recovery_disposition=raise_terminal_error`。
- UnknownOutcome：`recovery_ready=true`、`recovery_disposition=manual_reconcile`，不得自动重派。

Recovery scope 是 authenticated `client_id + canonical source_id`。hidden、无权或不存在统一为 `404 not_found`；同 scope tombstone 能证明过期时返回 `410`；保留期内暂不可读取为 `503`，且不得重新 dispatch。Canonical Response 不暴露 physical Provider payload。

## 7. M2-C 有限保证窗口

V0.3 单一选择是 C：有限保证窗口，不新增永久索引或 epoch/token 协议。

- 最短保证窗口 `W=168h`，从 Invocation terminal 时刻开始，由 active record 与 content-free digest/tombstone 的连续存在共同保证。
- safety margin `M=24h`，其中允许的 clock skew 最多 5 分钟，其余作为 transport/service recovery safety；约束为 `max_client_retry_deadline <= W-M = 144h`。
- 产品侧 Piko 自动 retry/recovery deadline `D=24h`，满足 `D <= 144h`；若 Piko 无法满足，必须在实现前提出一个唯一替代数值，不得运行时自动降级。
- active idempotency record 至少保留到 Invocation terminal。
- terminal 后 content-free digest/tombstone 的去重保证至少 7 天。
- Invocation terminal view 与 canonical Responses 从 terminal 起至少保留 7 天。
- Prompt/output privacy retention 可独立配置，但不能使 content-free digest/tombstone 提前消失。
- 完全删除后不再保证识别历史 key；V0.3 不声称无限期 exactly-once。

## 8. Streaming、Chat 与 Embeddings

Streaming、Chat 和 Embeddings 都在唯一 V0.3 scope 内，但 production activation 取决于 Piko pinned capture：

- SSE 在连接前完成 admission；delta 可重组；有且只有一个 terminal marker；断流不是自动 Failed。
- active stream replay 不自动 reattach，不宣称 SSE replay；adapter 查询原 Invocation，且不得 redispatch。
- Chat 使用 Chat 自身标准 response/event Schema；不是 Responses fallback，也不需要伪造 Responses projection。
- Embeddings completed replay 返回原 Embeddings response；不得跨 Service Level 或 Provider-direct 重试。

Piko 基于上述固定 Pi baseline 的 mock capture 已证明：内建 `openai-responses` 固定 `stream:true`；不识别 active `202 InvocationAccepted`；旧 terminal `200 InvocationView` 会报缺少 terminal event；typed `409` 被压成普通 provider error；lost response 会触发默认最多 3 次 agent-level retry。因此 V0.3 recovery 必须由自定义 adapter 执行，不能退回内建 adapter。Node `22.22.3` 对 `@earendil-works/gondolin@0.12.0` 的 `>=23.6.0` engine warning 尚待完整 Piko runtime matrix 处理。

Piko 已命名 Responses adapter 为 `piko-llmtier-responses-v0.3`，计划经 `registerProvider(..., streamSimple)` 接入并自行执行 non-stream POST、Invocation/Response GET、typed status 和 durable recovery；这是同一 Piko->LLMTier 路径的 adapter，不是第二 inference path。

Piko 请求把 Streaming/Chat normalization 延至 V0.4；Slinky Amendment 1 则要求 V0.3 保持 Responses+Chat+Embeddings+Models+SSE 的唯一 surface。该 scope 冲突超出 LLMTier 单方裁决权：当前 manifest 保留 Slinky 要求的统一 candidate surface，但整体 activation=false；在 Slinky/用户明确 scope amendment 前，不创建 Responses-only 分支，也不把 Chat/SSE 作为 fallback。

## 9. Activation evidence

V0.3 激活要求至少包括：production implementation commit；正负 Contract Test；Management API/UI 证据；同一 Registry 驱动 Models/Observation/admission；multi-client/source isolation 与公平性；Capacity semantic validator 生产接线；Piko pinned SDK/adapter 对首次 200、active 202、terminal error、lost response、UnknownOutcome、Chat/Embeddings/SSE/Models 的真实 capture；以及旧 embedded Tier、Role routing、Agent backend、Provider-direct path 删除扫描。

当前 Schema、fixtures 和本地测试只属于 candidate artifact evidence，不代表 endpoint、ledger、SDK 或 runtime 已实现。
