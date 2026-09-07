<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier C2 Assurance Migration Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-c2-assurance-review` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-07` |
| STD Version | `0.1.0-draft.17` |
| Template ID | `review.packet` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-std-c2-assurance-review.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review 请求与期望决定

| Gate | 请求/结果 |
|---|---|
| Review Verdict | PENDING |
| Document Status before review | Draft |
| Requested Document Status after review | unchanged |
| Runtime Activation requested | false |
| Runtime Activation authority | N/A |

请求审查 C2 V&V plan、contract test specification、source→target mapping 和三层 evidence boundary。
本 packet 不请求 Document Status 升级、canonical promotion、RAG publication、外部发布或 Runtime Activation。

## 2. Scope、authority 与 reviewers

- 新增两份 assurance 候选及 sidecar；更新 migration plan、inventory 与迁移一致性测试。
- `docs/qa/llm-tier-contract-qa-v0.3.md` 在 promotion 前保留 review ledger/residual evidence authority。
- OpenAPI、manifest、tests 和 fixtures 的机器/可执行 authority 不变；新文档只描述计划与映射。
- LLMTier owner/QA 审核整体；Piko/Slinky production evidence 仍由对应 consumer authority 提供。

## 3. 冻结基线

| 项目 | 值 |
|---|---|
| Project root | `/Users/ben/work/LLMTier` |
| Input commit | `aa2638283e77bc658e98df8d40396306cad17aa2` |
| Input dirty path | `rag/std-ingestion-manifest.jsonl`（既有、排除） |
| Input tracked diff SHA-256 | `5ecf097f57ec627f36586218d14e8df036467c8466de59e06adc7553c6073234`（仅上述 RAG path） |
| Input untracked set SHA-256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（empty） |
| STD revision/tag | `94c0262de35b5b989bba9f8d23f212af709c9dbf` / `std-v0.1.0-draft.17` |
| Source manifest | `docs/std-source-manifest.json`；71 artifacts |
| Candidate hash list | `docs/98_migration/evidence/c2-candidate-sha256.txt` |

## 4. 变更摘要与设计理由

1. 将旧 QA 的策略/Gate 迁为 template-complete V&V plan；保留旧 QA 的历史 review 与 residual evidence。
2. 将现有 tests/fixtures/OpenAPI/manifest 整理为 case matrix 和可重复执行规则，不复制 executable oracle。
3. 明确 static candidate PASS、runtime/external NOT_RUN/BLOCKED 和 activation-required evidence 的边界。
4. 不新增 runtime、endpoint、Schema、config、fallback、selector 或 compatibility path。

## 5. Requirement、Design、Contract、Test 对齐

| 范围 | Design/Contract | Case | 当前 evidence |
|---|---|---|---|
| authority/exact ID/no fallback | service design + Piko/Slinky controls + OpenAPI | CT-AUTH-001、CT-ID-001 | local semantic PASS；consumer review/evidence 独立 |
| Scope B/deferred fail closed | Piko control + manifest | CT-DP-001 | fixture/semantic PASS；Piko capture BLOCKED |
| recovery/M2-C | Piko control + OpenAPI | CT-REC-001/002 | fixture PASS；durable crash evidence BLOCKED |
| Observation/capacity | Slinky control + OpenAPI | CT-OBS-001 | fixture PASS；Slinky E2E BLOCKED |
| Management/security/isolation | Management control + OpenAPI | CT-MGT-001/CT-SEC-001 | static PASS；runtime/UI BLOCKED |
| Registry/performance/activation | service design + manifest | CT-REG-001/CT-PERF-001 | static consistency PASS；production BLOCKED |

## 6. 风险、未决项和不阻塞项

- Runtime-required routes、store、provider、consumers、security/isolation、capacity/SLO 与 UI evidence 未运行，
  继续阻塞 Runtime Activation，但不阻止诚实的 C2 Migration Review candidate。
- C1 Piko/Slinky consumer verdict 仍由 STD 汇总；若产生 amendment，C2 mapping 随同修正后复验。
- 既有 RAG dirty 文件不属于 C2，不修改、不暂存。
- 当前无阻止 C2 候选进入 STD pre-commit review 的 blocker。

## 7. 验证命令与结果

原始命令、exit code、关键输出和 dirty preservation 记录在
`docs/98_migration/evidence/c2-validation-evidence.txt`；结构化 validator artifact 为
`docs/98_migration/evidence/c2-std-validation.json`。

- STD source verifier：exit 0；71 artifacts PASS。
- project-root validator：exit 0；11 metadata / 11 Markdown / 3 decision，0 issue。
- project tests：exit 0；43 tests PASS。
- `git diff --check`：exit 0。
- runtime/external：NOT_RUN/BLOCKED；本 cohort 不启动服务或 consumer。

## 8. Review Checklist

- [x] scope 与 authority 清楚
- [x] 现状、批准变更和未来设想未混写
- [x] 接口、错误、状态和恢复映射闭合
- [x] 安全与隔离 case 已列出，runtime evidence gap 未隐藏
- [x] traceability 和 evidence 路径可打开
- [x] 未发生静默 fallback 或兼容性扩张
- [x] 三层候选验证完成并固化
- [ ] STD pre-commit Gate 返回 COMMIT_APPROVED

## 9. 决定、条件与签署

机器 decision 位于 `docs/91_reviews/llmtier-std-c2-assurance-review.review-decision.json`，当前 PENDING。
终局 verdict 不自动提升 Document Status、执行 promotion/RAG publication 或激活 runtime。
