<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier Independent Project Documentation Refresh Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-independent-project-doc-refresh` |
| Document Version | `0.1.0-draft.3` |
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
| Canonical Path | `docs/91_reviews/llmtier-independent-project-doc-refresh.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review 请求与期望决定

| Gate | 请求/结果 |
|---|---|
| Review Verdict | PENDING |
| Document Status before/after | Approved；请求 `unchanged` |
| Runtime Activation requested | `false` |
| Machine contract change | none |
| Current implementation change | client trace default moved from legacy workspace to LLMTier `state/`; service help text updated |
| Requested reviewers | Slinky、Piko |

本 packet 请求复核“LLMTier 已是独立单服务项目”的当前路径和使用说明，不重开 V0.3 Scope B、
authority、M2-C、capacity、header/path 或 activation 决策。

draft.2 修正 draft.1 的设计层级错误：LLMTier 是本仓库完整 `system`，不是跨项目系统的内部
`subsystem`。主设计从 `docs/30_subsystem_design/` 移至 `docs/20_system_design/`，并改用
`design.system`；当前没有内部 subsystem design。

draft.3 补齐此前缺失的完整系统架构表达：新增系统边界与 logical building blocks 全景图、Responses
首次调用及两种 lost-response 恢复分支时序图，以及当前单进程开发部署图。图中明确三类 API 分面共享
Registry/ledger/identity，不把 logical building block 误写成 subsystem，也不新增实现路径。

## 2. 当前事实基线

| 范围 | 当前事实 |
|---|---|
| Repository | `corezilla/LLMTier`；单服务根布局 |
| Python/build | Python `>=3.11`；setuptools；project `llm-tier` version `0.1.0` |
| Source | `src/` flat modules/packages |
| Service entry | installed `llm-tier`; checkout `PYTHONPATH=src python3 -m tier_service` |
| Operator entry | installed `llm-tier-cli`; checkout `PYTHONPATH=src python3 -m cli` |
| Config | Git-ignored `config/settings.json`; `--settings`/`LLMTIER_CONFIG` |
| Secret files | Git-ignored `config/secrets/`; never copied into evidence or RAG |
| Runtime state | Git-ignored `state/`; `LLMTIER_STATE_DIR` |
| Client origin | `TIER_SERVER_URL`; credential-free trusted-network HTTP origin |
| Machine contract | `interfaces/`; unchanged and `overall.runtime_activation=false` |

Slinky/Piko 只通过其受控 HTTP consumer boundary 使用 LLMTier，不 import LLMTier 源码、不共享配置或
状态目录，也不控制 LLMTier 进程。

## 3. 修改范围与 traceability

1. README 改为当前项目入口，补齐安装、启动、operator CLI、路径和能力边界。
2. tailoring 增加 `LT-TL-016`，固定单服务的 `src/config/state/interfaces` ownership。
3. requirements 增加 `LT-FUN-007`、`LT-DEP-003/004`，traceability 增加 `CT-OPS-001` 映射。
4. system design 使用 STD `design.system` 的 12 节与 A-H 附录，更新 system context、building blocks、
   runtime、deployment、横切概念、质量、风险与当前 entry points；并提供系统逻辑架构、运行时恢复时序和
   当前物理部署三张 Mermaid 图。
5. 三份 interface control 明确 consumer 只走 HTTP/artifact，不共享 LLMTier filesystem。
6. contract specification 明确 `interfaces/` 是唯一机器 authority，并记录本轮 machine bytes 不变。
7. V&V/test specification 增加当前路径、CLI、旧 workspace 回流检查。
8. operations 给出可执行安装/启动/health/config/state 流程，并区分 legacy runtime 与未激活 V0.3。
9. `tests/test_std_migration.py` 增加 current-doc path/usage regression test。
10. `src/client.py` 将现有 client trace 默认文件收敛到项目 `state/`；保留 `TIER_TRACE_STATE_PATH`，不新增
    环境变量或兼容分支。`src/tier_service.py` 的模块说明和进程 banner 统一为 LLMTier 当前入口。

历史 `docs/99_reference/`、旧 review/evidence 和 `rag/project-ingestion-manifest.jsonl` 保持原样；后者仍绑定
此前 accepted commit，本候选在 review/promotion 前不重发 RAG。

## 4. 不变项

- `interfaces/openapi/`、`interfaces/compatibility/`、`interfaces/schemas/`、`interfaces/vectors/` 字节不变；
- V0.3 Scope B、Chat/SSE V0.4 deferred、exact-case Service Level、单一 Registry/OpenAPI 不变；
- M2-C `W=168h`、`M=24h`、`D=24h`、UnknownOutcome 和 Seat invalidation 不变；
- Management/Admin UI required 与 production Open Gates 不变；
- 不新增 config path、selector、alias、fallback、第二 inference/recovery/management path；
- Runtime Activation 保持 false。

## 5. 验证与判定

| 检查 | 结果 |
|---|---|
| STD source manifest | PASS；73 artifacts |
| STD project validator | PASS；20 metadata、20 Markdown、9 decisions、0 issues |
| Project tests | PASS；最终用例数由 immutable commit 验证，新增 client state-path regression |
| Service/operator CLI help | PASS |
| Machine contract diff against base | empty |
| `git diff --check` | PASS |

L3 production endpoint、durability、consumer capture、Admin UI 与 activation 均 NOT_RUN/BLOCKED；本轮静态
PASS 不得向上推导为 runtime capability。

## 6. Review 决定

机器决定记录在
`docs/91_reviews/llmtier-independent-project-doc-refresh.review-decision.json`。当前为 PENDING；review
target 由 Git/Matrix 提供 immutable commit，避免文档自引用。draft.1 commit `8c8f8b2` 与此前 draft.21
review target、draft.2 commit `21794e2` 均由本候选后继 commit supersede，但 STD lock/source 与机器契约
事实不变。
