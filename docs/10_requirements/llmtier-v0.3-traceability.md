<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Traceability

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-traceability` |
| Document Version | `0.3.2-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | 待定 |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.1.0` |
| Template ID | `requirements.traceability` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/10_requirements/llmtier-v0.3-traceability.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 范围与基线

基线是 requirements `0.3.2-draft.1`、system design `0.3.2-draft.1`、OpenAPI `0.3-simplified-candidate.1` 与 compatibility manifest 同版本。

## 2. Traceability Matrix

| Capability | Requirements | Design | Machine Contract | Tests | Runtime |
|---|---|---|---|---|---|
| Stateless Responses/tool loop | LT-FUN-001/007/008 | §2/6/11 | `/v1/responses` | CT-DP-001/CT-BOUNDARY-001 | BLOCKED |
| Models/exact level | LT-FUN-002 | §3/4 | `/v1/models*` | CT-MODEL-001 | BLOCKED |
| Embeddings | LT-FUN-003 | §6.2 | `/v1/embeddings` | CT-EMB-001 | BLOCKED |
| Token Usage | LT-FUN-004、LT-INT-004/005 | §10/11 | response usage + `/tier/v1/usage` | CT-USAGE-001 | BLOCKED |
| Admin UI/API | LT-FUN-005、LT-SEC-001 | §11.2 | `/tier/admin/v1/*` | CT-ADMIN-001/CT-UI-001 | BLOCKED |
| Health/operations | LT-FUN-006、LT-OPS-001..004 | §6.3/12 | `/healthz`、`/readyz`、probe | CT-OPS-001 | BLOCKED |
| Removed extensions | LT-INT-003、LT-REL-002 | §3/12/G | absence oracle | CT-SCOPE-001 | STATIC COVERED |

## 3. Coverage Rules

每个 current path 必须有成功、validation、auth 和 provider failure case。Usage 必须有 measured、estimated、unknown；unknown 不得为 0。旧 custom path/header/schema 必须以 absence test 防止回归。

## 4. Orphan、Gap 与冲突

- Cross-system open：Piko 是否需要 standard streaming。
- LLMTier implementation gaps：目标 `/v1` routes、embedding deployment、Usage query、Admin UI/API、production auth/TLS/runbook。
- legacy `/call` 实现仍在源码但不属于 current contract；迁移完成前不得暴露为 fallback。
- 旧 review/历史文件仅作 provenance，不参与当前 traceability。

## 5. Review、冻结与更新记录

本候选是一次性替代旧 `finalization-candidate.5`，不建立兼容分支。Consumer 与 Owner 复审、实现 capture 和 runtime activation 分别记录；静态签署不自动激活。
