<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Traceability

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-traceability` |
| Document Version | `0.3.2-draft.3` |
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

基线是 requirements `0.3.2-draft.3`、system design `0.3.2-draft.3`、OpenAPI `0.3-simplified-candidate.5` 与 compatibility manifest 同版本。

## 2. Traceability Matrix

| Capability | Requirements | Design | Machine Contract | Tests | Runtime |
|---|---|---|---|---|---|
| Stateless Responses/tool loop | LT-FUN-001/007/008 | §2/6/11、core module §5 | `/v1/responses` | CT-DP-001/CT-BOUNDARY-001 | STATIC COVERED；runtime BLOCKED |
| Models/exact level | LT-FUN-002 | §3/4 | `/v1/models*` | CT-MODEL-001 | BLOCKED |
| Embeddings | LT-FUN-003 | §6.2、core module §7 | `/v1/embeddings` + ModelCapabilities embedding fields | CT-EMB-001 | STATIC COVERED；runtime BLOCKED |
| Token Usage | LT-FUN-004、LT-INT-004/005/007 | §10/11、core module §6 | standard response usage + `/tier/v1/usage` | CT-USAGE-001 | STATIC COVERED；runtime BLOCKED |
| Admin UI/API | LT-FUN-005、LT-INT-008、LT-SEC-001 | §11.2、Web UI design | `/tier/admin/v1/*` | CT-ADMIN-001/CT-UI-001 | STATIC COVERED；runtime BLOCKED |
| Config authority | LT-REL-004 | module §4、ISD §3/4 | internal store contract | CT-STORE-001 | DESIGN COVERED；runtime BLOCKED |
| Health/operations | LT-FUN-006、LT-OPS-001..004 | §6.3/12 | `/healthz`、`/readyz`、probe | CT-OPS-001 | BLOCKED |
| Removed extensions | LT-INT-003、LT-REL-002 | §3/12/G | absence oracle | CT-SCOPE-001 | STATIC COVERED |

## 3. Coverage Rules

每个current path必须有成功、validation、auth和provider failure case。固定Pi golden request必须覆盖首轮、assistant历史、function call/output、image tool result与opaque reasoning。SSE必须执行sequence/item ID/terminal语义检查。Usage必须有measured、estimated、unknown、版本替换和store失败；unknown不得为0。Admin必须覆盖If-Match、partial patch、401/403/409/412。旧custom path/header/schema必须以absence test防止回归。

## 4. Orphan、Gap 与冲突

- Standard Responses SSE已由固定Pi adapter的`stream:true/store:false`调用方式确定；candidate.5静态fixture覆盖真实序列化形状，Piko消费复审与真实capture仍是后续证据。
- LLMTier implementation gaps：目标 `/v1` routes、embedding deployment、Usage query、Admin UI/API、production auth/TLS/runbook。
- legacy `/call` 实现仍在源码但不属于 current contract；迁移完成前不得暴露为 fallback。
- 旧 review/历史文件仅作 provenance，不参与当前 traceability。

## 5. Review、冻结与更新记录

本候选是一次性替代旧 `finalization-candidate.5`，不建立兼容分支。Consumer 与 Owner 复审、实现 capture 和 runtime activation 分别记录；静态签署不自动激活。
