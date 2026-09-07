<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier C4 Decisions + Operations Migration Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-c4-operations-review` |
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
| Canonical Path | `docs/91_reviews/llmtier-std-c4-operations-review.md` |
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

C4 operations boundary、ADR omission rationale、Open Gate 和 residual authority 已由 LLMTier Owner
终局接受。Document Status 仅在独立 promotion Gate 中切换；本 packet 不请求 RAG publication、外部发布或 Runtime Activation。

## 2. Scope、authority 与 reviewers

- 新增一份 `operations.release` 候选与 sidecar；更新 tailoring、inventory、plan 与 migration test。
- operations 文档只承接当前仓库可确认的 package/CLI/start-stop/diagnostic 与已冻结 release Gate。
- 当前没有新的、已批准的 persistence/HA/RPO/RTO/topology 选择，因此不创建 retrospective ADR。
- 既有 Scope B、M2-C、authority 与接口决定继续由原 Matrix Review ID、service design 和 machine contract
  承担；未来新决定才使用 `decisions.adr`。

## 3. 冻结基线

- Input commit：`13b5d02266624b6b662349f0b88de23696c823bb`；branch `main`；existing `origin`。
- STD：`9841083c4d8d0ed1556bdc413d77b4567ac696b4` / `std-v0.1.0-draft.18`。
- 唯一输入 dirty：`rag/std-ingestion-manifest.jsonl`，排除且不修改。
- 输入 RAG binary diff SHA-256：`5ecf097f57ec627f36586218d14e8df036467c8466de59e06adc7553c6073234`；输入 untracked set 为空。
- Candidate/evidence：`docs/98_migration/evidence/c4-candidate-sha256.txt`、`c4-validation-evidence.txt`。

## 4. 变更摘要与设计理由

C4 把已有 operations facts 组织为 release、build/provenance、deployment boundary、config/secret、preflight、
upgrade/rollback/recovery、monitoring/SLO、maintenance、retention/backup/audit、acceptance/retirement。所有未实现
或未批准内容明确为 Open Gate/NOT_RUN/BLOCKED；不创建新 runtime/config/fallback/compatibility path。

ADR 决定为“本 cohort 不生成”：模板要求记录一个实际选择及其 considered options/evidence，而当前 Open
Gate 没有可合法填写的 Decision。凭迁移倒推答案会伪造 authority，故由 tailoring 保留按需启用。

## 5. Requirement、Design、Contract、Test 对齐

- LT-DEP-001/002 对应独立配置、release/rollback/backup/recovery/retirement 边界。
- LT-OPS-001/002/003 对应 health/readiness、audit、manifest/Registry consistency。
- LT-REL-001/002 对应 M2-C retention、fail-closed 与 recovery。
- 当前 tests 只验证文档、contract 与当前 package baseline；production operations evidence 全部独立。

## 6. 风险、未决项和不阻塞项

- 阻塞 production release/activation：artifact/SBOM、topology/TLS/service manager、config/secret store、durable
  store、backup/restore、HA/RPO/RTO、SLO/alerts、consumer/runtime/security evidence。
- 上述缺口不阻止诚实的 Migration Review candidate，但禁止将文档用作可执行 production runbook。
- 当前无阻止 C4 候选进入 STD pre-commit Gate 的 blocker。

## 7. 验证命令与结果

原始结果见 `docs/98_migration/evidence/c4-validation-evidence.txt`；validator JSON 为
`docs/98_migration/evidence/c4-std-validation.json`。L3 runtime/external 为 NOT_RUN/BLOCKED。

- source verifier：exit 0；71 artifacts。
- project-root validator：exit 0；16 metadata / 16 Markdown / 5 decisions，0 issue。
- project tests：exit 0；45 tests PASS。
- `git diff --check`：exit 0。

## 8. Review Checklist

- [x] scope 与 authority 清楚
- [x] current CLI 与 V0.3 production Open Gate 未混写
- [x] upgrade/rollback/recovery 与 no-fallback 边界闭合
- [x] secret、retention、backup 和 audit gap 明确
- [x] 未伪造 ADR、production evidence 或 SLO
- [x] 未发生兼容性扩张
- [x] 三层验证固化
- [x] STD pre-commit Gate 返回 COMMIT_APPROVED

## 9. 决定、条件与签署

机器 decision 位于 `docs/91_reviews/llmtier-std-c4-operations-review.review-decision.json`，当前为
`ACCEPTED`。终局 verdict 不自动改变 Document Status、promotion、RAG publication 或 Runtime Activation。
