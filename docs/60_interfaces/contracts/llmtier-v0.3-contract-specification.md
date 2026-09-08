<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Contract Specification

| 文档字段 | 值 |
|---|---|
| Document ID | llmtier-v0.3-contract-specification |
| Document Version | 0.3.0 |
| Status | Approved |
| Project | LLMTier |
| Authority | LLMTier |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | 2026-09-07 |
| Created Date | 2026-09-07 |
| Last Modified Date | 2026-09-08 |
| STD Version | 0.1.0-draft.18 |
| Template ID | contracts.specification |
| Template Conformance | tailored |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | corezilla/LLMTier |
| Canonical Path | docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本文只建立 V0.3 machine contract 的 scope、authority、演进和验证索引，不转写字段定义。
> interfaces/openapi/llmtier-v0.3.openapi.json 与
> interfaces/compatibility/compatibility-manifest-v0.3.json 原位保持各自机器 authority。

## 1. Contract scope 与 authority

OpenAPI 3.1 文件是 Data Plane、Observation 和 Management 的 method/path、header、parameter、
request/response、status、typed error 与 Schema 唯一字段级 authority。compatibility manifest 是
capability support、SDK matrix、overall contract status 和 runtime activation 的机器 authority；
当前 overall.contract_status=candidate 且 overall.runtime_activation=false。

三份 interface candidate 解释双方职责和 failure/recovery rationale，不得覆盖机器字段。fixtures 与
tests 是 oracle/evidence，不能取代 Contract 定义。v0.1/v0.2 文件只作 historical/provenance。

## 2. Operation / Message / Event Catalog

| ID | Kind | Producer | Consumer | Sync/Async | Idempotency |
|---|---|---|---|---|---|
| LT-OP-RESPONSES | HTTP operation | LLMTier | Piko | sync + explicit recovery | required logical invocation key |
| LT-OP-EMBEDDINGS | HTTP operation | LLMTier | Memory/Knowledge Client | sync | OpenAPI contract |
| LT-OP-MODELS | HTTP operation | LLMTier | Piko/authorized clients | sync | read-only |
| LT-OP-DP-RECOVERY | HTTP operation | LLMTier | Piko adapter | sync polling/read | original invocation key/identity |
| LT-OP-OBSERVATION | HTTP operations | LLMTier | Slinky | sync read | read-only, ETag where declared |
| LT-OP-MANAGEMENT | HTTP operations | LLMTier | LLMTier Admin | sync + async AdminJob | POST key; PATCH If-Match/version |

完整 operationId 与 path catalog 直接引用 OpenAPI paths，不在 Markdown 复制一份可漂移列表。

## 3. Request、Response、Event 与数据对象

OpenAPI components 是所有 DTO 和 Schema ref 的唯一字段定义，包括 ResponsesRequest/Response、
EmbeddingRequest/Response、Model/List、InvocationAccepted/View/Page、CapacitySnapshot、
ReadinessView、ServiceLevelView/Page、CompatibilityView、Management resource/page、AdminJob、
ErrorEnvelope 和 TerminalErrorEnvelope。

Metadata 的 Schema maxLength 之外还必须执行 64/512 UTF-8 encoded-byte validator。canonical
Service Level ID exact、大小写敏感；Client/Source identity 由 authenticated binding 和授权决定。
示例不能放宽 required、additionalProperties、enum、range 或 encoded-byte 约束。

## 4. 状态、错误和 blocker catalog

Invocation active 状态仅 Pending、Queued、Running；terminal 仅 Succeeded、Failed、Cancelled、
UnknownOutcome。POST active replay 是 202 InvocationAccepted；Succeeded replay 是原 canonical 200
body；Failed 为 502 invocation_failed；Cancelled 为 409 invocation_cancelled；UnknownOutcome 为
503 invocation_outcome_unknown 且 retryable=false。

通用错误包括 model_not_found、unsupported_endpoint、unsupported_feature、not_found、
idempotency_conflict、source_error、contract_mismatch、client_quota_unknown 和 version_conflict。
具体 HTTP mapping、envelope 和 header 以 OpenAPI 为准。

runtime blockers 包括 implementation、durable ledger/retention、Registry 多分面 wiring、
capacity semantic validator、multi-client isolation/fairness、Management/API UI、Piko adapter、
Embeddings consumer 和 production SLO evidence 缺失。

## 5. 幂等、并发、事务与一致性

Responses 在 backend dispatch 前事务性持久化 request digest、Invocation、dispatch intent 和 recovery
obligation。同 namespace/key/digest 的所有 replay additional dispatch=0；同 key/different digest
为不可重试 conflict。

