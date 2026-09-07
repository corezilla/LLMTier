<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier–Piko Data Plane Interface Control（V0.3）

| 文档字段 | 值 |
|---|---|
| Document ID | llmtier-piko-data-plane-control |
| Document Version | 0.3.0 |
| Status | Approved |
| Project | LLMTier |
| Authority | LLMTier |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier; Piko consumer boundary |
| Approver | LLMTier |
| Approval Date | 2026-09-07 |
| Created Date | 2026-09-07 |
| Last Modified Date | 2026-09-07 |
| STD Version | 0.1.0-draft.18 |
| Template ID | interfaces.control |
| Template Conformance | tailored |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | corezilla/LLMTier |
| Canonical Path | docs/60_interfaces/piko-data-plane-control.md |
| Supersedes | docs/contracts/piko-data-plane-contract-v0.3.md |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本文是当前 Approved consumer-boundary prose authority。原
> docs/contracts/piko-data-plane-contract-v0.3.md 已 Superseded 并仅保留历史；字段级机器 authority
> 始终是 v0.3 OpenAPI。

## 1. 接口目的、范围与双方 authority

本接口使 Piko 把 LLMTier 作为 OpenAI-compatible 模型服务使用。唯一 IR-backed inference 路径是
Runtime → Piko → LLMTier。Piko 拥有 Agent Runtime、受控 credential 使用、canonical Source identity、
durable idempotency obligation 和 recovery adapter；LLMTier 拥有模型服务、Registry、admission、
routing、Invocation ledger 和 canonical response。

Piko 不调用 Management/Observation，不理解 Provider、Account、Deployment、Pool 或 Capacity Group。
LLMTier 不执行 Agent Tool Loop，不接受 Role/IR selector，不提供跨 Service Level fallback。

## 2. 接口注册表

| Interface ID | Provider | Consumer | 类型 | Version | Status |
|---|---|---|---|---|---|
| LT-PKO-RESPONSES | LLMTier | Piko | HTTP POST /v1/responses non-stream | v0.3 | Candidate / not active |
| LT-PKO-MODELS | LLMTier | Piko | HTTP GET /v1/models 与 detail | v0.3 | Candidate / not active |
| LT-PKO-INVOCATION | LLMTier | Piko adapter | HTTP GET /v1/invocations/{invocation_id} | llmtier_recovery_extension_v1 | Candidate / not active |
| LT-PKO-RESPONSE | LLMTier | Piko adapter | HTTP GET /v1/responses/{response_id} | v0.3 | Candidate / not active |
| LT-EMBEDDINGS | LLMTier | Memory/Knowledge Client | HTTP POST /v1/embeddings non-stream | v0.3 | Candidate / separate consumer gate |

Chat Completions、Responses SSE、Chat SSE 和 streaming replay 属于 V0.4；V0.3 必须 fail closed，不能
形成 inactive parallel path。

## 3. 传输与物理边界

接口是 LLMTier HTTP service boundary。Piko 生产调用除 base URL 和 credential 外，还必须发送
canonical Source、Idempotency-Key 和 client request correlation。active replay 与两个 recovery GET
由同一个 Piko adapter 显式处理，不新建第二 Data Plane。

physical Provider、account、pool 和 deployment 完全位于 LLMTier 边界内；Piko 不获得 provider-direct
route 或 credential。

## 4. 数据、命令与 Schema

docs/contracts/openapi/llmtier-v0.3.openapi.json 是 request、response、header、status、typed error 和
Schema 的唯一字段级 authority。model 字段等于 exact、大小写敏感的 service_level_id；Worker 和
Junior 是示例合法 ID，lowercase、alias、Role selector 均无效。

Authorization 绑定服务端 client_id；X-Tier-Source-Id 是已授权 canonical source；
X-Tier-Source-Instance-Id 只用于 correlation/observation；Idempotency-Key 标识 logical invocation；
X-Tier-Client-Request-ID 是 Piko correlation ID。Metadata 最多 16 对，key/value 的最终限制为
64/512 UTF-8 encoded bytes。

