# LLMTier 三方契约 QA v0.3

Last Updated: 2026-09-06

Status: Candidate Amendment 3；正在处理 Slinky `S-20260906-7f86cf4103bd`，scope/capture 仍待裁决

## 1. Slinky amendment traceability

| Review item | 修改 | Artifact | 状态 |
| --- | --- | --- | --- |
| Authority 与唯一路径 | 固定 Slinky Project/Plan/IR、Piko Runtime、LLMTier model service；唯一 `Runtime -> Piko -> LLMTier` | design §2；Piko contract §1；Slinky contract §1 | Candidate aligned |
| Seat invalidation | Seat 立即 Invalidated、阻断新 dispatch、通知 Plan；只允许已 admission Invocation 收敛 | design §6；Slinky contract §5 | 设计已修订，未接线 |
| M2-C 数值 | retry/recovery <=24h；terminal 后 digest/tombstone >=7d；Response recovery >=7d | design §5.3；两侧 contract；manifest；fixture | 选择已冻结，执行未验证 |
| Registry authority/case | LLMTier authority；exact-case `Worker`/`Junior`；同一 Registry 驱动 Models/Observation/admission/manifest；无 alias/fallback | design §4；两侧 contract；manifest；Data Plane Schema | Candidate aligned |
| Management API/UI | 恢复为 V0.3 required scope；覆盖 inventory、registry、identity/entitlement、probe、capacity/usage/audit/recovery；secret write-only | design §7；management contract；manifest | Required，未实现 |
| 唯一 Data Plane | Responses + Chat + Embeddings + Models + SSE；没有 Responses-only 或第二兼容路径 | design §5；Piko contract §2/§8；manifest | Required，待 Piko capture |
| terminal replay | POST 不再以 200 返回 InvocationView；Failed/Cancelled/UnknownOutcome 使用 typed non-2xx Error，详情由 Invocation GET 查询 | design §5.2；Piko contract §5；manifest；recovery fixture | Candidate fixed |
| Activation gates | 加入 Management、Registry consistency、isolation/fairness、production validator、Piko capture、legacy/direct-path removal scan | design §9；Piko contract §9；management contract §4；manifest | Candidate fixed |
| 单一 path/header authority | 全链只允许 `/tier/admin/v1`、`X-Tier-Client-Request-ID`、`X-Tier-Invocation-ID`；无 alias | OpenAPI；两侧 contract；fixtures；authority scan test | Candidate fixed |
| 可执行 Data Plane | OpenAPI 3.1 固定 body、SSE event/sequence、typed input/output、未知字段拒绝；支持 `store`、`max_completion_tokens`、`stream_options.include_usage`，拒绝 `max_tokens` | OpenAPI；data-plane/SSE fixtures；Contract Test | Candidate fixed，capture 待补 |
| Recovery 一致性 | `InvocationAccepted` 只允许 Pending/Queued/Running；create/replay/retrieve 复用 canonical Response；409/502/503 与 required headers 固定 | OpenAPI；Piko contract；recovery fixtures/tests | Candidate fixed |
| Observation/Management 完整性 | Invocation list/detail、分页、ETag/304；Management method/path、DTO、并发、幂等、Job、secret/recovery 机器契约 | OpenAPI；两份 prose contract；coverage tests | Candidate fixed，未实现 |
| Activation 可判定 | policy selection 与 runtime activation 分离；overall/per-capability 均为 false | manifest；activation tests | Candidate fixed |
| 唯一 Schema authority | Manifest 只装载 V0.3 OpenAPI；历史 v0.2 不作为当前 Data Plane authority | manifest；full-ref/authority tests | Candidate fixed |

## 2. Machine-readable consistency

- `compatibility-manifest-v0.3.json` 的 `data_plane_endpoints` 必须恰好包含统一 V0.3 surface，且只引用 `openapi/llmtier-v0.3.openapi.json`。
- 所有 endpoint 仍是 `candidate_required` 或 `candidate_required_extension`，不得出现 `verified`。
- `terminal_replay.http_200_invocation_view_allowed=false`。
- M2-C 为唯一选项，Manifest 与 fixture 的 24h/7d 数值一致。
- `service_level_registry.id_matching=exact_case_sensitive`，alias/cross-level fallback 均为 false。
- Management API/UI 都是 candidate required，prefix 仅 `/tier/admin/v1`，secret policy 为 write-only。
- OpenAPI 必须包含 Responses、Chat、Embeddings、Models、SSE、ErrorEnvelope、Recovery、Observation 和 Management schema/path。
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
| Streaming/Chat scope | Piko 请求延至 V0.4；Slinky 要求留在 V0.3 统一 surface | NEEDS_INFO，等待 Slinky/用户裁决；无第二路径 |

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

1. Slinky/用户裁决 V0.3 是否保留 Chat/SSE/Embeddings/Models，或接受 Piko 的 V0.4 scope amendment。
2. Piko 按裁决后的唯一 surface 实现 adapter，并补齐首次 200、active 202、terminal error、lost response、UnknownOutcome 和适用 endpoint 的真实 capture。
3. Piko 完整 runtime matrix 需解决 Gondolin Node `>=23.6.0` 与 capture Node `22.22.3` 的 engine warning。
4. Slinky 对本轮 Amendment 3 immutable commit/diff re-review 并给出 ACCEPTED/REJECTED/AMENDMENT。
5. production implementation 与第 4 节列出的运行证据尚未完成；Manifest 保持 candidate。