Management create/action POST 使用 Idempotency-Key；PATCH 同时使用 If-Match 和 expected_version；
async mutation 返回 AdminJob。Registry/manifest/Models/Observation/admission 对 exact ID、catalog
version/ref 和 capability semantics 一致，但各 endpoint ETag 只绑定自身 representation。

## 6. Pagination、filter、ordering 与 retention

list operations 使用 limit、cursor 与 PageMeta.next_cursor；允许的 filter、group_by 和 ordering 由
各 OpenAPI operation 定义。unknown/partial Usage 数值保持 null，不得补零。

M2-C 固定 W=168h、M=24h、D=24h。active record 保留到 terminal；terminal 后 content-free
digest/tombstone、Invocation terminal view 和可恢复 canonical Response 至少 168h。privacy retention
不能破坏这些下限，短配置无效并阻断 activation。

## 7. 身份、权限、Secret 与多项目隔离

Authorization 绑定 canonical client_id；X-Tier-Source-Id 必须被该 Client 授权；
source_instance_id 只用于 correlation/observation/audit。Data Plane recovery scope 固定为
authenticated client + canonical source。Observation multi-source aggregate 不扩大 recovery scope。

Management credential 与 Data Plane/Observation 分离。Account secret 只写不读；Client credential
仅在创建时返回一次，之后只暴露 fingerprint/status。所有 list/detail/UI/log/audit 禁止 secret 和
跨 Client 内容。

## 8. 版本、兼容性与迁移

当前 contract version 是 0.3 candidate Amendment 4。Scope B 只含 Responses non-stream、Embeddings
non-stream、Models、Invocation/Response recovery、Observation 和 Management。Chat/SSE/streaming
属于 V0.4，不能以 alias、translation、provider passthrough 或 inactive endpoint 进入 V0.3。

破坏兼容性的 Service Level 语义使用新 ID 或 API major。compatibility manifest 必须与 OpenAPI、
Registry、fixtures 和 SDK matrix 同步。本文的 STD 迁移不改变任何 API 兼容承诺。

## 9. Positive/Negative fixture 与 validator

v0.3 fixtures 包括 authorization scope、capacity semantic negative、Data Plane OpenAPI、
deferred-surface fail-closed、idempotency policy、metadata UTF-8 byte、Observation/Management OpenAPI
和 recovery protocol。它们保持在 interfaces/vectors/v0.3/。

tests/test_contract_semantics_v03.py 验证 semantic invariants；
tests/test_contract_consistency.py 验证 manifest/contract consistency；其他 tests 验证当前实现基线。
fixture PASS 只说明 candidate artifact consistency，不是 production endpoint evidence。

## 10. Requirement → Contract → Test traceability

| Requirement / Review scope | Contract element | Test/evidence | 当前证据状态 |
|---|---|---|---|
| exact-case Service Level、无 fallback | Models/Registry/admission enums与refs | semantic tests + manifest | Candidate PASS |
| Scope B 与 deferred surface | OpenAPI path set + surface_policy | deferred-surface fixture | Candidate PASS |
| zero duplicate dispatch/recovery | Responses/Invocation responses + recovery_protocol | recovery/idempotency fixtures | Candidate PASS；runtime BLOCKED |
| capacity all-constraints | CapacitySnapshot + groups/quota/readiness | capacity negative fixtures | Candidate PASS；production BLOCKED |
| Client/Source isolation | auth headers、filters、404/typed errors | authorization fixtures | Candidate PASS；runtime BLOCKED |
| secret non-disclosure/concurrency | Management schemas + If-Match/version | Management semantic tests | Candidate PASS；UI/runtime BLOCKED |
| activation separation | compatibility overall/activation fields | manifest consistency tests | Candidate PASS；activation false |

原 Review ID 和更细 traceability 继续由 docs/99_reference/verification/llm-tier-contract-qa-v0.3.md 保留，直到 C2 assurance
candidate 和后续 promotion 完成。

## 11. Activation Gate 与未决项

Document migration、OpenAPI validation、fixtures 和 local tests 不授权 runtime。激活仍要求 production
implementation commit、真实正负 Contract Test、Management API/UI、安全隔离、Registry/admission、
capacity/fairness、Piko pinned adapter、Embeddings consumer、lost-response/restart 与 legacy-path
removal evidence。

本文为 Approved contract index，实际 reviewed commit 见 sidecar；原 v0.3 machine artifacts 原位保留，
旧 prose contracts 标为 Superseded 并保留历史。`runtime_activation=false`，本状态不授权项目 RAG publication。
