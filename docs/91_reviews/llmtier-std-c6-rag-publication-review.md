<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier C6 RAG Publication Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-c6-rag-publication-review` |
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
| Canonical Path | `docs/91_reviews/llmtier-std-c6-rag-publication-review.md` |
| Supersedes | none |

> 本 packet 只申请项目文档 RAG publication，不申请 Runtime Activation 或外部服务部署。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review 请求

| Gate | 请求/结果 |
|---|---|
| Review Verdict | PENDING |
| Document Status before/after | Draft / unchanged |
| Requested action | 提交项目 ingestion manifest 与静态 publication evidence |
| Runtime Activation requested | false |
| External RAG service deployment | NOT_RUN / not requested |

唯一 publication input 是已推送的 canonical promotion commit
`503d0a03fa92aeeb7657ce7ed54bab8b77efef34`。本 cohort 新建
`rag/project-ingestion-manifest.jsonl`，不会修改或纳入既有 dirty
`rag/std-ingestion-manifest.jsonl`。

## 2. Inclusion 与 immutable binding

manifest 仅包含 promotion commit 中 11 份 `Accepted` 项目 prose authority。每行保存
`repository`、`path`、`commit`、`document_status`、`visibility`、`authority`、Document ID、
document type/version、namespace、chunk strategy 和内容 SHA-256。所有路径按 UTF-8 byte order
排序，均绑定同一个 publication commit；内容 hash 从该 commit 的文件字节复算。

## 3. Exclusion

以下内容不进入 current project namespace：

- 五份 `Superseded` V0.3 legacy prose；
- `docs/91_reviews/`、`docs/98_migration/` 中的 review/candidate/evidence；
- historical/provenance、future/deferred 文档；
- OpenAPI、compatibility manifest、fixtures、源码与 tests 等 machine/executable authority；
- STD 模板/规范副本和既有 `rag/std-ingestion-manifest.jsonl`；
- 未提交编辑器内容、非 promotion commit 字节和 runtime/external evidence 缺口。

排除并不删除 Git 中的历史、machine authority 或 evidence，也不改变它们的权威边界。

## 4. ACL 与 namespace

publication namespace 固定为 `project/llmtier`，visibility 固定为 `project`，authority 固定为
`llmtier`。检索必须先验证调用者具有 LLMTier project scope 且请求 authority 为 `llmtier`，再允许读取
manifest 对应内容；未认证、其他项目 scope、其他 authority 或跨 namespace 请求一律 fail closed。
本 cohort 只验证该 pre-filter contract 和 manifest 数据，不配置或部署外部检索服务。

## 5. Duplicate-authority 检查

静态检查要求 Document ID、path 和 `(authority, current scope)` 唯一；每行 status 必须为
`accepted` 且 include=true。manifest 集合必须与 promotion commit 中 11 份 Accepted、非 review
metadata 的 source path 双向相等，并确认五份 Superseded legacy 路径与所有 review/evidence 路径均不在集合。

## 6. Retrieval contracts

在 ACL 允许的 `project/llmtier` 集合上执行确定性 heading/text 检索：

1. `canonical service_level_id alias Role selector` 命中 Piko Data Plane control；
2. `same-tier fallback Upshift admission` 命中 Slinky Capacity/Observation control；
3. `Runtime Activation NOT_RUN BLOCKED` 命中 V&V/operations authority；
4. 非 LLMTier project principal 返回零候选；
5. Superseded legacy 路径、review packet 和 STD manifest 请求返回零 current-authority 候选。

这是 publication candidate 的静态 retrieval contract，不冒充外部索引、线上召回质量或 production L3。

## 7. 三层验证与边界

- L1 STD source verifier PASS（71 artifacts）；project-root validator PASS（18 metadata / 18 Markdown /
  7 decisions，0 issue）；
- L2 项目 tests 48/48 PASS，包含 manifest schema、commit/hash、ACL、include/exclude、authority 唯一
  和检索合约；
- L3 runtime/external RAG indexing：NOT_RUN / N/A，本 cohort 未授权部署或 activation；
- dirty preservation：`rag/std-ingestion-manifest.jsonl` 保持未修改、未暂存并以既有 binary diff digest 核验。

## 8. Review Checklist

- [x] canonical promotion commit 已存在并推送
- [x] 11 份 current project authority 已纳入
- [x] legacy/review/evidence/future/STD/machine authority 已排除
- [x] ACL 先于 retrieval 且 fail closed
- [x] duplicate authority 与 deterministic retrieval contract 已定义
- [x] L1/L2 原始证据已固化
- [ ] 精确 pre-commit allowlist/digest 已固化并提交 STD
- [ ] STD 返回 COMMIT_APPROVED

## 9. 决定

机器 decision 位于同名 `.review-decision.json`，在 STD pre-commit Gate 前保持 `PENDING`。
无论 publication verdict 如何，`runtime_activation_requested=false`。
