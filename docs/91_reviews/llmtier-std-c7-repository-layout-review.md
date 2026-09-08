<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier C7 Repository Layout Migration Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-c7-repository-layout-review` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-08` |
| Last Modified Date | `2026-09-08` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `review.packet` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | docs/98_migration/current-document-inventory.md |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-std-c7-repository-layout-review.md` |
| Supersedes | none |

> 本 packet 只审 repository paths、引用与 byte preservation，不授权 Runtime Activation。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 请求与输入

| Gate | 请求/结果 |
|---|---|
| Review Verdict | PENDING |
| Input commit | `9c554f79942bf574a2bddf5dc6110293d6b21240` |
| Requested Document Status | unchanged |
| Runtime Activation requested | false |
| External RAG indexing | NOT_RUN / not requested |

用户要求按照 STD 单服务软件目录一次性建立新目录树并移动文件。采用锁仍是
`0.1.0-draft.18` / `9841083c4d8d0ed1556bdc413d77b4567ac696b4`；draft.18 与当前 draft.19
的 repository/software layout 正文相同，path-policy 仅版本字段不同，因此本次不升级 STD lock。

## 2. 路径迁移

| 原路径 | 新 canonical path | 文件数 | Authority/状态 |
|---|---|---:|---|
| `docs/contracts/openapi/` | `interfaces/openapi/` | 1 | V0.3 字段级机器 authority |
| `docs/contracts/compatibility-manifest-*.json` | `interfaces/compatibility/` | 3 | activation/历史 compatibility；V0.3 仍 false |
| `docs/contracts/schemas/` | `interfaces/schemas/` | 1 | 历史 Schema |
| `docs/contracts/fixtures/v0.2/` | `interfaces/vectors/v0.2/` | 4 | 历史 frozen vectors |
| `docs/contracts/fixtures/v0.3/` | `interfaces/vectors/v0.3/` | 8 | 当前 executable oracle inputs |
| `docs/contracts/*.md` | `docs/99_reference/contracts/` | 7 | historical/Superseded prose |
| `docs/design/` | `docs/99_reference/design/` | 2 | historical/Superseded design |
| `docs/qa/` | `docs/99_reference/verification/` | 3 | historical/Superseded QA prose |
| `docs/future/` | `docs/99_reference/future/` | 1 | future/deferred，非 V0.3 authority |
| `docs/migration/source-provenance-v0.1.md` | `docs/98_migration/source-provenance-v0.1.md` | 1 | migration provenance |

总计 31 个 tracked artifact 使用 Git rename 迁移。只有路径和引用改变；机器 JSON/vectors 的文件字节
必须与输入 commit 完全一致。根 `src/`、`tests/`、`tools/` 按 single-service tailoring 原位保留，
不创建 `apps/`、`services/`、`packages/` 或空目录树。

## 3. Authority 与 residual

- 当前 prose authority 仍是 11 份 Approved STD 文档；本次只更新其中的路径引用。
- OpenAPI、compatibility manifest、Schema 和 vectors 移至顶层 `interfaces/` 后仍是原有唯一机器 authority。
- 五份 V0.3 Superseded prose 及 V0.1/V0.2 historical prose 移入 `docs/99_reference/`，不恢复 current authority。
- V0.4 future 文档继续 deferred；source provenance 继续不是 current design authority。
- `rag/std-ingestion-manifest.jsonl` 是输入前已有 dirty，原位保留且不纳入本 candidate。

## 4. Publication 边界

`rag/project-ingestion-manifest.jsonl` 是 commit `9c554f7` 中发布、绑定 promotion commit `503d0a0`
的不可变 snapshot。C7 不改写该 manifest 来伪造尚不存在的自引用 commit。C7 提交后如需让项目 RAG
索引当前路径引用字节，必须基于 C7 immutable commit 另走 RAG refresh Gate。外部索引和 Runtime
Activation 都保持 NOT_RUN/false。

## 5. 验证计划

- L1：锁定 draft.18 source verifier、project-root validator、metadata/path/reference 检查；
- L2：全部项目 tests；新增新目录存在、旧 tracked 路径消失、机器 artifact byte preservation、
  compatibility relative refs 与历史 disposition 检查；
- L3：N/A/NOT_RUN；本次没有 runtime 或外部系统变化；
- Git：rename detection、`git diff --check`、精确 candidate allowlist、既有 dirty preservation。

## 6. 当前决定

机器 decision 位于同名 `.review-decision.json`，当前保持 `PENDING`。本地迁移与验证完成后，若需提交，
仍按项目既定 pre-commit Gate 请求精确 COMMIT_APPROVED。
