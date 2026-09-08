# llmtier 面向 Piko 的 Data Plane 契约提案 v0.2

Last Updated: 2026-09-06 15:03:00 +08:00

Status: Candidate；回应 Slinky C4–C7，等待 Piko pinned SDK evidence

## 1. Surface 与标准兼容边界

`POST /v1/responses` 是 required 主 generation surface；`GET /v1/models` 和 `GET /v1/models/{service_level_id}` 提供 exact model 校验。`POST /v1/chat/completions` 只有 pinned Pi SDK 实测必需时启用，且绝不是 Responses 失败后的 fallback。

`GET /v1/invocations/{invocation_id}` 是明确标记的 `llmtier_recovery_extension_v1`，不是 OpenAI 标准 SDK 自动调用能力。Piko 若采用它，必须在 Agent Runtime adapter 中显式调用并纳入自己的 recovery evidence；只替换 `base_url` 不会自动获得恢复行为。

## 2. Authentication 与 visibility

Header 名称仍待三方冻结，candidate 为 `Authorization`、`Idempotency-Key`、`X-Client-Request-Id`、`X-Tier-Source-Id`、`X-Tier-Source-Instance-Id`。

Credential 解析出 authoritative `client_id` 与允许的 Source scope。Source scope 越权返回 `403 source_scope_forbidden`。Model 不存在和无权访问统一返回 `404 model_not_found`，不泄漏 hidden catalog。

Invocation 默认以 `client_id + source_id` 为读取边界；`source_instance_id` 是 correlation 而非恢复隔离边界。Piko 重启后，新 instance 只要持有同一 Client credential、同一 Source identity 和 `invocation:read:source` scope，即可读取旧 instance 创建的 Invocation。其他 Source/Client 统一 `404 not_found`。

## 3. Invocation ledger 与状态机（C4）

Machine-readable Schema：`schemas/llmtier-contracts-v0.2.schema.json#/$defs/InvocationView`。

合法状态：

```text
Pending -> Queued -> Running -> Succeeded | Failed | Cancelled | UnknownOutcome
Pending -> Failed | Cancelled
Queued  -> Failed | Cancelled | UnknownOutcome
Running -> Failed | Cancelled | UnknownOutcome
UnknownOutcome -> Succeeded | Failed | Cancelled
```

除 `UnknownOutcome` 的 evidence-backed reconciliation 外，terminal 状态不可覆盖。每次状态/usage/error/response-ref 变化递增 `record_version` 并追加审计事件。

查询结果：

- Authorized active/terminal record：`200` + `InvocationView`。
- Record 状态为 `UnknownOutcome`：仍是 `200`，并保留 recovery obligation；不能混同 not-found。
- 不存在或无权访问：统一 `404 not_found`。
- Active record 已清理但同 Client/Source tombstone 仍在：`410 invocation_record_expired`，不允许重派旧 key。
- Tombstone 也过期、无法证明旧 key 安全：该 key 仍不得被当前 namespace 重用；Client 必须以新的业务 Attempt/new key 走显式决策。

`Succeeded` 必须给出唯一 `response_ref=/v1/responses/{response_id}`；该 response 使用同一 Client/Source scope 读取，内容 retention 不得短于 Invocation active retention。敏感字段、physical routing、credential、prompt/output retention 仅按 policy 返回，默认 recovery view 不包含它们。

Observation `/tier/v1/invocations/{id}` 和本 extension 是同一 ledger 的两个授权 projection，不得双写或维护第二 recovery store。

## 4. Idempotency 与 lost acknowledgment（C5）

命名空间：`authenticated client_id + canonical source_id + endpoint version + Idempotency-Key`。

Digest：`sha256(RFC8785(request_body_after_schema_validation))`。字段范围是 Schema 允许的完整 request body，包括 `model`、input、instructions、tools/tool choice、structured-output、sampling、reasoning、parallel flag、stream、metadata；不包含 transport/correlation headers、credential 或服务端生成字段。只有 Schema 明确定义的 default 才可在 digest 前 materialize；v0.2 Schema 没有 default，因此 omitted 与显式值保持不同。Endpoint version 位于命名空间中，因此不同 endpoint 不共享 key。

原子边界：

1. 在一个 durable transaction 中，以 namespace unique constraint 写入 `Pending` idempotency record、digest、invocation ID、request reference 和 created time。
2. transaction commit 后才能创建 Backend dispatch intent。
3. Backend dispatch intent 与 attempt ID 也必须先持久化，再执行外部调用。
4. 并发重复由 unique constraint 串行化；loser 读取 winner record，不 dispatch。

重复响应：

- Same key + same digest + Pending/Queued/Running：返回 `202` 和同一 invocation ID/status。
- Same key + same digest + Succeeded：返回既有 response/ref，`200`。
- Same key + same digest + Failed/Cancelled/UnknownOutcome：返回既有 terminal view；不得自动创建 Backend attempt。
- Same key + different digest：`409 idempotency_conflict`。
- Key tombstone 命中：`409 idempotency_key_expired`，dispatch count 必须为零。

Crash recovery：如果 durable dispatch evidence 不足以证明 Backend 未接收，不能自动重派；转为 `UnknownOutcome` 或显式 recovery required。Idempotency active retention 覆盖 Client/SDK/Tier 最大 retry window；key tombstone retention 覆盖 Provider side-effect/reconciliation 安全窗口。具体时长仍待 SLO 冻结，但 retention 不足或不可确认永远不能被解释为“安全重派”。

SDK automatic retry、Piko retry 和 llmtier internal Backend retry 必须计入同一请求 deadline/retry budget；每个内部 attempt 记录证据，不能切换 endpoint 或 service level。

正反 fixture：`fixtures/v0.2/idempotency-recovery-fixtures.json`。

## 5. Error/Manifest（C6）

Error Schema：`schemas/llmtier-contracts-v0.2.schema.json#/$defs/Error`。Source scope 越权用 403；hidden model 用一致 404。Manifest 的 endpoint support 必须是 `planned | conditional | verified | disabled`；只有 `verified` 且 activation requirements 全满足的 surface 才能进入 readiness 的可接入声明。

Manifest v0.2 补充 request/schema refs、字段状态、Tool/structured output、stream contract、error codes、size/token limits、SDK matrix、activation requirements。所有 pending/planned 项运行时必须 fail closed。

## 6. 证据状态

- Planned：本文件定义的 surface、ledger、idempotency 和 manifest candidate。
- Implemented：独立 config/state 与纯模型 registry；Data Plane route/ledger 尚未实现。
- Verified：独立 runtime tests 与契约静态/fixture 结构检查；尚无 service execution result。
