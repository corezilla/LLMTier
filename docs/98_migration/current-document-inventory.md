# LLMTier 当前文档盘点与 STD 映射

盘点日期：2026-09-08
盘点基线：`9c554f79942bf574a2bddf5dc6110293d6b21240`
范围：项目 README、`docs/`、顶层 `interfaces/`、RAG manifests 和相关可执行测试。

输入工作树唯一既有 dirty 是 `rag/std-ingestion-manifest.jsonl`，binary diff SHA-256 为
`5ecf097f57ec627f36586218d14e8df036467c8466de59e06adc7553c6073234`。C7 保留其路径和字节，
不 reset、不 clean，也不把它纳入目录迁移 candidate。

## 1. 分类、Authority 与状态

- LLMTier 是 STD 所称的单应用、单服务或单库型软件项目；当前只有一个服务 owner、部署边界和
  release boundary，根目录 `src/`、`tests/`、`docs/` 是 canonical repository layout。
- 本仓库使用 `design.definition`、`design_level=subsystem` 表达 LLMTier 服务设计。此前
  `design.system` 把跨项目上下文误写为 LLMTier 所拥有系统，现已由本次候选替换。
- LLMTier 是本服务设计、接口实现和模型服务事实的 authority；Slinky 的 Project/Plan/IR/Scope
  决策与 Piko 的 Agent Runtime/adapter 事实仍由各自项目负责。
- V0.3 字段级机器接口 authority 是 `interfaces/openapi/llmtier-v0.3.openapi.json`；
  compatibility activation authority 是 v0.3 manifest。v0.1/v0.2 只作历史输入。
- 本次迁移不会把未实现能力提升为 accepted、released、Implemented、Verified 或 active。

## 2. 本轮 Migration Review cohort

| 路径 | 类型 | 状态 | 处置 |
|---|---|---|---|
| `docs/std.lock.json` | STD adoption lock | draft.18 immutable lock | 固定完整 commit SHA、annotated source tag、software profile 与 management/software domains |
| `docs/std-source-manifest.json` | STD 来源清单 | source evidence；非项目 ingestion | 保存 71 个 draft.18 规范/模板/Schema/工具 SHA-256 |
| `docs/00_management/std-tailoring.md` + metadata | `management.tailoring` | review candidate | 冻结单服务 profile 与裁剪理由 |
| `docs/30_subsystem_design/llmtier-service-design.md` + metadata | `design.definition` / subsystem | review candidate | 本轮主交付，承接原设计且不改业务契约 |
| `docs/98_migration/current-document-inventory.md` | migration inventory | review evidence | 当前文件；记录旧→新映射 |
| `docs/91_reviews/llmtier-std-draft16-migration-review.md` + metadata/decision | `review.packet` | C0 ACCEPTED | 汇总三层验证、authority 边界与后置 Gate |
| `docs/98_migration/llmtier-std-migration-plan.md` | phased migration plan | active | 定义 C0-C6 mapping、依赖、Owner Gate、residual authority 和完成标准 |
| `docs/60_interfaces/piko-data-plane-control.md` + metadata | `interfaces.control` | C1 draft candidate | 承接 Piko Data Plane/adapter consumer boundary；不复制 Piko runtime authority |
| `docs/60_interfaces/slinky-capacity-observation-control.md` + metadata | `interfaces.control` | C1 draft candidate | 承接 Observation/Seat consumer boundary；不复制 Slinky Project/Plan/IR authority |
| `docs/60_interfaces/llmtier-management-control.md` + metadata | `interfaces.control` | C1 draft candidate | 承接 LLMTier admin、安全、并发和 recovery management scope |
| `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` + metadata | `contracts.specification` | C1 draft candidate | 索引 OpenAPI/manifest/fixtures；机器 artifact 原位保持字段 authority |
| `docs/91_reviews/llmtier-std-c1-interface-contract-review.md` + metadata/decision | `review.packet` | C1 ACCEPTED | 固定 C1 mapping、consumer verdict、L1/L2 PASS 与 L3 NOT_RUN/BLOCKED |
| `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` + metadata | `assurance.vv-plan` | C2 draft candidate | 迁移 V0.3 strategy/Gate；区分 static 与 production evidence |
| `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` + metadata | `assurance.test-specification` | C2 draft candidate | 映射 case/fixture/oracle；tests/fixtures 仍为可执行 authority |
| `docs/91_reviews/llmtier-std-c2-assurance-review.md` + metadata/decision | `review.packet` | C2 ACCEPTED | 固定 C2 mapping、三层验证和 evidence boundary |
| `docs/10_requirements/llmtier-v0.3-requirements.md` + metadata | `requirements.specification` | C3 draft candidate | 只承接 LLMTier 自有 shall statements；外部需求仅引用 |
| `docs/10_requirements/llmtier-v0.3-traceability.md` + metadata | `requirements.traceability` | C3 draft candidate | 连接 requirement、design/contract、case 与实际 evidence 状态 |
| `docs/91_reviews/llmtier-std-c3-requirements-review.md` + metadata/decision | `review.packet` | C3 ACCEPTED | 固定 C3 authority、coverage 与三层验证 |
| `docs/80_operations/llmtier-v0.3-release-and-operations.md` + metadata | `operations.release` | Approved candidate | 承接当前 package/CLI 与 release Gate；production procedure/evidence 保持 BLOCKED |
| `docs/91_reviews/llmtier-std-c4-operations-review.md` + metadata/decision | `review.packet` | C4 ACCEPTED | 固定 operations scope、ADR omission 与 Open Gate |
| `docs/98_migration/canonical-promotion-readiness.md` | C5 authority/completion inventory | promoted at `503d0a0` | 列出 11 份 Approved、机器/执行 authority、旧文档 disposition 和 promotion 原子步骤 |
| `docs/98_migration/legacy-v03-scope-mapping.md` | C5 old→new mapping | promotion evidence | 五份旧 V0.3 文档逐章节映射；consumer verdict 均 ACCEPTED，residual=none |
| `docs/98_migration/evidence/c5-consumer-verdicts.txt` | C1 consumer audit ledger | Piko ACCEPTED / Slinky AMENDMENT | 记录 message ID、immutable commit/blob/hash、结论和 draft.2 re-review 条件 |
| `docs/91_reviews/llmtier-std-c5-canonical-promotion-review.md` + metadata/decision | `review.packet` | C5 review record | promotion 已在 `503d0a0` 完成；该 packet 不授权 RAG/runtime |
| `docs/91_reviews/llmtier-std-c6-rag-publication-review.md` + metadata/decision | `review.packet` | C6 review record | publication 已在 `9c554f7` 完成；Runtime Activation=false |
| `rag/project-ingestion-manifest.jsonl` | `llmtier-project-rag.v1` | published at `9c554f7` | 绑定 promotion commit `503d0a0` 的 11 份 Accepted prose authority |
| `docs/99_reference/design/llmtier-v0.3-design-review.md` | 原始 V0.3 设计 | Superseded | 全部 current scope 已迁出；保留 historical provenance |
| `rag/std-ingestion-manifest.jsonl` | legacy draft.12 STD source list | 既有 dirty 文件；非 draft.18 source manifest、非项目 ingestion | 本轮不修改、不装载；后续 promotion packet 决定 historical/exclusion |

