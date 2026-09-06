# LLMTier 三方契约 QA v0.3

Last Updated: 2026-09-06

Status: Candidate Amendment 1；已处理 Slinky `S-20260906-59891d73fa13`，等待 Piko capture 与 Slinky re-review

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

## 2. Machine-readable consistency

- `compatibility-manifest-v0.3.json` 的 `data_plane_endpoints` 必须恰好包含统一 V0.3 surface。
- 所有 endpoint 仍是 `candidate_required` 或 `candidate_required_extension`，不得出现 `verified`。
- `terminal_replay.http_200_invocation_view_allowed=false`。
- M2-C 为唯一选项，Manifest 与 fixture 的 24h/7d 数值一致。
- `service_level_registry.id_matching=exact_case_sensitive`，alias/cross-level fallback 均为 false。
- Management API/UI 都是 candidate required，secret policy 为 write-only。
- Schema 必须包含 Responses、Chat、Embeddings、Models、ErrorEnvelope、Registry entry 和 recovery views。

## 3. Evidence boundary

当前本地测试可以证明 JSON 可解析、Schema/Manifest 结构与上述决策一致、capacity/metadata/recovery fixtures 在候选算法下得到预期结果。它不能证明：

- 生产 Data Plane、Management、Observation route 已实现；
- durable ledger/crash recovery 已执行且零重复 dispatch；
- Admin Web UI 可用或 secret 从未泄漏；
- 单一 Registry 已接入 Models/Observation/admission；
- multi-client/source isolation 和公平性；
- Capacity validator 已接生产路径；
- Piko SDK/provider adapter 的真实兼容行为；
- 旧 embedded Tier、Role routing、Agent backend、Provider-direct path 已删除。

## 4. Remaining blockers

1. Piko 提交 pinned SDK/provider adapter 名称、版本，以及 Responses/Chat/Embeddings/Models/SSE、首次 200、active 202、terminal error、lost response、UnknownOutcome capture。
2. Piko 确认 canonical Client/Source 绑定与最长 24 小时 retry/recovery deadline；不能满足则在实现前提出唯一替代值。
3. Slinky 对本次 amendment commit/diff re-review 并给出 ACCEPTED/REJECTED。
4. production implementation 与第 3 节列出的运行证据尚未完成；Manifest 保持 candidate。
