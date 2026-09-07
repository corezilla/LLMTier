# LLMTier C5 Canonical Promotion Readiness Inventory

盘点日期：2026-09-07
Promotion 输入：`e1f9b796368ec5f358e466c7e6299cc16b1bf181`
STD：`9841083c4d8d0ed1556bdc413d77b4567ac696b4` / `std-v0.1.0-draft.18`
结论：`READY_FOR_COMMIT` candidate；已构造原子 canonical-promotion diff，尚未提交或执行 RAG publication。

## 1. 完成度结论

- C0-C4 已分别冻结为四个 immutable candidate commits：`aa2638283e77bc658e98df8d40396306cad17aa2`、
  `b2e298aadf981283aa52d4764b201400397d1116`、`13b5d02266624b6b662349f0b88de23696c823bb`、
  `962e8003712738d2cb4e3a0a38173a9fd2bdd0a1`。
- 当前共有 11 份实质 STD 文档实例、5 份 C0-C4 review packet/terminal decision，以及 1 份 C5
  promotion packet/PENDING decision。C0-C4 decision 均为 `ACCEPTED`；11 份实质文档在本次原子 diff
  中升级为 Approved，并继续由 draft.18 lock/source manifest 约束。
- requirements、service design、三个 interface control、contract specification、V&V plan、test specification、
  release/operations 和 tailoring 已覆盖本轮约定的 management+software scope。
- 五份旧 V0.3 prose 的逐章节 old→new 证据见 `docs/98_migration/legacy-v03-scope-mapping.md`。
- LLMTier Owner 对 C0-C4 均为 ACCEPTED；Piko 与 Slinky consumer-boundary verdict 均可审计且为
  ACCEPTED，审查记录见 `docs/98_migration/evidence/c5-owner-verdicts.txt` 和 `c5-consumer-verdicts.txt`。
  STD reviewer 不替代 Owner authority。
- 当前没有必须补建的 ADR。persistence、HA、topology、RPO/RTO 等尚未决定的事项继续是 Open Gate，不能
  通过 promotion 倒推为已批准决定。
- production L3 证据仍为 NOT_RUN/BLOCKED；这不阻止批准一份诚实描述当前事实和缺口的文档，但继续
  阻止 Runtime Activation 和把 operations 文档当作 production runbook。

## 2. 拟 promotion 的当前 authority

| Authority scope | 拟 canonical artifact | 当前状态 | Promotion 动作 |
|---|---|---|---|
| adoption/tailoring | `docs/00_management/std-tailoring.md` | Approved candidate | `reviewed_commit=962e800...` |
| LLMTier requirements | `docs/10_requirements/llmtier-v0.3-requirements.md` | Approved candidate | Owner ACCEPTED；runtime gaps 保留 |
| requirement traceability | `docs/10_requirements/llmtier-v0.3-traceability.md` | Approved candidate | Owner ACCEPTED；blocked-runtime 状态保留 |
| service design | `docs/30_subsystem_design/llmtier-service-design.md` | Approved candidate | Owner ACCEPTED；旧 design prose Superseded |
| Piko consumer boundary | `docs/60_interfaces/piko-data-plane-control.md` | Approved candidate | Piko `P-20260907-e009921eda0a` ACCEPTED |
| Slinky consumer boundary | `docs/60_interfaces/slinky-capacity-observation-control.md` | Approved candidate | Slinky `S-20260907-45938693e578` ACCEPTED exact draft.2 |
| LLMTier management boundary | `docs/60_interfaces/llmtier-management-control.md` | Approved candidate | Owner ACCEPTED；实现 Open Gate 保留 |
| contract index | `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` | Approved candidate | 不复制机器字段 authority |
| verification strategy | `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` | Approved candidate | L3 gap 保持原样 |
| executable case specification | `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` | Approved candidate | tests/fixtures 仍是 oracle |
| release/operations boundary | `docs/80_operations/llmtier-v0.3-release-and-operations.md` | Approved candidate | 不等于 release/activation |

C0/C2/C3/C4 terminal decisions 使用包含其 exact reviewed content 的 integrated input `962e800...`；C1
terminal decision 使用包含 draft.2 Slinky control 与 revised C1 packet 的 clarification snapshot
`e1f9b796...`。STD 只审结构、来源、迁移完整性和切换规则；`ACCEPTED` 不授权 Runtime Activation。

## 3. 原位保留的机器与执行 authority

