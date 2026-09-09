<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier STD draft.21 Upgrade Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-draft21-upgrade-review` |
| Document Version | `0.1.0-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-09` |
| Last Modified Date | `2026-09-09` |
| Template ID | `review.packet` |
| Template Version | `0.1.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-std-draft21-upgrade-review.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review 请求与期望决定

| Gate | 请求/结果 |
|---|---|
| Review Verdict | PENDING |
| Document Status before review | Approved canonical documents；本 packet 为 In Review |
| Requested Document Status after review | `unchanged`；tailoring 仅 PATCH 到 `0.1.1` |
| Runtime Activation requested | `false` |
| Runtime Activation authority | N/A；本 packet 不具备 runtime activation authority |

> `Review Verdict = ACCEPTED` 不会自动将文档升为 Approved，也不会自动激活 runtime 变更。

## 2. Scope、authority 与 reviewers

- Scope：把 LLMTier 项目采用从 STD `0.1.0-draft.18` 升级到 `0.1.0-draft.21`，更新 lock、
  source manifest、所有已启用模板实例的封面/sidecar、项目 validator test 和采用说明。
- Authority：LLMTier 负责项目采用与文档事实；STD 负责模板、Schema 与工具；Slinky、Piko 只复核
  与其消费边界相关的内容没有语义漂移。
- Requested reviewers：Slinky、Piko。
- Non-goals：不改变 V0.3 Scope B、OpenAPI/manifest/fixture bytes、接口 ID、运行配置路径、业务
  Document Version/Status、旧 review verdict 或 Runtime Activation。

## 3. 冻结基线

| 项目 | 冻结值 |
|---|---|
| LLMTier base | `corezilla/LLMTier@2c01e36b`；完整 base commit 由 Git review diff 解析 |
| Target STD | `corezilla/STD@274ef0a67eda080baa0063ae27ede7ee129aa32a` |
| STD Version | `0.1.0-draft.21` |
| Source tag | `null`；没有伪造或使用 lightweight tag |
| Source manifest | `docs/std-source-manifest.json`；73 artifacts，逐文件 SHA-256 |
| Project profile/domains | `software`；`management, software` |
| Review target | 本 packet 随同的 immutable LLMTier review commit；commit 由 Matrix/Git transport 提供，避免文档自引用 |

## 4. 变更摘要与设计理由

1. README 与 `docs/std.lock.json` 统一记录项目采用 STD `0.1.0-draft.21` 和完整 40 位 commit。
2. `docs/std-source-manifest.json` 由 STD 官方工具重建，替代旧 draft.18 来源锁。
3. 所有 18 份既有正式文档移除单篇 `STD Version`，增加独立 `Template Version=0.1.0`；sidecar
   移除 `std_version`，更新 template hash，并保留原 conformance、tailoring、reviewed commit 和状态。
4. `std-tailoring` 因采用事实发生 PATCH 更新，Document Version 升为 `0.1.1`；业务设计、需求、接口、
   contract、assurance 和 operations 文档内容未改变，Document Version 保持原值。
5. 删除 legacy `rag/std-ingestion-manifest.jsonl`；STD source manifest 与 project RAG manifest 继续分离。
   已发布 `rag/project-ingestion-manifest.jsonl` 仍绑定原 canonical commit，本 review branch 不重发 RAG。
6. 单服务分类保持不变：`design.definition`、`design_level=subsystem`、根 `src/tests/docs/interfaces`；
   不引入 workspace、多服务目录或第二实现路径。

## 5. Requirement、Design、Contract、Test 对齐

| 范围 | 影响 |
|---|---|
| Requirements/traceability | 业务正文与 ID 零改动；仅封面/sidecar template fields |
| Service design | authority、Scope B、M2-C、recovery、capacity、安全与 activation gate 零改动 |
| Interfaces/contract | OpenAPI、compatibility manifest、schemas、vectors 字节不变 |
| Assurance/operations | 已批准正文与 historical evidence 不改写；旧 draft.18 执行记录继续作为历史事实 |
| Tests | migration tests 改为验证 draft.21 lock、73-source manifest、无 per-document STD Version、template 0.1.0/hash 和 legacy RAG source list 删除 |

## 6. 风险、未决项和不阻塞项

- 风险：把 project adoption version 误写回单篇文档。由 validator 与 regression test 阻断。
- 风险：把旧 review packet 中 draft.18 的历史执行记录误改成 draft.21。正文历史记录明确保留，
  只有封面/sidecar采用当前模板字段。
- 风险：把 template upgrade 误解释为业务 reapproval 或 runtime activation。此 packet 明确请求
  `requested_document_status_after=unchanged`、`runtime_activation_requested=false`。
- 不阻塞：formatter/linter 精确版本尚未冻结；本轮没有修改运行代码，README 仅记录该编码规范差距。
- 不阻塞：production persistence/HA、Admin UI、SDK capture 和 runtime gates 仍维持原状态。

## 7. 验证命令与结果

| 层 | 命令 | 期望/结果 | Artifact |
|---|---|---|---|
| L1 STD structural | `/Users/ben/work/STD/scripts/validate-design --project-root /Users/ben/work/LLMTier --require-immutable-std --json docs/98_migration/evidence/draft21-std-validation.json` | exit 0；最终结果随 review commit 固定 | `docs/98_migration/evidence/draft21-std-validation.json` |
| L1 source lock | `/Users/ben/work/STD/scripts/verify-source-manifest docs/std-source-manifest.json --std-root /Users/ben/work/STD` | exit 0；73 artifacts | source manifest |
| L2 project contract/schema | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | exit 0；用例数见执行输出 | unittest output |
| L2 JSON/diff | `python3 -m json.tool ...`；`git diff --check` | exit 0 | Git diff |
| L3 runtime/external | NOT_RUN；本轮无 runtime 变更 | 不得推导 activation | 原 V0.3 Open Gates |

## 8. Review Checklist

- [x] scope 与 authority 清楚
- [x] 现状、批准变更和未来设想未混写
- [x] 接口、错误、状态和恢复未发生业务变更
- [x] 安全与隔离边界未改变
- [x] traceability 和 evidence path 可打开
- [x] 未发生静默 fallback、兼容性扩张或新运行路径

## 9. 决定、条件与签署

机器决定记录：`docs/91_reviews/llmtier-std-draft21-upgrade-review.review-decision.json`。
当前为 `PENDING`，`decided_at=null`，不请求 Document Status 改变或 Runtime Activation。收到终局
review verdict 后按独立 promotion/publication Gate 处理；不得把 Matrix ACK 当作 ACCEPTED。
