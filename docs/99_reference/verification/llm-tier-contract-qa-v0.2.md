# LLMTier 三方契约 QA v0.2

Last Updated: 2026-09-06 15:18:00 +08:00

Status: Candidate review response；设计项已静态验证，服务实现与 Piko SDK evidence 仍未完成

| Review | 处理结果 | 证据 | 状态 |
| --- | --- | --- | --- |
| C1 Authority | 接受 Slinky 评审结论，保持 Management/Observation、Data Plane 与 Agent authority 分离 | `slinky-capacity-observation-contract-v0.2.md` §1 | 设计已对齐 |
| C2 Seat projection | 新增 `CapacitySnapshot`/group DTO、完整示例、确定性整数/共享组/重叠组/quota/burst/expiry 约束与正反 fixture | Schema、capacity snapshot/example 与 projection fixtures | 设计已补；真实 admission 未实现 |
| C3 Snapshot invalidation | 分离 configuration/inventory/capacity/snapshot version，定义强 ETag、valid_until 和 active invocation 不回滚边界 | Capacity contract §4 | 设计已补 |
| C4 Outcome query | 明确标记 `llmtier_recovery_extension_v1`、Piko adapter 显式消费、同一 ledger、跨 instance visibility、状态机、404/410/UnknownOutcome、response ref 与 retention | Data Plane contract §1–§3、`InvocationView` Schema 与 recovery fixtures | Candidate；待 Piko 证据 |
| C5 Idempotency | 定义认证命名空间、RFC 8785 digest、持久化先于 dispatch、并发/terminal duplicate、crash/expiry tombstone 与统一 retry budget | Data Plane contract §4 与 idempotency fixtures | 设计已补；持久 ledger 未实现 |
| C6 Error/Manifest | Source 越权为 403；hidden/nonexistent model 同为 404；manifest 补 Schema/fields/tool/structured output/stream/error/limits/version/activation，未验证项 fail closed | Data Plane contract §5 与 manifest v0.2 | 设计已补；无 verified surface |
| C7 继续与待决定 | 独立 runtime 工作继续；Pi SDK endpoint/stream/tool 证据仍由 Piko 提供，不由 LLMTier 猜测 | `P-20260906-001__003__NEEDS_INFO__pinned-pi-sdk-runtime-behavior.md` | 等待 Piko |

## 自动检查

- JSON 文件可解析，Draft 2020-12 Schema 可通过 validator 自检。
- `tests/test_contract_fixtures.py` 检查 manifest 不发布未验证 surface、snapshot group membership 双向一致，以及 Slinky 要求的关键正反 fixture 类别齐全。
- 这些检查只证明 candidate artifact 自洽，不代表 endpoint、ledger、SDK 或 admission 执行已经实现。

## 仍未冻结

- Piko pinned Pi SDK package/version、实际 endpoint、retry/timeout/stream/cancel 行为。
- Tool/structured output 的请求与事件细节。
- Header 最终名称、credential binding、retention 时长和 Service Level catalog。
- `/v1/chat/completions` 是否属于最低 surface，以及 recovery extension 是否被 Piko 显式采用。
