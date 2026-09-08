# LLMTier 三方契约 QA v0.3

> **Document Status: Superseded（2026-09-07）** 当前 V&V/traceability prose authority 已迁至
> [`llmtier-v0.3-vv-plan`](../70_verification/plans/llmtier-v0.3-vv-plan.md)、
> [`llmtier-v0.3-contract-test-specification`](../70_verification/specifications/llmtier-v0.3-contract-test-specification.md)
> 和 [`llmtier-v0.3-traceability`](../10_requirements/llmtier-v0.3-traceability.md)。测试源码与 fixtures
> 继续是 executable oracle；本文件仅保留历史 review ledger。逐 scope disposition 见
> [`legacy-v03-scope-mapping.md`](../98_migration/legacy-v03-scope-mapping.md)。

Last Updated: 2026-09-06

Status: Superseded；历史 QA/review ledger，Runtime Activation 未授权

## 1. Slinky amendment traceability

| Review item | 修改 | Artifact | 状态 |
| --- | --- | --- | --- |
| Authority 与唯一路径 | 固定 Slinky Project/Plan/IR、Piko Runtime、LLMTier model service；唯一 `Runtime -> Piko -> LLMTier` | design §2；Piko contract §1；Slinky contract §1 | Candidate aligned |
| Seat invalidation | Seat 立即 Invalidated、阻断新 dispatch、通知 Plan；只允许已 admission Invocation 收敛 | design §6；Slinky contract §5 | 设计已修订，未接线 |
| M2-C 数值 | retry/recovery <=24h；terminal 后 digest/tombstone >=7d；Response recovery >=7d | design §5.3；两侧 contract；manifest；fixture | 选择已冻结，执行未验证 |
| Registry authority/case | LLMTier authority；exact-case `Worker`/`Junior`；同一 Registry 驱动 Models/Observation/admission/manifest；无 alias/fallback | design §4；两侧 contract；manifest；Data Plane Schema | Candidate aligned |
| Management API/UI | 覆盖 inventory、registry、Client/Source/SourceInstance/Entitlement、CapacityGroup、Job、probe、aggregate capacity/usage、audit、RecoveryItem；secret write-only | design §7；management contract；OpenAPI；manifest | Required，未实现 |
| 唯一 Data Plane | V0.3 仅 Responses non-stream、Models、Responses recovery、Embeddings non-stream；Chat/SSE/streaming 移至 V0.4 | design §5；Piko contract §2/§8；manifest；future doc | Scope B fixed |
| terminal replay | POST 不再以 200 返回 InvocationView；Failed/Cancelled/UnknownOutcome 使用 typed non-2xx Error，详情由 Invocation GET 查询 | design §5.2；Piko contract §5；manifest；recovery fixture | Candidate fixed |
| Activation gates | 加入 Management、Registry consistency、isolation/fairness、production validator、Piko capture、legacy/direct-path removal scan | design §9；Piko contract §9；management contract §4；manifest | Candidate fixed |
| 单一 path/header authority | 全链只允许 `/tier/admin/v1`、`X-Tier-Client-Request-ID`、`X-Tier-Invocation-ID`；无 alias | OpenAPI；两侧 contract；fixtures；authority scan test | Candidate fixed |
| 可执行 Data Plane | OpenAPI 3.1 只含 Scope B current paths；Responses `stream=true` 与 Chat path fail closed | OpenAPI；data-plane/deferred fixtures；Contract Test | Candidate fixed，capture 待补 |
| Recovery 一致性 | `InvocationAccepted` 只允许 Pending/Queued/Running；create/replay/retrieve 复用 canonical Response；409/502/503 与 required headers 固定 | OpenAPI；Piko contract；recovery fixtures/tests | Candidate fixed |
| Observation/Management 完整性 | Invocation list/detail、分页、ETag/304；Management method/path、DTO、并发、幂等、Job、secret/recovery 机器契约 | OpenAPI；两份 prose contract；coverage tests | Candidate fixed，未实现 |
| Activation 可判定 | policy selection 与 runtime activation 分离；overall/per-capability 均为 false | manifest；activation tests | Candidate fixed |
| 唯一 Schema authority | Manifest 只装载 V0.3 OpenAPI；历史 v0.2 不作为当前 Data Plane authority | manifest；full-ref/authority tests | Candidate fixed |
| Observation DTO/query | 扩展 Readiness、ServiceLevel、Compatibility；Invocation/Usage 全过滤维度、分页、ETag/304 与 typed source/contract errors | OpenAPI；Slinky contract；observation fixtures/tests | Candidate fixed |
| Management resources | 增加 SourceInstance、CapacityGroup、Job list、RecoveryItem；aggregate capacity/usage 独立 DTO | OpenAPI；Management contract；fixtures/tests | Candidate fixed，未实现 |

