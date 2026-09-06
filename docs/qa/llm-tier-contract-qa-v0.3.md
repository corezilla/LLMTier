# LLMTier 三方契约 QA v0.3

Last Updated: 2026-09-06 15:34:00 +08:00

Status: Candidate review response；M1/M3/M4 已补设计与本地证据，M2 等待契约责任方选择

| Review | 处理结果 | 状态 |
| --- | --- | --- |
| M1 Response read-back | 新增 conditional `GET /v1/responses/{response_id}`、Schema、授权/retention/error/activation；Chat 未有 normalization evidence 时 fail closed | Candidate，待 Piko |
| M2 forgotten key | 明确完全删除后的信息论不可区分；列 A 永久 index、B server epoch、C 有限保证窗口三种取舍，未选择、未实现 | 需要 Slinky/Piko 决定 |
| M3 first/replay protocol | 定义 non-stream 首次 200、active replay 202 自定义 envelope、completed replay 200、首次丢包用相同 key 取回 invocation ID；stream/chat 未验证时 fail closed | Candidate，待 Piko SDK capture |
| M4 byte/capacity semantics | UTF-8 bytes 成为 authoritative unit；加入多字节负例和 executable validator；加入 duplicate IDs、available、membership、time、unknown quota 执行负例 | 本地验证完成，未接 production route |

## 本地验证边界

`tools/contract_semantic_validator_v03.py` 是 candidate contract test harness，不是生产 admission/metadata middleware。测试通过只能证明 fixtures 在该候选算法下产生预期结果；不能证明真实 API、SDK 或持久 ledger 已完成。

## 需要的决定

- Slinky/Piko 对 M2 选择 A、B 或 C；A/B 是新机制，不经明确批准不实现。
- Piko 提供 pinned SDK 对 202 custom response、stream headers/events、retry 和 Chat normalization 的 capture。
- 决定 retention 数值后，才能激活 response retrieval 和 idempotency recovery 声明。