错误候选 `docs/design/llmtier-v0.3-system-design.md` 与旧 tailoring 路径在 READY 输入工作树中已经
处于 tracked deletion。本轮只记录这一事实，不恢复、不覆盖，也不将 deletion 视为已批准的 authority
切换；Git 历史继续提供可追溯性。

## 3. 现有设计、接口与证据

| 路径/集合 | 状态 | STD 目标/处置 |
|---|---|---|
| `docs/99_reference/design/legacy-capability-audit-v0.1.md` | historical design input | 已归位；保留为 review/source-baseline evidence |
| `docs/98_migration/source-provenance-v0.1.md` | migration provenance | 已归位；不是 current design authority |
| `docs/99_reference/future/llmtier-v0.4-data-plane.md` | future/not implemented | 已归位；与 V0.3 current authority 分离 |
| `docs/99_reference/contracts/*-v0.1.md`、`*-v0.2.md` | historical/superseded | 已归位并排除 current 检索 |
| 三份 `docs/99_reference/contracts/*-v0.3.md` | Superseded prose | 已归位；current successor 位于 `docs/60_interfaces/` |
| `interfaces/openapi/llmtier-v0.3.openapi.json` | current machine authority/candidate | 顶层机器契约 canonical path |
| `interfaces/compatibility/compatibility-manifest-v0.3.json` | current activation authority；false | 顶层 compatibility canonical path |
| `interfaces/compatibility/compatibility-manifest-v0.1.json`、`v0.2.json` | historical/superseded | 保留历史机器记录 |
| `interfaces/schemas/llmtier-contracts-v0.2.schema.json` | historical，非 V0.3 authority | 保留历史 Schema，不由 V0.3 manifest 装载 |
| `interfaces/vectors/v0.2/` | historical evidence | 保留历史 vectors |
| `interfaces/vectors/v0.3/` | current candidate evidence | 顶层 machine/executable oracle path |
| `docs/99_reference/verification/llm-tier-contract-qa-v0.1.md`、`v0.2.md` | historical/superseded | 已归位并排除 current 检索 |
| `docs/99_reference/verification/llm-tier-contract-qa-v0.3.md` | Superseded | C2 assurance、traceability 与 review evidence 已承接全部 current scope；保留历史 review ledger |

