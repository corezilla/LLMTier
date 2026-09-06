# LLMTier 三方契约 QA v0.1

Last Updated: 2026-09-06 13:40:00 +08:00

Status: Open；所有未决项均不得被实现私自冻结

| ID | 问题 | 当前结论/临时边界 | 影响 | 责任方 | 状态 |
| --- | --- | --- | --- | --- | --- |
| LT-QA-001 | Piko pinned Pi SDK package/version 与实际 endpoint | 尚未收到实测版本；主设计按 `/v1/responses`，不据名称推断 SDK 行为 | 阻塞 Pi conformance 与 Chat surface 决策 | Piko | 待材料 |
| LT-QA-002 | `/v1/chat/completions` 是否属于最低范围 | 仅当 pinned Pi SDK 必需且 manifest 明确授权时加入；绝不是 fallback | 影响首版 surface 和 fixture | Piko/LLMTier | 待决定 |
| LT-QA-003 | Data Plane-only 下的 lost-response outcome query | Piko 不调用 Observation API；候选是在 Data Plane authority 下提供受 Client scope 保护的 invocation outcome resource，否则保留 `UnknownOutcome` | 阻塞恢复契约冻结 | LLMTier/Piko/Slinky | 待提案 review |
| LT-QA-004 | canonical Client/Source headers 与伪造检测 | 需要 Slinky/Piko 给出最终 header 名、credential binding 与 identity 注册约束 | 阻塞 auth/negative fixture | Slinky/Piko | 待材料 |
| LT-QA-005 | `service_level_id` 最终集合与大小写 | 必须来自 versioned catalog，当前不建立大小写 alias | 阻塞 model fixture | Slinky/LLMTier | 待决定 |
| LT-QA-006 | idempotency 与 outcome retention | retention 必须覆盖 Client 最大恢复窗口，但具体时长未定 | 阻塞存储/SLO | 三方 | 待决定 |
| LT-QA-007 | Streaming disconnect 后 Provider cancel/continue policy | 必须按 Service Level/Backend capability 明示，不允许隐式重派 | 阻塞 stream recovery fixture | LLMTier | 待设计 |
| LT-QA-008 | Tool/structured output 的最低 JSON Schema keyword 集 | 不能以 Provider 宣称兼容替代 LLMTier contract test | 阻塞 Tool/structured-output fixture | Piko/LLMTier | 待实测 |
| LT-QA-009 | usage 缺失与最终 reconciliation | final usage 缺失必须为 absent/unknown，不能沿用旧代码部分补零语义 | 需要修改 stats/result mapping | LLMTier | 已识别 |
| LT-QA-010 | Embeddings 调用方和 scope | 不是 Piko Agent Data Plane 最低要求；Knowledge 使用需独立明确 Client/Source scope，不能成为 Slinky direct inference 旁路 | 影响首版范围 | Slinky/LLMTier | 待决定 |
| LT-QA-011 | 旧源工作树 `volc.py` 未提交差异 | 导入基线包含 `doubao-seed-2.1-turbo`；已记录工作树与 HEAD digest | 不阻塞独立化，但需审计其新 catalog 资格 | LLMTier | 已记录 |
| LT-QA-012 | 旧 Agent/mlexp/CLI backend 的处置 | 从新 authoritative registry 删除，不作为 fallback；代码删除时间随独立化提交记录 | 影响迁移与测试 | LLMTier | 已确定方向 |

## 已由资料回答

- IR-backed 唯一路径：`Slinky Runtime -> Piko -> LLMTier Data Plane -> Model Backend`。
- LLMTier 不承担 Agent、Plan、IR composition、Knowledge selection、Artifact 或 Acceptance authority。
- Piko 不消费 Tier Management/Observation authority，不理解 Provider/Account/Pool/capacity group。
- exact `model` 表示 `service_level_id`，不得用 physical model 或大小写 alias 替代。
- 无可验证 outcome 时必须保留 `UnknownOutcome`，不能盲目重派。

## 后续证据门槛

每个 QA 项关闭时必须引用不可变邮箱消息、versioned contract/manifest、实现提交和对应正反 fixture；只有设计文本不能标记“已验证”。
