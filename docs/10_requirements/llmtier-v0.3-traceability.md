<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Requirements Traceability Matrix

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-traceability` |
| Document Version | `0.3.0` |
| Status | `Approved` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | `2026-09-07` |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-07` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `requirements.traceability` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/10_requirements/llmtier-v0.3-traceability.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 范围与基线

本矩阵固定 LLMTier V0.3 requirements、service design、C1 interfaces/contract、C2 assurance 与现有
OpenAPI/manifest/tests/fixtures 的追踪关系。输入基线是 C2 commit
`b2e298aadf981283aa52d4764b201400397d1116` 和 STD draft.18。外部 Piko/Slinky needs 只作为输入，
其实现与验收 authority 不迁入本仓库。

状态只描述该行 evidence：`static-covered`、`blocked-runtime`、`not-run` 或 `open-decision`；没有实际
production evidence 的行不得标为 covered/accepted。

## 2. Traceability Matrix

| Need | Requirement | Design | Interface/Contract | Implementation | Verification/Test | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 唯一安全推理入口 | LT-FUN-001、LT-INT-001 | service design §1/3/5 | Piko control；OpenAPI；manifest | V0.3 route wiring 未证明 | CT-DP-001、CT-ID-001 | fixture/semantic tests | static-covered；blocked-runtime |
| 单一 catalog 与准确选择 | LT-FUN-002、LT-INT-001 | service design §5 | contract spec；OpenAPI/manifest | Registry/admission wiring 未证明 | CT-REG-001 | manifest/ref/authority tests | static-covered；blocked-runtime |
| durable recovery | LT-FUN-003/006、LT-INT-004、LT-REL-001 | service design §7-9 | Piko control；OpenAPI | durable ledger/store 未证明 | CT-REC-001/002 | recovery fixtures | static-covered；blocked-runtime |
| 只读 Seat/Observation | LT-FUN-004、LT-INT-005、LT-CAP-001/002 | service design §8/10 | Slinky control；OpenAPI | Observation routes 未证明 | CT-OBS-001 | capacity/observation fixtures | static-covered；Slinky E2E blocked |
| 可管理服务 | LT-FUN-005、LT-INT-002 | service design §5/6/11 | Management control；OpenAPI | API/UI 未证明 | CT-MGT-001 | management fixture/semantic tests | static-covered；blocked-runtime |
| Client/Source 与 secret 安全 | LT-SEC-001/002、LT-REL-002 | service design §11 | three controls；OpenAPI | auth/store/log wiring 未证明 | CT-AUTH-001、CT-SEC-001 | authorization fixtures | static-covered；security run blocked |
| 可观测且不误激活 | LT-OPS-001/002/003 | service design §9/12/14 | Observation/contract spec；manifest | runtime telemetry 未证明 | CT-OBS-001、CT-REG-001 | activation/static tests | static-covered；blocked-runtime |
| 可重复容量与 SLO | LT-PERF-001 | service design §10 | Slinky control | provider/model baseline 未批准 | CT-PERF-001 | none | open-decision/not-run |
| 独立部署与安全退役 | LT-DEP-001/002 | service design §13 | Management/operations future | topology/procedure 未批准 | C4 operations Gate | none | open-decision/not-run |
| STD 结构与来源完整 | all migrated docs | tailoring + inventory | metadata/source manifest | docs/tests | CT-MIG-001 | source verifier、validator、43+ tests | static-covered |

## 3. Coverage Rules

- `static-covered` 需要可打开的 fixture/test output 或 validator artifact；只有 case 名称不算 evidence。
- `blocked-runtime`、`not-run`、`open-decision` 不得提升为 PASS。
- requirement 变化必须检查 design、OpenAPI/manifest、controls、case matrix、tests/fixtures 和 consumer impact。
- OpenAPI/manifest/tests/fixtures 是机器/可执行 authority；本矩阵出现不一致时由本矩阵让位并触发 review。
- 一个测试可覆盖多条 requirement，但每条 P0 requirement 必须有独立可判定 oracle。

## 4. Orphan、Gap 与冲突

- 当前无 orphan V0.3 requirement：每条 requirement 至少映射到设计/contract 和 case。
- Runtime gaps：routes、durable ledger/store、Registry/admission、Management UI、security/isolation、capacity/SLO。
- Consumer gaps：Piko adapter capture、Slinky Observation E2E、实际 Embeddings consumer contract test。
- Decision gaps：persistence/HA/RPO/RTO/topology/provider SLO；C4 不得倒推答案。
- 若 Slinky same-tier fallback/Upshift 只在其内部路由层发生，不改变 transmitted exact
  `service_level_id`，则与 LLMTier API boundary 无冲突；任何跨级 ID 重写/alias 则冲突并 fail closed。

## 5. Review、冻结与更新记录

C3 terminal decision 为 ACCEPTED；source verifier、project-root validator、项目 tests 与 STD
pre-commit Gate 分别保留证据。requirements 或 machine contract 变化时同步更新本矩阵；execution evidence 形成时只更新
对应 evidence/status，不把局部 PASS 推导成 Runtime Activation。RAG publication 与
Runtime Activation 保持独立 Gate。