| Scope | Canonical artifact | Promotion 处置 |
|---|---|---|
| V0.3 字段、path、header、error、schema | `docs/contracts/openapi/llmtier-v0.3.openapi.json` | 原位保留为唯一字段级 authority；新文档只索引 |
| activation candidate | `docs/contracts/compatibility-manifest-v0.3.json` | 原位保留；`overall.runtime_activation=false` 不变 |
| V0.3 vectors | `docs/contracts/fixtures/v0.3/` | 原位保留为小型冻结 evidence/oracle |
| executable contract semantics | `tests/` | 原位保留为测试源码 authority |
| current implementation | `src/` | 原位保留；promotion 不修改 runtime/config/fallback/compatibility path |
| source provenance | `docs/migration/source-provenance-v0.1.md` | 保留为 migration provenance，不作为 current design authority |

## 4. 旧文档 residual-authority ledger

| Legacy scope | 当前 residual authority | Promotion 后处置 | 完成判据 |
|---|---|---|---|
| `docs/design/llmtier-v0.3-design-review.md` | 所有 current scope 已映射 | 本次整体 Superseded，保留 historical provenance | `legacy-v03-scope-mapping.md` §1；residual=none |
| 三份 `docs/contracts/*-v0.3.md` prose | 所有 current scope 已映射 | 本次整体 Superseded，保留 historical prose | `legacy-v03-scope-mapping.md` §2-§4；residual=none |
| `docs/qa/llm-tier-contract-qa-v0.3.md` | 所有 current scope 已映射 | 本次整体 Superseded，保留 historical review ledger | `legacy-v03-scope-mapping.md` §5；residual=none |
| V0.1/V0.2 prose、manifest、fixture、schema | historical/provenance only | 保留历史，不进入 current authority 或项目 RAG current set | README/manifest 明确排除，不删除 Git history |
| `docs/design/legacy-capability-audit-v0.1.md` | source-baseline evidence | 保留为 historical reference，排除 current RAG | service design 已承接当前边界；审计不被写成实现验收 |
| `docs/future/llmtier-v0.4-data-plane.md` | future/deferred scope | 保留 Future，排除 V0.3 current RAG | 不生成 inactive endpoint、fallback 或 V0.3 authority |
| `rag/std-ingestion-manifest.jsonl` | legacy draft.12 STD source list；且为既有 dirty | 不纳入 C5 promotion commit；新 project manifest 明确排除它 | 不覆盖/暂存当前 dirty，不把 STD source list冒充项目 publication |

逐 scope 盘点未发现未映射 current scope；Piko/Slinky auditable verdict 均已收齐且为 ACCEPTED。
五份旧 V0.3 文档在同一 promotion diff 中获得 Superseded forward link，单一 authority 检查由项目测试执行。

## 5. 独立 promotion 变更计划

1. 以本文件和 `docs/91_reviews/llmtier-std-c5-canonical-promotion-review.md` 为唯一 promotion review 输入。
2. 同一 diff 更新 11 份实质文档及 sidecar 的 Approved 状态、review fields 与稳定版本。
3. C0-C4 review decisions 已终局化为 `ACCEPTED`，填写授权 reviewer、决定时间、rationale 和实际
   immutable input；全部保持 `runtime_activation_requested=false`。
4. 同一 diff 更新 README canonical index，并给旧 V0.3 design/contract/QA prose 添加明确 Superseded
   标记和 successor links；历史、future、provenance、机器契约和 executable evidence 原位保留。
5. 运行 source verifier、project-root validator、项目全部测试、链接/单一 authority 检查和
   `git diff --check`；当前 candidate 在提交前等待 STD 精确 pathspec Gate。
6. promotion commit 推送后才生成 `rag/project-ingestion-manifest.jsonl`：纳入 Approved canonical 项目实例
   及其 publication commit，排除旧/历史/future/review candidate、legacy STD manifest 和 runtime evidence
   缺口。RAG publication 使用另一个 Gate。
7. Runtime Activation 始终保持独立；不得由 ACCEPTED、Approved、promotion commit 或 RAG publication 推导。

## 6. 当前 blockers 与请求决定

- 内容迁移 blocker：none。
- Promotion Gate blocker：none。Piko 与 Slinky verdict 均可审计且为 ACCEPTED，LLMTier Owner C0-C4
  terminal decisions 已记录。当前只等待 STD 对精确 allowlist/digest 的 pre-commit review。
- Publication blocker：需要 promotion commit 后的独立 RAG manifest review；当前 legacy RAG dirty 必须继续隔离。
- Runtime blocker：production L3 evidence 和独立 activation authority，明确不属于本次请求。
