<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier C3 Requirements + Traceability Migration Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-c3-requirements-review` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-07` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `review.packet` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-std-c3-requirements-review.md` |
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

C3 requirements/traceability 的来源、authority、coverage status 和 residual scope 已由 LLMTier Owner
终局接受。Document Status 仅在独立 promotion Gate 中切换；本 packet 不请求 RAG publication、外部发布或 Runtime Activation。

## 2. Scope、authority 与 reviewers

- 新增 requirements specification、traceability matrix 及 sidecar；更新 tailoring、inventory、plan 与测试。
- LLMTier 只提取本服务 shall statements；Piko/Slinky inputs 仅引用，不复制其 Runtime/Project/Plan/IR authority。
- OpenAPI/manifest/tests/fixtures 继续为机器/可执行 authority；原设计、contract、QA 的 current scope 已逐项
  映射，本次 promotion 后仅保留 historical provenance。
- LLMTier owner 审核需求归属和 completeness；consumer-boundary review 仍独立。

## 3. 冻结基线

- Input commit：`b2e298aadf981283aa52d4764b201400397d1116`；branch `main`。
- 唯一输入 dirty：`rag/std-ingestion-manifest.jsonl`，排除且不修改。
- 输入 RAG binary diff SHA-256：`5ecf097f57ec627f36586218d14e8df036467c8466de59e06adc7553c6073234`；输入 untracked set 为空。
- STD revision/tag：`9841083c4d8d0ed1556bdc413d77b4567ac696b4` / `std-v0.1.0-draft.18`。
- Hash/evidence：`docs/98_migration/evidence/c3-candidate-sha256.txt`、`c3-validation-evidence.txt`。

## 4. 变更摘要与设计理由

Owner 已决定启用独立 requirements 与 traceability 实例，以明确 shall statement、外部输入与 runtime evidence
gap。迁移不增加 endpoint、Schema、selector、fallback、config 或 runtime mechanism，也不把 static evidence
改写为 production evidence。

STD draft.18 修复 Git ignored/non-Git fallback source discovery，模板正文不变。本 cohort 同时把 lock、
71-artifact source manifest 及全部受 lock 约束的 candidate cover/metadata 统一 rebaseline 到 draft.18；
旧 C0-C2 packet 正文中的 draft.17 执行记录继续作为历史 evidence，不被改写成新的执行事实。

## 5. Requirement、Design、Contract、Test 对齐

矩阵覆盖 Scope B、Registry、recovery、Observation/capacity、Management、安全、运维、部署与 activation。
所有 P0 requirement 均映射 design/contract 与 C2 case；没有 production evidence 的行明确为
blocked-runtime/not-run/open-decision。

## 6. 风险、未决项和不阻塞项

- production persistence/HA/RPO/RTO、Admin UI、provider SLO、isolation 与 consumer evidence 继续开放。
- 这些 gap 阻塞 Runtime Activation 或 C4 结论，不阻塞诚实的 C3 migration candidate。
- C1 consumer review 若产生 amendment，C3 requirement/matrix 必须同步修正后复验。
- 当前无阻止进入 STD pre-commit review 的 blocker。

## 7. 验证命令与结果

原始命令、exit code 和结果见 `docs/98_migration/evidence/c3-validation-evidence.txt`；validator JSON 为
`docs/98_migration/evidence/c3-std-validation.json`。L3 runtime/external 为 NOT_RUN/BLOCKED。

- draft.18 source verifier：exit 0；71 artifacts；`.DS_Store` entries=[]。
- project-root validator：exit 0；14 metadata / 14 Markdown / 4 decisions，0 issue。
- project tests：exit 0；44 tests PASS。
- `git diff --check`：exit 0。

## 8. Review Checklist

- [x] scope 与 authority 清楚
- [x] 现状、批准变更和未来设想未混写
- [x] 接口、错误、状态与 recovery requirement 可追踪
- [x] 安全与隔离 requirement/case 已列出
- [x] static/runtime evidence 状态未混淆
- [x] 未发生静默 fallback 或兼容性扩张
- [x] 三层验证固化
- [x] STD pre-commit Gate 返回 COMMIT_APPROVED

## 9. 决定、条件与签署

机器 decision 位于 `docs/91_reviews/llmtier-std-c3-requirements-review.review-decision.json`，当前为
`ACCEPTED`。终局 verdict 与 Document Status、promotion、RAG publication、Runtime Activation 分开。
