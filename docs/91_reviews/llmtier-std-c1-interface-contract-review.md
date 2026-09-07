<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier C1 Interface + Contract Migration Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | llmtier-std-c1-interface-contract-review |
| Document Version | 0.1.0-draft.2 |
| Status | Draft |
| Project | LLMTier |
| Authority | LLMTier |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | 2026-09-07 |
| Last Modified Date | 2026-09-07 |
| STD Version | 0.1.0-draft.18 |
| Template ID | review.packet |
| Template Conformance | tailored |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | corezilla/LLMTier |
| Canonical Path | docs/91_reviews/llmtier-std-c1-interface-contract-review.md |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review 请求与期望决定

| Gate | 请求/结果 |
|---|---|
| Review Verdict | ACCEPTED |
| Document Status before review | Draft |
| Requested Document Status after review | accepted |
| Runtime Activation requested | false |
| Runtime Activation authority | N/A |

C1 interface/contract 的结构化迁移、authority 和 residual-scope 映射已完成终局 review。Document Status
只在独立原子 canonical-promotion Gate 中切换；本 packet 不请求项目 RAG ingestion、外部发布或 Runtime Activation。

## 2. Scope、authority 与 reviewers

- 范围：三份 interfaces.control 候选、一份 contracts.specification 候选、plan/inventory/tailoring
  增量和迁移一致性测试。
- LLMTier owner 审核整体服务、Management、安全和机器 contract authority。
- Piko reviewer 只审核 Piko consumer/recovery obligations；不取得 LLMTier 服务 authority。
- Slinky reviewer 只审核 Observation/Seat consumer obligations；不取得 LLMTier 服务 authority。
- OpenAPI v0.3 保持字段级机器 authority；compatibility manifest v0.3 保持 capability/activation
  machine authority；tests/fixtures 保持 executable evidence authority。
- 原三份 v0.3 prose contract 的 current scope 已逐项映射；本次原子 promotion 将其标为
  Superseded，新 interface controls 明确记录一对一 predecessor，机器契约仍原位保留。

## 3. 冻结基线

| 项目 | 值 |
|---|---|
| Project root | /Users/ben/work/LLMTier |
| Project input HEAD | 8dc6a54c92608ab6373f40c78cc954da7086f30e |
| Input stable dirty snapshot digest | dfe350dded17c0173f61acb52cba065c1ed307ccf23e7d68710f1861f9c3616c |
| Input tracked diff SHA-256 | bc7bec6eae476d0fd61c66afcbd94cd69e73f54422521b35e2bc27ca4ab24c39 |
| Input untracked set SHA-256 | db2121431530bd305a3f21ac380cb9ab22aa498e0f730ce9a399c59affd45404 |
| STD revision | 94c0262de35b5b989bba9f8d23f212af709c9dbf |
| STD annotated tag | std-v0.1.0-draft.17 |
| STD source manifest | docs/std-source-manifest.json；71 artifacts |
| Migration plan | docs/98_migration/llmtier-std-migration-plan.md |

C1 candidate payload 的 12 个文件逐文件 SHA-256 见
docs/98_migration/evidence/c1-candidate-sha256.txt；有序清单摘要为
150609cc05bfbfbc8be81b57a39242aa1336305c4ed6e8a8705fdea207da94dc。review packet、decision 和
validator output 不纳入该 payload，避免自引用。

## 4. 变更摘要与设计理由

| Source | C1 candidate | 迁移结论 |
|---|---|---|
| docs/contracts/piko-data-plane-contract-v0.3.md | docs/60_interfaces/piko-data-plane-control.md | 承接 Data Plane/adapter boundary；保持 exact ID、恢复、M2-C 与 no fallback |
| docs/contracts/slinky-capacity-observation-contract-v0.3.md | docs/60_interfaces/slinky-capacity-observation-control.md | 承接只读 Observation、Seat、ETag/invalidation 与 Client scope |
| docs/contracts/llmtier-management-contract-v0.3.md | docs/60_interfaces/llmtier-management-control.md | 承接 admin、安全、并发、secret 和 recovery management |
| OpenAPI/manifest/fixtures/三份说明 | docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md | 只建立 scope/authority/evolution/test 索引；机器 artifact 原位 |

迁移没有建立新的 endpoint、Schema、selector、fallback、compatibility path 或 runtime mechanism。
v0.1/v0.2 historical 文件、原 v0.3 prose、OpenAPI、manifest、fixtures 和运行代码均未删除/移动。

## 5. Requirement、Design、Contract、Test 对齐