## 5. 状态机、顺序和时序

Invocation active 状态为 Pending、Queued、Running；terminal 为 Succeeded、Failed、Cancelled、
UnknownOutcome。首次请求在 backend dispatch 前必须持久化 digest、Invocation 和 dispatch intent。

同 namespace/key/digest 的 active replay 返回 202 InvocationAccepted；Succeeded replay 返回原 endpoint
canonical 200 body；其他 terminal replay 返回 typed non-2xx。Succeeded 通过 response_ref 指向唯一
canonical Response。UnknownOutcome 只能 manual reconcile。

## 6. 错误、timeout、重试、幂等和恢复

idempotency namespace 固定覆盖 canonical client_id、canonical source_id、endpoint/version 和 key；
digest 覆盖 exact Service Level、规范化 body 和影响语义的 headers。同 key 不同 digest 返回不可重试
409 idempotency_conflict，并引用既存 Invocation。

已取得 Invocation ID 时按 recovery_ready、retry_after_ms 和 recovery_disposition 查询；响应头丢失且
无 Invocation ID 时，在 D=24h 内以完全相同 authenticated client、source、body、digest 和 key 重放
原 POST。该 transport recovery 不产生新 Attempt、endpoint、key 或 redispatch 授权。

hidden/无权/不存在统一为 404；保留窗口内暂不可读为 503；能证明过期的同 scope tombstone 为 410。
Failed/Cancelled/UnknownOutcome 不得盲重派。

## 7. 并发、流控、容量与性能

唯一 Seat 单位是 concurrent_invocation。LLMTier admission 同时检查 direct capacity、全部
shared/overlapping groups、Client quota、readiness、blocking reason 和 valid_until。Piko 不预测或覆盖
admission，active replay 的 Retry-After 也不授权新 dispatch。

当前没有 production throughput/latency evidence；静态 contract tests 不能转写为 measured SLO。

## 8. 安全、身份、权限和隔离

recovery scope 是 authenticated client_id + canonical source_id；source_instance_id 不形成恢复
namespace。跨 Client、未授权 Source 和 hidden resource 均 fail closed。canonical Response 不暴露
physical Provider payload、credential 或 routing。

Piko credential 与 Management/Observation credential 分离；日志、error 和 audit 不得泄露 secret 或
跨 Client 内容。

## 9. 版本协商、兼容矩阵与弃用

v0.3 compatibility manifest 记录 contract_status=candidate、runtime_activation=false。固定 capture
baseline 包括 Pi source 9767ba275f3e9a5ee0f5c5342249b629ab1b2282、pi-coding-agent 0.85.1、
pi-ai 0.85.1、openai 6.40.0、provider llmtier 和 adapter piko-llmtier-responses-v0.3。

这些版本只冻结 conformance matrix。破坏兼容性的变化必须使用新 Service Level ID 或 API major；
不得 silent fallback 或把 V0.4 surface 暗中加入 v0.3。

## 10. Contract fixture、验证与证据

- 字段 authority：docs/contracts/openapi/llmtier-v0.3.openapi.json。
- activation 状态：docs/contracts/compatibility-manifest-v0.3.json。
- fixtures：data-plane-openapi-fixtures、recovery-protocol-fixtures、
  idempotency-forgotten-key-options、authorization-scope-fixtures、
  deferred-surface-fail-closed 和 metadata-utf8-byte-fixtures。
- 静态/语义验证：tests/test_contract_semantics_v03.py、tests/test_contract_consistency.py。
- production evidence：Piko pinned adapter capture、lost-response/restart、UnknownOutcome 和真实 LLMTier
  endpoint 尚未完成，状态为 BLOCKED/NOT_RUN。

## 11. 未决项与双方批准

LLMTier Owner 已审核提供方事实，Piko reviewer 已在 `P-20260907-e009921eda0a` 接受其
consumer/recovery obligations。本文的 Approved 状态不请求 RAG publication 或 Runtime Activation。