## 4. 旧→新映射

| 旧 authority/内容 | 新候选/目标 | 本轮结果 |
|---|---|---|
| `docs/99_reference/design/llmtier-v0.3-design-review.md` | `docs/30_subsystem_design/llmtier-service-design.md` | 14 节及关联 requirements/interfaces 已覆盖全部 current scope；旧文件 residual=none，标为 Superseded candidate |
| `docs/design/llmtier-v0.3-system-design.md` | 不保留 | 错误的 `design.system` candidate 已删除，Git 历史可追溯 |
| `docs/management/std-tailoring-v0.1.md` | `docs/00_management/std-tailoring.md` | 升级 draft.12，并改为单服务 profile |
| 三份 v0.3 interface Markdown | `docs/60_interfaces/*-control.md` | C1 terminal ACCEPTED；新 controls 为 Approved candidate，旧 prose 为 Superseded candidate |
| OpenAPI/manifest/error/schema | `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` + 原机器文件 | C1 只建立说明与索引；字段级机器 authority 未改、不复制 |
| v0.3 QA 与 fixtures/tests | assurance templates + 原 evidence | QA prose 已迁移；tests/fixtures 继续保持 executable authority |
| `docs/99_reference/verification/llm-tier-contract-qa-v0.3.md` | `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` + `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` | C2/traceability/review evidence 已覆盖全部 current scope；旧 QA residual=none，标为 Superseded candidate |
| Matrix review ledger | `docs/91_reviews/llmtier-std-draft16-migration-review.md` | C0-C4 terminal decisions 已记录；原 Review ID 保留 |

## 5. 目录与迁移约束

1. 当前不创建 `software/llmtier/`、`services/llmtier/`、`apps/` 或 `packages/`。只有在出现多个
   独立部署、发布和 owner 单元时才重新 tailoring。
2. `docs/00_management/`、`docs/30_subsystem_design/`、`docs/91_reviews/` 和
   `docs/98_migration/` 是迁移与 Gate evidence 位置；authority 切换已由 promotion commit `503d0a0` 完成。
   Contract/QA/Provenance 已在 C7 一次性归位，不建立重复正文。
3. `docs/std-source-manifest.json` 是 draft.18 source lock；既有
   `rag/std-ingestion-manifest.jsonl` 仍是 legacy STD source-list dirty，明确排除且不修改。
   C6 新建 `rag/project-ingestion-manifest.jsonl`，只绑定 promotion commit `503d0a0` 的 11 份
   Accepted canonical prose，并记录 inclusion/exclusion、ACL 和 publication commit。
4. 业务 Contract/OpenAPI/Manifest/fixture 未因分类修正而改变；若后续发现必须改变冻结字段，需先
   报告冲突并走独立接口评审。
5. 源码 `src/` 与 runtime 配置不在 C7 写入范围；机器契约和 vectors 只移动路径、不改变字节，
   不引入新 runtime/config/fallback/compatibility path。

## 6. Canonical promotion 与后置 publication 边界

本 inventory 已随 C5/C6 完成状态及 C7 repository-layout candidate 更新：

1. LLMTier Owner terminal decisions 与 reviewed commits 已固定；
2. README、authority index、新旧文档状态及 residual-scope 映射在同一 diff 更新；
3. 五份旧文档全部 scope 已迁出，因此整体 Superseded；
4. C6 manifest 纳入 `503d0a0` 的 11 份 canonical prose，排除旧/历史/candidate 和 legacy
   STD source list，并验证 ACL、内容 hash、检索合约和单一 current authority；
5. runtime activation 始终保持 `false`，直至独立 authority 与 production evidence Gate 关闭。
6. C7 只改变 repository paths 与引用；提交后如需索引当前字节，另走 commit-bound RAG refresh。

## 7. C5 完整度与 residual-authority 结论

当前输入 HEAD `503d0a03fa92aeeb7657ce7ed54bab8b77efef34` 已完成 C5 canonical promotion，并固定
C0-C4 的 11 份实质 STD 文档和 Slinky draft.2 clarification。C0-C4 五份 terminal decision 均为
ACCEPTED。全量 scope、原位机器/执行 authority、旧 V0.3 prose successor、
historical/future/provenance exclusions 及后续 RAG 边界见
`docs/98_migration/canonical-promotion-readiness.md`。

逐章节盘点未发现未映射 current scope，证据见 `legacy-v03-scope-mapping.md`。Piko/Slinky consumer verdict
均具备 immutable commit/blob/SHA-256 与 ACCEPTED Matrix 证据，因此五份旧文件 residual=none，并在本次
原子 promotion 中整体标为 Superseded。V0.1/V0.2、legacy audit、V0.4 future 与 source provenance 继续保留，
但不进入 V0.3 current authority。
