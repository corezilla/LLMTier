# llmtier 面向 Piko 的 Data Plane 契约提案 v0.3

Last Updated: 2026-09-06 15:34:00 +08:00

Status: Candidate；回应 Slinky M1–M3，仍等待 Piko pinned SDK capture

## 1. 恢复读取闭环（M1）

`GET /v1/invocations/{invocation_id}` 继续是 `llmtier_recovery_extension_v1`，返回最小 Invocation 状态。只有 `Succeeded` 才返回唯一 `response_ref=/v1/responses/{response_id}`。

v0.3 新增候选读取面：

- `GET /v1/responses/{response_id}`。
- 响应 Schema：`schemas/llmtier-recovery-v0.3.schema.json#/$defs/ResponseRetrievalView`。
- 授权边界与 Invocation 相同：authenticated `client_id + canonical source_id`；`source_instance_id` 不隔离重启恢复。
- hidden、无权或不存在统一 `404 not_found`；同 scope tombstone 可证明已过期时为 `410 response_record_expired`；保留期内 Backend 暂不可读取为 `503 response_temporarily_unavailable`，不得重新 dispatch。
- Response active retention 不短于关联 Invocation active retention；response tombstone 不短于 Invocation tombstone。Prompt/output/usage 的具体 retention 与 privacy policy 仍待冻结。
- 返回 body 是 llmtier 持久化的 canonical Responses projection，不直接暴露 physical provider payload。

这两个 GET surface 都要求 Piko adapter 显式调用；仅替换标准 SDK 的 `base_url` 不会自动获得恢复闭环。

`POST /v1/chat/completions` 仍是 conditional。只有 Piko 明确验证 Chat result 到 canonical Responses projection 的确定映射后，Chat invocation 才能发布上述 `response_ref`；未验证时 Chat recovery activation 必须 fail closed，并保留 `UnknownOutcome`。不能无条件把 Chat result 指向 Responses。

## 2. 首次、重复与 lost-response 协议（M3）

### 2.1 Non-stream Responses

- 首次请求：先持久化 idempotency/invocation/dispatch intent，再执行 Backend；正常完成返回 `200 ResponseRetrievalView`。
- 首次 HTTP response 丢失：Piko 以同 namespace、key、digest 重试。
- 重试命中 Pending/Queued/Running：`202 InvocationAccepted`，同时返回 `Location: /v1/invocations/{id}` 和 `X-LLMTier-Invocation-Id`；dispatch count 为零。
- 重试命中 Succeeded：`200 ResponseRetrievalView`，dispatch count 为零。
- 首次执行以 Failed 结束：返回适用的非 2xx `Error` body，并在 header 携带 `X-LLMTier-Invocation-Id`；ledger 保留原始 error evidence。
- 重试命中 Failed/Cancelled/UnknownOutcome：返回 `200 InvocationView` 作为自定义 terminal/recovery view，不产生新 attempt；Piko adapter 必须按其中状态处理，不能把 HTTP 200 等同推理成功。
- 202 与 Invocation extension 都是自定义行为；在 Piko pinned SDK/adapter capture 通过前只能标为 conditional/unverified。

因此 Piko 不需要在首次丢包前取得 invocation ID：同 key 重试先命中 ledger，202 body/header 再暴露已存在的 ID。若 ledger evidence 不足，则返回 `UnknownOutcome`，不能重新 dispatch。

### 2.2 Streaming

首次 stream 候选为 `200 text/event-stream`，响应 header 可携带 `X-LLMTier-Invocation-Id`，事件序列仍待 Piko capture。v0.3 不承诺 active stream 的自动 reattach、SSE replay 或标准 SDK 对 202 的处理；同 key active retry 必须零 dispatch 并 fail closed。stream replay contract 未验证前，manifest 不允许启用 streaming recovery。

### 2.3 Chat Completions

Chat 首次/重复的 body 与 event 不能沿用 Responses Schema。必须先有 pinned SDK capture、Chat response/event Schema 和显式 canonical normalization 规则；否则 Chat endpoint 与 recovery 均不激活。

Machine-readable case specification：`fixtures/v0.3/recovery-protocol-fixtures.json`。它验证协议分支定义，不代表 SDK 执行证据。

## 3. Idempotency 完全删除后的不可区分性（M2）

若 active record 和 tombstone 均完全删除，只看 `client_id + source_id + endpoint version + key + digest`，历史 key 重放与首次使用在可观察状态上相同。有限本地状态不能同时“完全遗忘”又可靠拒绝旧 key；调用者声明 new Attempt 不能修复这一点。

v0.3 只提出取舍，不冻结新机制：

| 方案 | 可执行保证 | 代价/边界 |
| --- | --- | --- |
| A：永久或可压缩 key index | 完全删除 payload 后仍可拒绝旧 key | 新持久索引，容量长期增长；属于新机制 |
| B：Server-issued epoch | 先拒绝过期 epoch，再查 key | 新 token/epoch rotation 协议；属于新机制 |
| C：有限保证窗口 | 只在公开 retention 窗口内保证 exactly-once；完全删除后不能区分 | 不新增机制，但必须收窄保证并要求 Client retry deadline 小于窗口 |

在契约责任方选择 A/B/C 且给出 retention/rotation 数值前，idempotency recovery 的 activation requirement 不满足；实现不得把完全删除后的重放当作“已证明安全”。Fixture：`fixtures/v0.3/idempotency-forgotten-key-options.json`。

## 4. 证据状态

- Planned：GET response、POST replay envelope、stream/chat recovery 与 idempotency retention policy。
- Implemented：Schema、manifest、fixtures 和静态语义检查；没有 production route/ledger。
- Verified：JSON/Schema 自检和本地 contract tests；没有 Piko SDK、服务或 crash execution evidence。