| 约束 | Candidate section | Machine authority / evidence | 状态 |
|---|---|---|---|
| Runtime → Piko → LLMTier；exact-case；无 fallback | Piko control §1/4/9 | OpenAPI + manifest + semantic tests | Candidate PASS |
| active/terminal/lost-response/UnknownOutcome | Piko control §5/6 | recovery fixtures + semantic tests | Candidate PASS；runtime BLOCKED |
| committed Seat 所有约束与失效 | Slinky control §5/7 | capacity fixtures + semantic tests | Candidate PASS；production BLOCKED |
| Client/Source isolation | three controls §8 | auth fixtures + OpenAPI | Candidate PASS；runtime BLOCKED |
| Management secret/concurrency/recovery safety | Management control §4-8 | OpenAPI + Management fixtures/tests | Candidate PASS；UI/runtime BLOCKED |
| activation=false 与三 Gate 分离 | contract spec §1/11 | compatibility manifest | Candidate PASS |

更细的原 Review ID 与 evidence ledger 仍由 docs/qa/llm-tier-contract-qa-v0.3.md 维护，C2 assurance
再迁为正式 V&V/traceability 候选。

## 6. 风险、未决项和不阻塞项

- 终局 C1 review 使用 clarification commit `e1f9b796368ec5f358e466c7e6299cc16b1bf181`，并由
  LLMTier Owner、Piko 与 Slinky 分别完成授权范围内复核。
- Piko 对 commit `aa263828...` 的 consumer boundary 为 ACCEPTED，证据见
  `docs/98_migration/evidence/c5-consumer-verdicts.txt`。Slinky 对原输入的 AMENDMENT
  `S-20260907-8866534be612` 已由 draft.2 修正；Slinky 在 `S-20260907-45938693e578` 对 exact
  commit/blob/SHA-256 返回 ACCEPTED，`SLK-BOUNDARY-001` 已关闭。
- production endpoint、ledger/retention、Registry/admission、capacity/fairness、Management API/UI、
  Piko pinned adapter、Embeddings consumer 与真实 isolation evidence 未运行，继续阻塞 activation。
- 本项目输入 worktree dirty 是已记录的非阻塞条件；本轮未 reset/clean，也未覆盖其他任务修改。
- 当前无阻止 C1 Migration Review candidate 完成的安全 blocker。
- 提交前必须通过 STD 只读复核并收到明确 COMMIT_APPROVED；批准应限定精确 pathspec，避免夹带
  cohort 输入时已存在的用户/其他任务 dirty 修改。

## 7. 验证命令与结果

所有命令均以 /Users/ben/work/LLMTier 为 workdir；不使用 || true 包装原始退出码。

### 7.1 STD structural/source

- /Users/ben/work/STD/scripts/verify-source-manifest /Users/ben/work/LLMTier/docs/std-source-manifest.json --std-root /Users/ben/work/STD
  - exit 0；STD source manifest verification OK: 71 artifacts。
  - artifact：docs/std-source-manifest.json。
- /Users/ben/work/STD/scripts/validate-design --project-root /Users/ben/work/LLMTier --require-immutable-std --json /Users/ben/work/LLMTier/docs/98_migration/evidence/c1-std-validation.json
  - exit 0；ok=true，new_error_count=0，inherited_error_count=0，checked_metadata=8，
    checked_markdown=8，checked_decisions=2。
  - artifact：docs/98_migration/evidence/c1-std-validation.json。

### 7.2 Project contract/schema/test

- PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests
  - exit 0；42 tests；OK。
  - 覆盖现有 contract semantics、OpenAPI/manifest/fixture consistency 与新增 C1 authority 断言。
- git diff --check
  - exit 0；无 whitespace error。

### 7.3 Runtime/external dependency evidence

NOT_RUN/BLOCKED。本轮不启动 service、provider、Piko/Slinky consumer、Admin UI 或 production store。
该结果不阻止 C1 文档候选 review，但继续阻塞 Runtime Activation。

## 8. Review Checklist

- [x] scope 与 authority 清楚
- [x] 现状、批准变更和未来设想未混写
- [x] 接口、错误、状态和恢复保持既有机器 contract
- [x] 安全、Secret 与 Client/Source 隔离边界已保留
- [x] traceability、fixture 和 tests 路径可打开
- [x] 未发生静默 fallback、Schema 复制或兼容性扩张
- [x] 旧文档 residual authority 与后置 promotion 边界明确
- [x] Piko consumer-boundary verdict 可审计且为 ACCEPTED
- [x] Slinky `SLK-BOUNDARY-001` 已形成 draft.2 定点修订
- [x] Slinky 对新的 immutable draft.2 input 返回 ACCEPTED
- [x] STD 已返回 clarification snapshot 精确 pathspec 的 COMMIT_APPROVED
- [x] immutable project candidate commit 与终局 reviewer/decision 已登记

## 9. 决定、条件与签署

机器 decision 位于 docs/91_reviews/llmtier-std-c1-interface-contract-review.review-decision.json，
当前为 `ACCEPTED`，decision commit 为 `e1f9b796368ec5f358e466c7e6299cc16b1bf181`。终局 verdict
不自动提升 Document Status，也不授权 promotion、RAG 或 runtime；状态切换仍由独立 promotion Gate 执行。
