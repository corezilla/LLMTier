<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier STD 裁剪清单

| 文档字段 | 值 |
|---|---|
| Document ID | `std-tailoring` |
| Document Version | `0.1.3-draft.3` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer |  |
| Approver |  |
| Approval Date |  |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.1.0` |
| Template ID | `management.tailoring` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/00_management/std-tailoring.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 适用背景

- 项目：`LLMTier`
- 生命周期阶段：V0.3 design/contract candidate；production implementation 尚未激活
- 产品类型：single-service software
- Repository model：单应用、单服务或单库；根目录使用 `src/`、`tests/`、`docs/` 和
  多 consumer 机器契约 authority `interfaces/`
- Runtime ownership：`config/` 和 `state/` 均属于 LLMTier；Piko/Slinky 只通过受控 HTTP contract 使用服务，
  不共享源码、配置文件、状态目录或进程生命周期
- 设计层级：`system`；表示本仓库拥有完整 LLMTier 软件系统。Slinky/Piko 是外部相邻项目，不用于
  把 LLMTier 降级为其内部 subsystem
- 安全或业务关键性：模型服务控制面和数据面；涉及 credential、跨 Client 隔离、容量与恢复
- STD 采用来源由 README 与 `docs/std.lock.json` 管理；当前锁定 `0.1.0-draft.26` 开发行、完整 commit
  `5a1e71f4e2baa6e6761b685e91deecbd58cf0649`（draft.26 tag 之后再 22 commits；`VERSION` 仍为 0.1.0-draft.26，尚未打新 annotated tag）
- 当前目录裁剪：正式 prose 使用编号化 `docs/`，机器契约集中到 `interfaces/`，历史/非权威资料
  集中到 `docs/99_reference/`；不改变 Scope B 或任何机器契约字节

## 2. 启用模板

| Template ID | Profile | 是否必需 | 计划文档 | Owner |
|---|---|---|---|---|
| `management.tailoring` | management | 是 | `docs/00_management/std-tailoring.md` | LLMTier |
| `management.development-plan` | management/software | 是，V0.3 implementation active | `docs/00_management/llmtier-implementation-plan.md`；编码调试与正式单元测试分Gate | LLMTier |
| `design.system` | software | omit | LLMTier 为纯软件单服务；顶层设计与系统概览改由 `design.software-system` 承担，不另建总体系统文档 | LLMTier |
| `design.software-system` | software | 是 | `docs/20_system_design/llmtier-system-design.md` | LLMTier |
| `design.subsystem` | software | 条件必需，当前 omit | 仅在 LLMTier 出现独立子系统时建立；当前所有模块归 `design.definition` | 对应 owner |
| `design.definition` | software | 是 | `docs/40_module_design/`与`docs/50_implementation_design/`；不建立虚构subsystem | LLMTier |
| `design.implementation` | software | 条件必需，当前 omit | 模块设计已包含实现细节（`docs/50_implementation_design/llmtier-runtime.isd.md`）；需要独立 ISD 时启用 | 对应 owner |
| `requirements.specification` | software | 是，C3 active | `docs/10_requirements/llmtier-requirements.md` | LLMTier；外部需求 authority 不迁入 |
| `requirements.traceability` | software | 是，C3 active | `docs/10_requirements/llmtier-traceability.md` | LLMTier |
| `interfaces.control` | software | 是，C1 active | Data Plane、Observation、Management interface migration | LLMTier；消费边界由 Piko/Slinky reviewer 复核 |
| `contracts.specification` | software | 是，C1 active | OpenAPI/manifest/error/schema 说明层；机器文件在 `interfaces/` 保持唯一 authority | LLMTier |
| `assurance.vv-plan` | software | 是，C2 candidate | V0.3 activation-gate V&V plan | LLMTier |
| `assurance.test-plan` | software | 是，C2 candidate | Runtime 端到端系统测试计划与策略；与 contract test specification 互补 | LLMTier |
| `assurance.test-specification` | software | 是，C2 candidate | Contract/SDK/recovery/isolation tests | LLMTier |
| `assurance.test-procedure` | software | 条件必需，当前 omit | 单次可复现 case 的逐步执行步骤文档；与 `tests/system/` 落地同步 | LLMTier |
| `assurance.test-report` | software | 条件必需，当前 omit | 测试实际发生什么；按最新 STD 路径存于 `tests/{level}/reports/<run-id>/`（与 case 同级，不集中到根 `tests/reports/`） | LLMTier |
| `assurance.acceptance-plan` | software | 条件必需，当前 omit | release 前正式验收自动化计划 | LLMTier + Piko + Slinky |
| `assurance.acceptance-report` | software | 条件必需，当前 omit | release 前正式验收报告；按最新 STD 路径存于 `tests/acceptance/reports/` | LLMTier + Piko + Slinky |
| `assurance.fpga-implementation-report` | software | omit | LLMTier 不拥有 FPGA；保留以备跨项目扩展 | N/A |
| `review.packet` | management/software | omit（迁移批次已完成） | 原迁移 review packet 记录已随版本演进删除；新的重大评审再按需建立 | 无 |
| `decisions.adr` | software | 条件必需 | persistence/HA/deployment 等新重大决定 | LLMTier |
| `operations.release` | operations/software | 是，C4 active | `docs/80_operations/llmtier-release-and-operations.md`；Open Gate 不伪造 | LLMTier |

## 3. 裁剪决定

| ID | 模板/章节 | keep / simplify / omit | 理由 | 风险 | 批准人 | ADR |
|---|---|---|---|---|---|---|
| LT-TL-001 | `design.system` 4.0.0 的 §1–6、§8、§10–15、§17–18 与既有 A-H 附录 | keep | LLMTier 是本仓库完整软件系统；系统概览、总体结构、运行流程、软件、数据、接口、可靠性、安全和验收均须覆盖 | 无 | 本轮 review | N/A |
| LT-TL-017 | `design.system` §7、§9、§16 | omit with rationale | `software-system` profile；本项目不拥有硬件、FPGA/专用处理单元、结构/热/工艺设计，正文保留章节及 N/A 依据 | 未来拥有硬件责任时需重新裁剪 | 本轮 review | ownership 变化时重新评审 |
| LT-TL-018 | 系统设计模板切换 `design.system` → `design.software-system` | keep（切换） | LLMTier 是纯软件、单服务、单进程项目；STD 规定纯软件项目顶层使用《软件系统设计说明书》`design.software-system`，不必另建重复的总体系统文档。原 `design.system` 文档非规范选择 | 需同步 tailoring、metadata 与 contract test；旧文档内容整体迁入新模板结构 | 用户 2026-09-22 指示 | N/A |
| LT-TL-002 | `design.system` deployment/physical detail | simplify | topology、DB、HA、RPO/RTO 尚未冻结，只记录当前单进程事实与 Open Gate | 选型不足阻塞 retention/recovery | Open Gate 保留 | 选型时新增 ADR |
| LT-TL-003 | `design.definition` / `docs/30_subsystem_design/` | keep module/ISD；omit subsystem | 当前仍无独立subsystem，但HTTP/SSE、provider adapter、Registry、Usage、Admin/Web UI已形成真实内部模块和实现边界 | 不设计会把事务与authority留到编码期；虚构subsystem同样有风险 | 用户2026-09-09单系统边界；三方2026-09-17整改 | 部署/owner边界变化时重审subsystem |
| LT-TL-004 | `requirements.specification` + `requirements.traceability` | keep，C3 complete | 独立 shall statements 与矩阵能分离 LLMTier 自有需求、外部输入、静态 evidence 和 runtime gap | 若复制外部需求会越权；由引用和 reviewer boundary 控制 | Owner ACCEPTED | N/A |
| LT-TL-005 | `design.hardware`/`design.fpga` | omit | 本项目无硬件/FPGA ownership；Provider/Local Deployment 是外部资源 | 无 | Owner ACCEPTED | N/A |
| LT-TL-006 | `interfaces.control` | keep，C1 complete | 三个 API 分面需保持独立 authority 与演进规则 | 旧 Markdown 已逐 scope 映射并 Superseded | Owner/consumer ACCEPTED | N/A |
| LT-TL-007 | `contracts.specification` | keep，C1 complete | OpenAPI、manifest、fixtures 保持机器可执行 authority | 不得转写出第二契约 | Owner ACCEPTED | N/A |
| LT-TL-008 | assurance templates | keep，C2 complete | Approved 文档与 runtime activation 必须由证据区分 | production execution report 尚未形成 | Owner ACCEPTED；L3 blocked | N/A |
| LT-TL-009 | `management.project-plan` | omit | 排期/资源管理不在本轮设计迁移范围，现无稳定计划基线 | 实施顺序不等于项目计划 | Owner ACCEPTED | N/A |
| LT-TL-010 | `decisions.adr` | simplify/按需 | 已有决定保留原 Matrix Review ID，不伪造 retrospective ADR | 决策分散 | Owner ACCEPTED | 新决定必须用 ADR |
| LT-TL-011 | 原设计与 v0.1/v0.2 历史材料 | keep | 不删除；统一移入 `docs/99_reference/`，inventory 标明 historical/superseded/future | 误检索历史语义 | Owner ACCEPTED | publication manifest 排除历史 |
| LT-TL-012 | STD 来源清单 / 项目 RAG ingestion | keep source manifest；RAG publication 独立 Gate | `docs/std-source-manifest.json` 记录 draft.26 的 75 个规范、模板、Schema 和工具 SHA-256；它不是 RAG manifest | 来源可校验；project ingestion 仍由既有 publication manifest 管理 | 本轮 review | N/A |
| LT-TL-013 | 多服务目录 `apps/`、`services/`、`packages/` | omit | 当前只有一个部署边界、一个服务 owner，根目录 `src/tests/docs` 已满足 STD | 过早分层会制造虚假 subsystem 与平行路径 | 用户已确认单服务 | ownership/deploy boundary 改变时重新 tailoring |
| LT-TL-014 | `operations.release` | keep，C4 complete | 当前 package/CLI 与 release/rollback/recovery Gate 需要集中，但 production procedure/evidence 尚不存在 | 文档被误作 production runbook；以 Approved/Blocked 和独立 activation Gate 控制 | Owner ACCEPTED；L3 blocked | topology/persistence 等实际决定形成时另建 ADR |
| LT-TL-015 | 顶层 `interfaces/` 与 `docs/99_reference/` | keep，C7 complete | HTTP/OpenAPI、compatibility、Schema 和 vectors 是多 consumer 机器 authority；历史 prose/future 不应继续占用非标准 `docs/contracts|design|qa|future` 路径 | 路径断链或双 authority | Owner ACCEPTED | 不适用 |
| LT-TL-016 | `config/`、`state/` 与 flat `src/` | keep | 当前项目是一个独立 Python 服务：配置、Secret、状态和 entry point 均由本仓库拥有；无须多服务 workspace | 把历史 Slinky path 当成当前路径会造成双 authority | 用户 2026-09-09 指示；本轮文档 review | ownership/deploy boundary 改变时重审 |

## 4. 禁止裁剪项

以下内容若适用，不得无理由删除：authority、接口、状态与数据所有权、失败恢复、安全、
验证方法、traceability、版本和来源证据。

本项目还不得删除或弱化：

- Slinky/Piko/LLMTier authority 与唯一 `Runtime -> Piko -> LLMTier` inference path；
- 无 Agent 会话状态的 OpenAI-compatible 网关边界：Piko 提供完整调用输入并拥有上下文与工具循环；
- exact-case Service Level ID、单一 Registry、单一 OpenAPI authority；
- 标准 Responses、Models、Embeddings 与统一 Token Usage；
- Provider/本地模型配置、内部并发保护、健康诊断、Secret 只写不读与 audit；
- 不恢复 SourceInstance、Seat、跨系统 capacity/claim、Invocation recovery、Cost 或业务 Session 语义；
- candidate 与 runtime activation=false 的区别；
- Current Baseline、Approved Delta 与 Future/Open Gate 的边界；
- 单服务 repo layout，不未经批准增加新机制、config path、selector、fallback 或并行实现。

## 5. Review 与生效

本文件与既有设计曾在 canonical promotion 中升级为 `accepted`。本轮把误分类的 service/subsystem design
改为 LLMTier system design；draft.26。

### 5.1 STD 升级记录

| 日期 | 从 | 到 | 变更要点 | commit |
|---|---|---|---|---|
| 2026-09-15 | (初始) | draft.26 | 首次采用 STD `software` profile | `f892b167b9fc7b8beb9dbdebb9209009d4334ce1` |
| 2026-09-19 | draft.26 (tag) | draft.26 + HEAD `5a1e71f`（22 commits，含 path-policy 0.2.0） | 见下 | `5a1e71f4e2baa6e6761b685e91deecbd58cf0649` |

**draft.26 tag → HEAD 变更要点**（22 commits）：
- `tests/` 子目录加 `unit/<module-id>/`、`{contract,integration,system,acceptance}/reports/`；测试报告（`assurance.test-report`）路径由 `docs/70_verification/reports/` 改为 `tests/{level}/reports/<run-id>/`
- `acceptance-report` 路径由 `docs/70_verification/acceptance/` 改为 `tests/acceptance/reports/`
- 新增启用模板候选：`design.software-system`、`design.subsystem`、`design.implementation`（按 §3 条件必需策略，当前 omit）
- 现有模板版本号提升：`design.definition` 2.1.1、`contracts.specification` 0.3.1、`interfaces.control` 0.3.1、`assurance.test-specification` 0.2.1 等（详见 `templates/catalog.json`）
- `path-policy.json` 升至 `0.2.0-draft.1`
- 新增 `ISD` 设计专项目录（`software/<component>/docs/isd/`）
- 大量软件/固件/FPGA 设计 strengthening 与示例补全（与 LLMTier 不直接相关）

**对本项目的影响**（已落地）：
- LLMTier 25 个 unit test 从 `tests/v03/` 与 `tests/` flat 重组为 `tests/unit/v03/` + `tests/contract/`
- `tools/v03_smoke.py`（集成测试）→ `tests/integration/`
- `tools/v03_fake_provider.py`（测试 fixture）→ `tests/fixtures/`
- `tools/contract_semantic_validator_v03.py` 保留在 `tools/`（operational validator，不是 test case）
- `tests/system/` 仍是空目录（M3 milestone，待 system test plan §5.1 落地）
项目采用升级只更新标准来源与模板字段，不回退或重新推导既有业务 approval。
`docs/std.lock.json` 锁定 STD 开发行 HEAD `5a1e71f`（draft.26 tag + 22 commits，2026-09-19 升级）的完整 commit SHA；该 commit 未打新 annotated tag，故 `source_tag` 为 null；
`docs/std-source-manifest.json` 保存 189 个来源 artifact 的 SHA-256（draft.26 为 75 个）。来源记录不等于项目 RAG
ingestion；Approved 不等于 Released，本轮 review verdict 也不授权 runtime activation。

重新评审触发条件：

1. STD immutable commit/tag 或 path/template policy 变化；
2. Slinky/Piko 修改 authority、Scope B、recovery 或 header/path contract；
3. production persistence/HA/deployment 形成 ADR；
4. 服务拆成多个独立部署/发布/owner 单元；
5. activation gate 关闭或重新打开；
6. 下一批接口、contract、assurance 或 repository layout 迁移。
7. LLMTier 内部形成真实 subsystem、module owner 或独立 deploy/release boundary。

2026-09-09 的独立项目文档维护统一采用当前路径和入口：`src/`、`config/settings.json`、
`config/secrets/`、`state/`、`interfaces/`、`llm-tier` 与 `llm-tier-cli`。历史 Slinky 路径只可出现在
`docs/99_reference/` 或 provenance/evidence 中。本轮不改变机器契约或 Runtime Activation。
