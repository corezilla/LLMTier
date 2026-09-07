<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier STD draft.17 Migration Review Packet

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-std-draft16-migration-review` |
| Document Version | `0.1.0-draft.2` |
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
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-std-draft16-migration-review.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review 请求与期望决定

| Gate | 请求/结果 |
|---|---|
| Review Verdict | ACCEPTED |
| Document Status before review | In Review |
| Requested Document Status after review | `accepted` |
| Runtime Activation requested | `false` |
| Runtime Activation authority | N/A |

本 packet 的迁移结构和 scope 映射已由 LLMTier Owner 终局接受；Document Status 仅在独立原子
canonical-promotion Gate 中切换，不请求项目 RAG ingestion、外部发布或 runtime activation。
文件路径保留早先的 `draft16` 字样，以维持已发送 Matrix review reference；Document ID 同样保持
稳定。封面、metadata、lock 和 source manifest 是当前 draft.17 authority。

## 2. Scope、authority 与 reviewers

- 项目根：`/Users/ben/work/LLMTier`；`project_profile=software`；
  `enabled_domains=[management, software]`。
- 首批 cohort：tailoring、document inventory/migration map、immutable STD lock/source manifest、
  LLMTier 单服务 `design.definition` 候选、review packet/decision 和迁移一致性测试。
- LLMTier 保持本服务设计和实现事实 authority；OpenAPI v0.3 保持字段级机器契约 authority；
  compatibility manifest v0.3 保持兼容性/activation 候选 authority且 activation=false；
  `tests/` 与 fixtures 保持可执行源码/证据 authority。
- 原 `docs/design/llmtier-v0.3-design-review.md` 的全部 current scope 已在 C5 逐项映射；本次原子
  promotion 将其标为 Superseded，同时保留为历史 review provenance。
- LLMTier Owner 已在终局 decision 中登记，decision commit 为集成输入 `962e800...`。

## 3. 冻结基线

| 项目 | 值 |
|---|---|
| Project repository | `corezilla/LLMTier` |
| Project input HEAD | `8dc6a54c92608ab6373f40c78cc954da7086f30e` |
| Project input state | dirty；不 reset、不 clean、不覆盖 |
| Input tracked diff SHA-256 | `1887324d647667196f4a38db2eb1f002e826fae714834a4750e48962a008fd8f` |
| Input untracked set SHA-256 | `dea984371cb7e552dcf8bb338bd48c35541dac035d496b16122f5315f7ed0471` |
| Input combined dirty digest | `0e290688a8d378727434c842e4fe072fb197946c20c6dc07db0c7efe73ec0b63` |
| Draft.17 incremental input tracked diff SHA-256 | `2fcc177e3b51c7969f027e548ba5e25e18e88acffe9d28d3f74408bdd5bdf7dc` |
| Draft.17 incremental input untracked set SHA-256 | `4d022bcddb876c41f876b819b44f40e4c825551daa3425c2d96dcbf8ecefbb47` |
| Draft.17 stable input snapshot digest | `d179348ad0a4a1adedd4222fd496b0b772a6d5da7f9ba9c1f4c237a015b97d23` |
| STD repository | `corezilla/architecture-standards` |
| STD revision | `94c0262de35b5b989bba9f8d23f212af709c9dbf` |
| STD annotated tag | `std-v0.1.0-draft.17` |
| STD source artifacts | 71；见 `docs/std-source-manifest.json` |

候选 payload 明确由 lock、source manifest、tailoring、service design、inventory 和两份迁移/契约
一致性测试组成；不把 READY 前已有的 README、旧路径 deletion 或 legacy RAG source list 冒充为
本轮独占修改。上述 9 个文件逐文件 SHA-256 的有序清单摘要为
`0b0971550447bbffaf4738e1680ee77042e01dd5f9bd8eaa667ff915ef743f29`。逐文件摘要：

| Artifact | SHA-256 |
|---|---|
| `docs/std.lock.json` | `a6e019d1b87cc0d604c2de37f2c2cd6fb163d9e0d8f8265cc598e76c7f5e365c` |
| `docs/std-source-manifest.json` | `2b6150c4dfd0df543ff24faff7c76a70ec3bb7c7169b43ccb8fcafb4bb4974ec` |
| `docs/00_management/std-tailoring.md` | `fbe16332b8ea3b323d7513ea5bc54bc4c310e2808ba20c0d6c47e14886f87870` |
| `docs/00_management/std-tailoring.metadata.json` | `4886fa16b3780c73720ec62ecd1a0740d2c7e4b0a1cc7812296fb17c20deadfc` |
| `docs/30_subsystem_design/llmtier-service-design.md` | `58f5aa210175f72e697b454e6f81636bb5ba376a50fb8b8aa964084dd1b2ac02` |
| `docs/30_subsystem_design/llmtier-service-design.metadata.json` | `d6905895eb1b2132bd7989f0428ae2d519411e6c9200212ae402a6756552a27b` |
| `docs/98_migration/current-document-inventory.md` | `321b5f8e7b9d7e011983059410d7409015fd4f35635d4fdf58d0c674c83b3bdd` |
| `tests/test_contract_semantics_v03.py` | `f762c4e88e750be00010d7e87c2016b47e88b552ba765f6bf42328e6450a5fbd` |
| `tests/test_std_migration.py` | `11c6bf1bec9ff96e7b4515e3b13e4848da038323ada2f1056b27923abaccfee3` |

## 4. 变更摘要与设计理由

1. 在已完成的 draft.16 candidate 上增量升级 immutable draft.17 lock 和 71-artifact source manifest；
   tailoring、service design 和 review packet 的 cover/metadata/template version 同步升级，模板内容
   SHA-256 未变化。
2. 保留项目已确认的单服务根结构：`src/`、`tests/`、`tools/`、`docs/`；不建立
   `services/llmtier/`、`software/llmtier/`、`apps/` 或 `packages/` 平行 ownership。
3. draft.17 只改变 validator discovery/read robustness，不改变 LLMTier 的 project profile、enabled
   domains、authority、Contract、运行代码或 activation gate，因此无需重做迁移内容。
4. 取消候选对旧设计的整体 supersession 声明，改为等待 promotion 时按 scope 切换 authority。
5. READY 前已有 README、旧候选删除、legacy RAG source list 和测试修改均作为输入 dirty state
   保留；本轮没有 reset、clean 或把它们归属为全新迁移变更。
6. discovery 审计确认本项目应纳入的三个 STD Markdown candidate、三个 sidecar 和一个 decision
   均为未被 ignore 的普通非 symlink 文件；不存在应纳入却被 ignore 的 candidate、candidate
   symlink 或同后缀目录。deleted tracked 旧候选因当前不是普通文件而不进入 validator，符合其在
   输入 dirty worktree 中的既有 deletion 状态。

## 5. Requirement、Design、Contract、Test 对齐

| 范围 | Canonical/候选 artifact | 本轮关系 |
|---|---|---|
| 迁移规则 | `docs/00_management/std-tailoring.md` | keep/simplify/omit 与风险；不改变项目业务决定 |
| 服务设计 | `docs/30_subsystem_design/llmtier-service-design.md` | 承接服务 boundary、状态、恢复、容量、安全和 Gate；候选不切 authority |
| 字段级机器契约 | `docs/contracts/openapi/llmtier-v0.3.openapi.json` | 原位保留、未修改 |
| Activation authority | `docs/contracts/compatibility-manifest-v0.3.json` | 原位保留、runtime activation=false |
| 测试源码/fixtures | `tests/`、`docs/contracts/fixtures/v0.3/` | 保留机器 oracle；只更新迁移结构断言 |
| 运行证据 | production implementation/SLO/recovery/isolation evidence | 尚未提供；不因结构/契约测试 PASS 推导为 runtime evidence |

完整旧→新映射和 residual scope 见
`docs/98_migration/current-document-inventory.md`。

## 6. 风险、未决项和不阻塞项

- 终局 review 已完成：机器 decision 包含授权 reviewer、`decided_at`、rationale 和 immutable decision commit。
- canonical promotion 仍需独立的精确 pathspec、scope-level authority 切换与单一 current authority Gate。
- 阻塞项目 RAG publication：promotion commit 尚不存在；不得生成项目 ingestion manifest。
- 阻塞 runtime activation：production implementation、恢复、隔离、SLO、管理面和 Consumer evidence
  Gate 均未关闭；本 packet 不请求 activation。
- 非阻塞：输入 worktree dirty；已记录完整输入 digest，并以非破坏方式继续。

## 7. 验证命令与结果

以下三层记录均为本轮实际执行结果；所有命令均以
`/Users/ben/work/LLMTier` 为显式工作目录，不使用 `|| true` 包装退出码。

### 7.1 STD structural validation

- 原始命令：`python3 -m unittest discover -s tests`（workdir=`/Users/ben/work/STD`）
  - 原始 exit code：`0`
  - 关键输出：draft.17 validator discovery/read regression `Ran 2 tests`；`OK`
  - Artifact：STD `tests/test_validate_design.py`
  - 执行 STD commit：`94c0262de35b5b989bba9f8d23f212af709c9dbf`
- 原始命令：`/Users/ben/work/STD/scripts/verify-source-manifest /Users/ben/work/LLMTier/docs/std-source-manifest.json --std-root /Users/ben/work/STD`
  - 原始 exit code：`0`
  - 关键输出：`STD source manifest verification OK: 71 artifacts`
  - Artifact：`docs/std-source-manifest.json`
  - 执行 project commit：`8dc6a54c92608ab6373f40c78cc954da7086f30e`
- 原始命令：`/Users/ben/work/STD/scripts/validate-design --project-root /Users/ben/work/LLMTier --require-immutable-std --json /Users/ben/work/LLMTier/docs/98_migration/evidence/std-validation.json`
  - 原始 exit code：`0`
  - 关键输出：JSON `ok=true`、`new_error_count=0`、`inherited_error_count=0`、
    `checked_metadata=3`、`checked_markdown=3`、`checked_decisions=1`
  - Artifact：`docs/98_migration/evidence/std-validation.json`
  - 执行 project commit：`8dc6a54c92608ab6373f40c78cc954da7086f30e`

### 7.2 Project contract/schema validation

- 原始命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests`
  - 原始 exit code：`0`
  - 关键输出：`Ran 41 tests`；`OK`
  - Artifact：测试源码与 v0.3 OpenAPI/manifest/fixtures；未生成 runtime report
  - 执行 project commit：`8dc6a54c92608ab6373f40c78cc954da7086f30e`
- 原始命令：`git diff --check`
  - 原始 exit code：`0`
  - 关键输出：无 whitespace error
  - Artifact：当前 working-tree diff
  - 执行 project commit：`8dc6a54c92608ab6373f40c78cc954da7086f30e`

### 7.3 Runtime/external dependency evidence

本轮未执行 production runtime 或外部依赖测试，结果为 NOT_RUN。本结论是明确的 evidence gap，
不影响 Migration Review 的结构候选生成，但继续阻塞 Runtime Activation。

## 8. Review Checklist

- [x] scope 与 authority 清楚
- [x] 现状、批准变更和未来设想未混写
- [x] 接口、错误、状态和恢复保持原契约
- [x] 安全与隔离边界保持原设计
- [x] traceability 和机器 evidence 路径可打开
- [x] 未发生静默 fallback 或兼容性扩张
- [x] immutable project candidate commit 与授权 reviewer 已登记
- [ ] canonical promotion、RAG publication 与 runtime activation 已分别授权

## 9. 决定、条件与签署

机器 decision 见
`docs/91_reviews/llmtier-std-draft16-migration-review.review-decision.json` 记录终局 `ACCEPTED`。
Review Verdict、Document Status 与 Runtime Activation 继续分开。
