# LLMTier 当前文档盘点与 STD 映射

盘点日期：2026-09-07
盘点基线：`8dc6a54c92608ab6373f40c78cc954da7086f30e`
范围：项目 README 与 `docs/` 下人工/机器文档；源码和测试代码不列为设计文档。

输入工作树：dirty；tracked diff SHA-256
`1887324d647667196f4a38db2eb1f002e826fae714834a4750e48962a008fd8f`，untracked content set
SHA-256 `dea984371cb7e552dcf8bb338bd48c35541dac035d496b16122f5315f7ed0471`，组合 digest
`0e290688a8d378727434c842e4fe072fb197946c20c6dc07db0c7efe73ec0b63`。本轮保留这些既有修改，
不 reset、不 clean，也不把它们冒充为本轮独占变更。

## 1. 分类、Authority 与状态

- LLMTier 是 STD 所称的单应用、单服务或单库型软件项目；当前只有一个服务 owner、部署边界和
  release boundary，根目录 `src/`、`tests/`、`docs/` 是 canonical repository layout。
- 本仓库使用 `design.definition`、`design_level=subsystem` 表达 LLMTier 服务设计。此前
  `design.system` 把跨项目上下文误写为 LLMTier 所拥有系统，现已由本次候选替换。
- LLMTier 是本服务设计、接口实现和模型服务事实的 authority；Slinky 的 Project/Plan/IR/Scope
  决策与 Piko 的 Agent Runtime/adapter 事实仍由各自项目负责。
- V0.3 字段级机器接口 authority 是 `docs/contracts/openapi/llmtier-v0.3.openapi.json`；
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
| `docs/91_reviews/llmtier-std-draft16-migration-review.md` + metadata/decision | `review.packet` | PENDING candidate | 汇总三层验证、authority 边界与后置 Gate |
| `docs/98_migration/llmtier-std-migration-plan.md` | phased migration plan | active | 定义 C0-C6 mapping、依赖、Owner Gate、residual authority 和完成标准 |
| `docs/60_interfaces/piko-data-plane-control.md` + metadata | `interfaces.control` | C1 draft candidate | 承接 Piko Data Plane/adapter consumer boundary；不复制 Piko runtime authority |
| `docs/60_interfaces/slinky-capacity-observation-control.md` + metadata | `interfaces.control` | C1 draft candidate | 承接 Observation/Seat consumer boundary；不复制 Slinky Project/Plan/IR authority |
| `docs/60_interfaces/llmtier-management-control.md` + metadata | `interfaces.control` | C1 draft candidate | 承接 LLMTier admin、安全、并发和 recovery management scope |
| `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` + metadata | `contracts.specification` | C1 draft candidate | 索引 OpenAPI/manifest/fixtures；机器 artifact 原位保持字段 authority |
| `docs/91_reviews/llmtier-std-c1-interface-contract-review.md` + metadata/decision | `review.packet` | C1 PENDING | 固定 C1 mapping、hash、L1/L2 PASS 与 L3 NOT_RUN/BLOCKED |
| `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` + metadata | `assurance.vv-plan` | C2 draft candidate | 迁移 V0.3 strategy/Gate；区分 static 与 production evidence |
| `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` + metadata | `assurance.test-specification` | C2 draft candidate | 映射 case/fixture/oracle；tests/fixtures 仍为可执行 authority |
| `docs/91_reviews/llmtier-std-c2-assurance-review.md` + metadata/decision | `review.packet` | C2 PENDING | 固定 C2 mapping、三层验证和 residual evidence boundary |
| `docs/10_requirements/llmtier-v0.3-requirements.md` + metadata | `requirements.specification` | C3 draft candidate | 只承接 LLMTier 自有 shall statements；外部需求仅引用 |
| `docs/10_requirements/llmtier-v0.3-traceability.md` + metadata | `requirements.traceability` | C3 draft candidate | 连接 requirement、design/contract、case 与实际 evidence 状态 |
| `docs/91_reviews/llmtier-std-c3-requirements-review.md` + metadata/decision | `review.packet` | C3 PENDING | 固定 C3 authority、coverage 与三层验证 |
| `docs/design/llmtier-v0.3-design-review.md` | 原始 V0.3 设计 | retained current residual-scope authority | 在 scope-level canonical promotion 前不删除、不整体 Supersede |
| `rag/std-ingestion-manifest.jsonl` | legacy draft.12 STD source list | 既有 dirty 文件；非 draft.18 source manifest、非项目 ingestion | 本轮不修改、不装载；后续 promotion packet 决定 historical/exclusion |

错误候选 `docs/design/llmtier-v0.3-system-design.md` 与旧 tailoring 路径在 READY 输入工作树中已经
处于 tracked deletion。本轮只记录这一事实，不恢复、不覆盖，也不将 deletion 视为已批准的 authority
切换；Git 历史继续提供可追溯性。

## 3. 现有设计、接口与证据

