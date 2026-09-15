<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Requirements Traceability Matrix

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-traceability` |
| Document Version | `0.3.1-draft.3` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | — |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-16` |
| Template Version | `0.1.0` |
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

本矩阵固定 LLMTier V0.3 requirements、system design、C1 interfaces/contract、C2 assurance 与现有
OpenAPI/manifest/tests/fixtures 的追踪关系。当前标准基线由 `docs/std.lock.json` 锁定为 STD draft.26；
业务 baseline 由 accepted documents、OpenAPI、manifest 与 review decisions 共同限定。外部 Piko/Slinky needs 只作为输入，
其实现与验收 authority 不迁入本仓库。

状态只描述该行 evidence：`static-covered`、`blocked-runtime`、`not-run` 或 `open-decision`；没有实际
production evidence 的行不得标为 covered/accepted。

## 2. Traceability Matrix

| Need | Requirement | Design | Interface/Contract | Implementation | Verification/Test | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 唯一安全推理入口 | LT-FUN-001、LT-INT-001 | system design §1-5 | Piko control；OpenAPI；manifest | V0.3 route wiring 未证明 | CT-DP-001、CT-ID-001 | fixture/semantic tests | static-covered；blocked-runtime |
| Piko 多轮工具交互 | LT-FUN-008 | system design §4/11.2 | Piko control；Responses schemas | LLMTier 不执行工具；真实 adapter capture 未证明 | CT-DP-001 | schema fixture + Piko capture | static-covered；consumer/runtime blocked |
| 单一 catalog 与准确选择 | LT-FUN-002、LT-INT-001 | system design §4/5/8 | contract spec；OpenAPI/manifest | Registry/admission wiring 未证明 | CT-REG-001 | manifest/ref/authority tests | static-covered；blocked-runtime |
| durable recovery | LT-FUN-003/006、LT-INT-004、LT-REL-001/003/004 | system design §6/8/11、附录 C | Piko control；OpenAPI | durable ledger/store 未证明 | CT-REC-001/002、CT-DEADLINE-001、CT-EMB-REC-001 | recovery/deadline/Embedding fixtures | static-covered；consumer/runtime blocked |
| admission 与只读 Seat/Observation | LT-FUN-004、LT-INT-005、LT-CAP-001/002/003/004/005 | system design §3-6/10-13、附录 E | Piko/Slinky controls；OpenAPI | admission/Observation routes 未证明 | CT-ADM-001、CT-OBS-001、CT-DEADLINE-001 | admission/capacity/deadline fixtures | static-covered；runtime/Slinky E2E blocked |
| 可管理服务 | LT-FUN-005、LT-INT-002 | system design §3-5/8 | Management control；OpenAPI | API/UI 未证明 | CT-MGT-001 | management fixture/semantic tests | static-covered；blocked-runtime |
| Client/Source 与 secret 安全 | LT-SEC-001/002、LT-REL-002 | system design §8、附录 D | three controls；OpenAPI | auth/store/log wiring 未证明 | CT-AUTH-001、CT-SEC-001 | authorization fixtures | static-covered；security run blocked |
| 可观测且不误激活 | LT-OPS-001/002/003/004 | system design §8/10/11、附录 E/G | Observation/contract spec；manifest | runtime telemetry/pricing 未证明 | CT-OBS-001、CT-REG-001、CT-COST-001 | activation/observation-cost tests | static-covered；blocked-runtime |
| 可重复容量与 SLO | LT-PERF-001 | system design §10、附录 E | Slinky control | provider/model baseline 未批准 | CT-PERF-001 | none | open-decision/not-run |
| 独立部署与安全退役 | LT-FUN-007、LT-DEP-001/002/003/004 | system design §5/7、附录 G | Management/operations | `pyproject.toml`、`src/tier_service.py`、`src/cli/`、`src/tier_config.py`、`src/server.py` | CT-PKG-001、CT-OPS-001；C4 operations Gate | CLI help与独立边界测试；production topology未批准 | static-covered；open-decision/not-run |
| STD 结构与来源完整 | all canonical docs | tailoring + inventory | metadata/source manifest | docs/tests | CT-MIG-001 | source verifier、validator、project tests | static-covered |

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

2026-09-09 的维护把当前路径/CLI/配置状态映射加入 LT-FUN-007、LT-DEP-003/004；没有修改
`interfaces/` 下的字段级机器契约，production gaps 和 activation 判定保持不变。
