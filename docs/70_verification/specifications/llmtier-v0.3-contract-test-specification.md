<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Contract Test Specification

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-contract-test-specification` |
| Document Version | `0.3.2-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier, Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.2.0` |
| Template ID | `assurance.test-specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与被测对象

被测对象是OpenAPI/manifest、current fixtures、authority docs和legacy-removal rules；不把未实现runtime当PASS。

## 2. 引用基线、环境与前置条件

使用candidate.1机器字节、Draft 2020-12 validator和Python unit tests。生产adapter、credential和模型不可作为静态前置。

## 3. Case Matrix

| ID | Subject | Oracle | Runtime state |
|---|---|---|---|
| CT-DP-001 | Responses text/tool call/tool result | OpenAPI + fixture valid；LLMTier不执行tool | BLOCKED |
| CT-MODEL-001 | Models exact ID/capabilities | case-sensitive；no alias/fallback | BLOCKED |
| CT-EMB-001 | Embeddings float/base64/batch | dedicated capability；standard response | BLOCKED |
| CT-USAGE-001 | per-call/query usage | measured/estimated/unknown；unknown null；no Cost | BLOCKED |
| CT-ADMIN-001 | cloud/local CRUD/probe/audit | Secret not returned；probe confirmation | BLOCKED |
| CT-OPS-001 | health/readiness/restart confirmation | no-cost probe separation | BLOCKED |
| CT-BOUNDARY-001 | stateless gateway | no Agent session/context/tool/KV ownership | STATIC PASS candidate |
| CT-SCOPE-001 | removed extensions | forbidden path/header/schema absent | STATIC PASS candidate |

## 4. 正常、边界、负向与并发场景

正常：text、function roundtrip、embedding batch、model list、measured usage、CRUD。边界：unknown usage、max limit、exact case、local provider without secret。负向：unknown field、wrong model capability、stream=true before decision、missing auth、probe without confirmation、delete referenced resource。并发编辑使用409；不测试外部Seat/claim。

## 5. Recovery、重放、幂等与故障注入

V0.3不定义custom model-call recovery/idempotency。测试标准client retry下的429/502/503和网络不明，不声称exactly-once。运维故障注入覆盖config/provider/store/restart；不创建跨系统恢复状态机。

## 6. 性能、容量、功耗或时序测试

功耗/硬件时序不适用。性能和内部保护需固定provider/model/config实测；不发布外部capacity snapshot或SLO前置结论。

## 7. 执行步骤与自动化入口

1. JSON parse + OpenAPI ref resolution。
2. fixture schema/semantic validation。
3. forbidden term/path/header scan。
4. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests`。
5. CLI help、STD validator和diff-check。

## 8. Pass/Fail/Blocked/Invalid 判定

Static PASS仅表示候选一致；runtime未执行为BLOCKED。旧custom机制仍在current machine authority为FAIL。用legacy `/call`替代目标API为INVALID。

## 9. Artifact、日志、测量与证据保存

保存commit/hash、命令、exit code、validator结果和合成fixture；不保存Secret、生产prompt/output或provider payload。

## 10. 安全、清理与可重复性

测试credential独立；probe需明确授权并记录费用可能性；清理测试资源但保留脱敏audit。重复执行不得依赖旧candidate或另一条fallback。