## 2. Machine-readable consistency

- `compatibility-manifest-v0.3.json` 的 `data_plane_endpoints` 必须恰好包含统一 V0.3 surface，且只引用 `openapi/llmtier-v0.3.openapi.json`。
- 所有 current endpoint 的 support 都是 `v0.3_required_active_candidate`，deferred surface 只出现在 `v0.4_deferred_not_implemented`，不得出现 `verified`。
- `terminal_replay.http_200_invocation_view_allowed=false`。
- M2-C 为唯一选项，Manifest 与 fixture 的 24h/7d 数值一致。
- `service_level_registry.id_matching=exact_case_sensitive`，alias/cross-level fallback 均为 false。
- Management API/UI 都是 candidate required，prefix 仅 `/tier/admin/v1`，secret policy 为 write-only。
- OpenAPI 必须包含 Responses non-stream、Embeddings non-stream、Models、Responses Recovery、Observation 和 Management；不得包含 Chat path、SSE content 或 streaming Schema。
- `W=168h`、`M=24h`、公式上限 144h、产品 deadline 24h，Invocation/Response/tombstone retention 均为 terminal 后至少 168h。
- active `202` 要求 Location、Invocation header、Retry-After；terminal non-2xx 要求 Location 与 Invocation header。
- Invocation GET 必须显式返回 `recovery_ready` 和 `recovery_disposition`。

## 3. Piko review traceability

| Piko item | 修改/结论 | 状态 |
| --- | --- | --- |
| 固定 Pi baseline | 记录 source commit、pi-coding-agent、pi-ai、openai、provider、adapter、Node 与 Gondolin warning | 已进入 Piko contract/manifest |
| Client/Source namespace | Responses namespace、canonical digest、同 key 冲突和 durable recovery obligation 明确 | Candidate fixed |
| W/M/retention | LLMTier 冻结 W=168h、M=24h、clock skew <=5m；Slinky D=24h 满足 D<=W-M | Candidate fixed，执行未验证 |
| terminal 200 | 旧 proposal 已被 Slinky Amendment 1 删除；POST 200 只允许标准成功 body | Superseded；Schema/fixture 已修正 |
| 202/non-2xx headers | Invocation 建立后 Location 与 Invocation ID 必需；202 另需 Retry-After | Candidate fixed |
| lost-response readiness | InvocationView 增加 recovery_ready/disposition/retry_after_ms | Candidate fixed |
| Pi mock captures | 记录内建 stream:true、202/旧 terminal incompatibility、typed error flatten、lost-response retry | Partial evidence，不足以激活 |
| Streaming/Chat scope | Slinky 已裁决移至 V0.4；V0.3 不实现、不声明、不保留第二路径 | CLOSED by Scope B |

## 4. Evidence boundary

当前本地测试可以证明 JSON 可解析、Schema/Manifest 结构与上述决策一致、capacity/metadata/recovery fixtures 在候选算法下得到预期结果。它不能证明：

- 生产 Data Plane、Management、Observation route 已实现；
- durable ledger/crash recovery 已执行且零重复 dispatch；
- Admin Web UI 可用或 secret 从未泄漏；
- 单一 Registry 已接入 Models/Observation/admission；
- multi-client/source isolation 和公平性；
- Capacity validator 已接生产路径；
- Piko SDK/provider adapter 的真实兼容行为；
- 旧 embedded Tier、Role routing、Agent backend、Provider-direct path 已删除。

## 5. Remaining blockers

1. Piko 按 Scope B 实现 adapter，并补齐 Responses non-stream、Models、active 202、terminal error、lost response 与 UnknownOutcome 的真实 capture。
2. Embeddings 需要 LLMTier OpenAI SDK Contract Test 和实际 Memory/Knowledge Consumer Contract Test。
3. Piko 完整 runtime matrix 需解决 Gondolin Node `>=23.6.0` 与 capture Node `22.22.3` 的 engine warning。
4. Slinky 对本轮 Amendment 4 immutable commit/diff re-review 并给出 ACCEPTED/REJECTED/AMENDMENT。
5. production implementation 与第 4 节列出的运行证据尚未完成；Manifest 保持 candidate。
