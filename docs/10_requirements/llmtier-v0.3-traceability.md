<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Traceability

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-traceability` |
| Document Version | `0.3.2-draft.5` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko、Slinky、LLMTier |
| Approver | LLMTier |
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

基线是 requirements `0.3.2-draft.5`、system design `0.3.2-draft.5`、OpenAPI `0.3-simplified-candidate.6` 与 compatibility manifest 同版本。

## 2. Traceability Matrix

| Capability | Requirements | Design | Machine Contract | Tests | Runtime |
|---|---|---|---|---|---|
| Stateless Responses/tool loop | LT-FUN-001/007/008 | §2/6/11、core module §5 | `/v1/responses` | CT-DP-001/CT-BOUNDARY-001 | STATIC COVERED；runtime BLOCKED |
| Models/exact level | LT-FUN-002 | §3/4 | `/v1/models*` | CT-MODEL-001 | BLOCKED |
| Embeddings | LT-FUN-003 | §6.2、core module §7、ISD §8 | `/v1/embeddings` + ModelCapabilities embedding fields | CT-EMB-001 | DESIGN/STATIC COVERED；deployment BLOCKED |
| Token Usage | LT-FUN-004、LT-INT-004/005/007 | §10/11、core module §6 | standard response usage + `/tier/v1/usage` | CT-USAGE-001 | STATIC COVERED；runtime BLOCKED |
| Admin UI/API | LT-FUN-005、LT-INT-008、LT-SEC-001/003 | §11.2、Web UI design §§2..10 | `/tier/admin/v1/*` | CT-ADMIN-001/CT-UI-001/CT-WEBSEC-001 | DESIGN COVERED；runtime BLOCKED |
| Sanitized operational logs | LT-FUN-005、LT-SEC-004、LT-OPS-006 | §11.2、Web UI design §7、ISD §10 | `GET /tier/admin/v1/logs` | CT-LOG-001 | STATIC CONTRACT COVERED；runtime BLOCKED |
| Internal admission | LT-PERF-001/002 | §12、core module §8、ISD §5 | standard 429/503 only | CT-ADM-001 | DESIGN COVERED；runtime BLOCKED |
| Config authority | LT-REL-004 | module §4、ISD §3/4 | internal store contract | CT-STORE-001 | DESIGN COVERED；runtime BLOCKED |
| Health/operations | LT-FUN-006、LT-OPS-001..005 | §6.3/12、Operations §§3/9/10 | `/healthz`、`/readyz`、probe | CT-OPS-001 | DESIGN COVERED；runtime BLOCKED |
| Removed extensions | LT-INT-003、LT-REL-002 | §3/12/G | absence oracle | CT-SCOPE-001 | STATIC COVERED |

## 3. Coverage Rules

每个current path必须有成功、validation、auth和provider failure case。固定Pi golden request必须覆盖首轮、assistant历史、function call/output、image tool result与opaque reasoning。SSE必须执行sequence/item ID/terminal语义检查。Usage必须有measured、estimated、unknown、版本替换和store失败；unknown不得为0。Admin必须覆盖If-Match、partial patch、401/403/409/412；日志必须覆盖Schema、禁入内容和store 503。旧custom path/header/schema必须以absence test防止回归。

## 4. Orphan、Gap 与冲突

- Standard Responses SSE已由固定Pi adapter的`stream:true/store:false`调用方式确定；candidate.6沿用已复审的candidate.5调用语义并新增脱敏日志查询，真实capture仍是后续证据。
- LLMTier implementation gaps：目标 `/v1` routes、固定BGE-M3 deployment字节、Usage query、Admin UI/API、production auth/TLS/systemd/backup证据。对应设计已确定，不再是跨方字段裁决项。
- legacy `/call` 实现仍在源码但不属于 current contract；迁移完成前不得暴露为 fallback。
- 旧 review/历史文件仅作 provenance，不参与当前 traceability。

## 5. Review、冻结与更新记录

本候选是一次性替代旧 `finalization-candidate.5`，不建立兼容分支。Consumer 与 Owner 复审、实现 capture 和 runtime activation 分别记录；静态签署不自动激活。