| 路径/集合 | 状态 | STD 目标/处置 |
|---|---|---|
| `docs/design/legacy-capability-audit-v0.1.md` | current design input | `review.packet` evidence；保留 |
| `docs/migration/source-provenance-v0.1.md` | current provenance | 后续迁入 `docs/98_migration/` 时另行 review；本轮不扩大改动 |
| `docs/future/llmtier-v0.4-data-plane.md` | future/not implemented | 后续 design/contract；与 V0.3 current authority 分离 |
| `docs/contracts/*-v0.1.md`、`*-v0.2.md` | historical/superseded | 后续归档并排除 current 检索 |
| 三份 `docs/contracts/*-v0.3.md` | current candidate/not active | 后续迁为 `interfaces.control` |
| `docs/contracts/openapi/llmtier-v0.3.openapi.json` | current machine authority/candidate | 原位保留；后续补 `contracts.specification` 说明层 |
| `docs/contracts/compatibility-manifest-v0.3.json` | current activation authority；false | 原位保留 |
| `docs/contracts/compatibility-manifest-v0.1.json`、`v0.2.json` | historical/superseded | 后续归档 |
| `docs/contracts/schemas/llmtier-contracts-v0.2.schema.json` | historical，非 V0.3 authority | 后续归档，不装载到 V0.3 manifest |
| `docs/contracts/fixtures/v0.2/` | historical evidence | 后续归档 |
| `docs/contracts/fixtures/v0.3/` | current candidate evidence | assurance migration 前原位保留 |
| `docs/qa/llm-tier-contract-qa-v0.1.md`、`v0.2.md` | historical/superseded | 后续归档 |
| `docs/qa/llm-tier-contract-qa-v0.3.md` | current candidate evidence | C2 assurance 候选已承接 strategy/case mapping；promotion 前继续承担历史 review ledger 与 residual evidence |

## 4. 旧→新映射

| 旧 authority/内容 | 新候选/目标 | 本轮结果 |
|---|---|---|
| `docs/design/llmtier-v0.3-design-review.md` | `docs/30_subsystem_design/llmtier-service-design.md` | 按 `design.definition` 14 节形成候选；只覆盖服务 boundary、职责、状态、恢复、容量、安全、实现映射和验证 scope。旧文件继续负责原始 review 结论、跨项目输入和其他 residual scope；本轮不切换 authority |
| `docs/design/llmtier-v0.3-system-design.md` | 不保留 | 错误的 `design.system` candidate 已删除，Git 历史可追溯 |
| `docs/management/std-tailoring-v0.1.md` | `docs/00_management/std-tailoring.md` | 升级 draft.12，并改为单服务 profile |
| 三份 v0.3 interface Markdown | `docs/60_interfaces/*-control.md` | C1 draft candidate 已形成；旧文档继续说明 residual authority，等待独立 review/promotion |
| OpenAPI/manifest/error/schema | `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` + 原机器文件 | C1 只建立说明与索引；字段级机器 authority 未改、不复制 |
| v0.3 QA 与 fixtures/tests | assurance templates + 原 evidence | 未迁移；现有静态证据继续有效 |
| `docs/qa/llm-tier-contract-qa-v0.3.md` | `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` + `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` | C2 形成计划与 case 候选；旧 QA、tests、fixtures 分别保留 residual ledger 与 executable authority |
| Matrix review ledger | `docs/91_reviews/llmtier-std-draft16-migration-review.md` | 本轮生成 PENDING packet；原 Review ID 保留，等待独立 reviewer 决定 |

## 5. 目录与迁移约束

1. 当前不创建 `software/llmtier/`、`services/llmtier/`、`apps/` 或 `packages/`。只有在出现多个
   独立部署、发布和 owner 单元时才重新 tailoring。
2. `docs/00_management/`、`docs/30_subsystem_design/`、`docs/91_reviews/` 和
   `docs/98_migration/` 是本批候选位置；在 canonical promotion 前不得称为已切换的项目 authority。
   原 Contract/QA/Provenance 的批量搬迁留待后续评审，避免无关路径 churn。
3. `docs/std-source-manifest.json` 是 draft.18 source lock；既有
   `rag/std-ingestion-manifest.jsonl` 仍是 legacy draft.12 记录。当前不生成
   `rag/project-ingestion-manifest.jsonl`，不把候选实例加入项目 RAG；只有 canonical promotion
   后才确定 inclusion/exclusion 和 publication commit。
4. 业务 Contract/OpenAPI/Manifest/fixture 未因分类修正而改变；若后续发现必须改变冻结字段，需先
   报告冲突并走独立接口评审。
5. 源码 `src/`、机器契约、fixtures 与 runtime 配置均不在本 cohort 的写入范围；本轮只调整文档、
   adoption metadata 和迁移一致性测试，不引入新 runtime/config/fallback/compatibility path。

## 6. Canonical promotion 与后置 publication 边界

本 packet 若获得 ACCEPTED，只代表固定迁移候选通过 review，不自动提升 Document Status。后续仍需：

1. 固定被 review 的项目 commit，并由 LLMTier owner 作出独立文档批准；
2. 按 scope 同时更新 README、authority index、新旧文档状态及 residual-scope 映射；
3. 只有全部 scope 迁出后才整体 Supersede 旧设计；否则旧设计继续承担明确 residual scope；
4. promotion 后生成项目 RAG manifest，纳入新的 canonical commit，排除旧/历史/候选和 legacy
   STD source list，并验证单一 current authority；
5. runtime activation 始终保持 `false`，直至独立 authority 与 production evidence Gate 关闭。
