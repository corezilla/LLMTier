<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier STD 裁剪清单

| 文档字段 | 值 |
|---|---|
| Document ID | `std-tailoring` |
| Document Version | `0.1.6-draft.3` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer |  |
| Approver |  |
| Approval Date |  |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-10-03` |
| Template Version | `0.2.0` |
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
- STD 采用来源由 README 与 `docs/std.lock.json` 管理；当前锁定 `0.1.0-draft.72` 开发行、完整 commit
  `f07339644221f694f38e7bdda63cf5364114599b`（含测试体系入口规范 `docs/test-standard.md`：分层总览、每层职责含**主要手段**、分层原则、通用规范 §6）
- 当前目录裁剪：正式 prose 使用编号化 `docs/`，机器契约集中到 `interfaces/`，历史/非权威资料
  集中到 `docs/99_reference/`；不改变 Scope B 或任何机器契约字节

## 2. 启用模板

| Template ID | Profile | 是否必需 | 计划文档 | Owner |
|---|---|---|---|---|
| `management.tailoring` | management | 是 | `docs/00_management/std-tailoring.md` | LLMTier |
| `management.development-plan` | management/software | 是，V0.3 implementation active | `docs/00_management/llmtier-implementation-plan.md`；编码调试与正式单元测试分Gate | LLMTier |
| `design.system` | software | omit | LLMTier 为纯软件单服务；顶层设计与系统概览改由 `design.software-system` 承担，不另建总体系统文档 | LLMTier |
| `design.software-system` | software | 是 | `docs/20_system_design/llmtier-system-design.md` | LLMTier |
| `design.system-mechanism` | software | 是 | `docs/20_system_design/mechanisms/`；端到端机制在系统概览之上的展开 | LLMTier |
| `design.subsystem` | software | 条件必需，当前 omit | 仅在 LLMTier 出现独立子系统时建立；当前所有模块归 `design.definition` | 对应 owner |
| `design.definition` | software | 是 | `docs/40_module_design/`与`docs/50_implementation_design/`；不建立虚构subsystem | LLMTier |
| `design.implementation` | software | **采用（separate）** | 模块设计**不兼作** ISD；每模块独立 ISD（`docs/50_implementation_design/<name>.isd.md`）。util 作首个试点 `util.isd.md` | 模块 owner |
| `requirements.specification` | software | 是，C3 active | `docs/10_requirements/llmtier-requirements.md` | LLMTier；外部需求 authority 不迁入 |
| `requirements.traceability` | software | 是，C3 active | `docs/10_requirements/llmtier-traceability.md` | LLMTier |
| `interfaces.control` | software | 是，C1 active | Data Plane、Observation、Management interface migration | LLMTier；消费边界由 Piko/Slinky reviewer 复核 |
| `contracts.specification` | software | 是，C1 active | OpenAPI/manifest/error/schema 说明层；机器文件在 `interfaces/` 保持唯一 authority | LLMTier |
| `assurance.vv-plan` | software | 已退役 | 见 §3 LT-TL-021；验收/validation 由 LT-TL-022 按 tailoring 承接，不在 tests 家族 | LLMTier |
| `assurance.test-plan` | software | 已退役 | 见 §3 LT-TL-020；迁移为 `tests.system-test-plan`（`docs/70_verification/system/llmtier-system-test-plan.md`） | LLMTier |
| `tests.system-test-scheme` | software | 是 | Case 清单唯一登记 | [llmtier-system-test-scheme](../70_verification/system/llmtier-system-test-scheme.md) | LLMTier |
| `tests.system-case` | software | 是 | 逐 Case 设计（一 Case 一文档） | `docs/70_verification/system/cases/<lowercased-case-id>.md` | LLMTier |
| `tests.system-test-plan` | software | 是 | 系统测试可执行作业指令 | [llmtier-system-test-plan](../70_verification/system/llmtier-system-test-plan.md) | LLMTier |
| `tests.system-test-report` | software | 是 | 系统 Run 报告；按 Run ID 存于 `tests/system/reports/<run-id>/` | `tests/system/reports/` | LLMTier |
| `tests.unit-test-scheme` | software | 是 | 单元 Case 清单唯一登记；本项目按授权合并 M001-M008 为一份（LT-TL-023） | [llmtier-unit-test-scheme](../70_verification/unit/llmtier-unit-test-scheme.md) | LLMTier |
| `tests.unit-case` | software | 是 | 单元逐 Case 设计（一 Case 一文档，共 66 份，按 VRC 一来源一 Case 并入覆盖洞新增与工具 Case） | `docs/70_verification/unit/cases/UT-<OBJ>-<NNN>.md` | LLMTier |
| `tests.unit-test-plan` | software | 是 | 单元测试可执行作业指令；本项目按授权合并 M001-M008 为一份（LT-TL-023） | [llmtier-unit-test-plan](../70_verification/unit/llmtier-unit-test-plan.md) | LLMTier |
| `tests.unit-test-report` | software | 是，首个 Run 已产出（Markdown 汇总待 Gate） | 首个 Run `run-20260930-01` 存于 `tests/unit/v03/reports/`（证据根见单元计划 §7 位置决定） | `tests/unit/v03/reports/` | LLMTier |
| `tests.asset-design` | software | 是（已建立 `llmtier-unit-fakes`） | 单元替身（`FakeAdapter`/`AppFixture`）契约与自检；`FakeResponse` 为各测试模块本地 stub（非本资产）；模块层复用同一资产 | `docs/70_verification/unit/assets/llmtier-unit-fakes.md` | LLMTier |
| `tests.module-test-scheme` | software | 是（新建） | 模块 Case 清单唯一登记；本项目按授权合并 M001-M008 为一份（LT-TL-025） | [llmtier-module-test-scheme](../70_verification/module/llmtier-module-test-scheme.md) | LLMTier |
| `tests.module-case` | software | 是（已建，68 份） | 模块逐 Case 设计（一 Case 一文档，按方案 §6 四层分母 91 条展开为 68 Case） | `docs/70_verification/module/cases/MT-<OBJ>-<NNN>.md` | LLMTier |
| `tests.module-test-plan` | software | 是（新建） | 模块测试可执行作业指令；本项目按授权合并 M001-M008 为一份（LT-TL-025） | [llmtier-module-test-plan](../70_verification/module/llmtier-module-test-plan.md) | LLMTier |
| `tests.module-test-report` | software | 是（首次执行时产出） | 模块 Run 报告；按 Run ID 存于 `tests/module/reports/<run-id>/` | `tests/module/reports/` | LLMTier |
| `assurance.test-specification` | software | 已退役 | 140-Case 权威清单已迁入 `tests.system-test-scheme` §3（见 LT-TL-019） | LLMTier |
| `assurance.test-procedure` | software | 已退役 | 单 Case 执行步骤现由 `tests.system-case` 承接 | LLMTier |
| `assurance.test-report` | software | 已退役 | 由 `tests.system-test-report` 承接；按 Run ID 存于 `tests/{level}/reports/<run-id>/` | LLMTier |
| `assurance.acceptance-plan` | software | deferred（不在 tests 家族） | release 前正式验收自动化计划；见 LT-TL-022 | LLMTier + Piko + Slinky |
| `assurance.acceptance-report` | software | deferred（不在 tests 家族） | 按 LT-TL-022，正式验收报告使用 `tests/acceptance/reports/` | LLMTier + Piko + Slinky |
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
| LT-TL-012 | STD 来源清单 / 项目 RAG ingestion | keep source manifest；RAG publication 独立 Gate | `docs/std-source-manifest.json` 记录 draft.34 的 196 个规范、模板、Schema 和工具 SHA-256；它不是 RAG manifest | 来源可校验；project ingestion 仍由既有 publication manifest 管理 | 本轮 review | N/A |
| LT-TL-013 | 多服务目录 `apps/`、`services/`、`packages/` | omit | 当前只有一个部署边界、一个服务 owner，根目录 `src/tests/docs` 已满足 STD | 过早分层会制造虚假 subsystem 与平行路径 | 用户已确认单服务 | ownership/deploy boundary 改变时重新 tailoring |
| LT-TL-014 | `operations.release` | keep，C4 complete | 当前 package/CLI 与 release/rollback/recovery Gate 需要集中，但 production procedure/evidence 尚不存在 | 文档被误作 production runbook；以 Approved/Blocked 和独立 activation Gate 控制 | Owner ACCEPTED；L3 blocked | topology/persistence 等实际决定形成时另建 ADR |
| LT-TL-015 | 顶层 `interfaces/` 与 `docs/99_reference/` | keep，C7 complete | HTTP/OpenAPI、compatibility、Schema 和 vectors 是多 consumer 机器 authority；历史 prose/future 不应继续占用非标准 `docs/contracts|design|qa|future` 路径 | 路径断链或双 authority | Owner ACCEPTED | 不适用 |
| LT-TL-016 | `config/`、`state/` 与 `src/<module>/` | keep | 单服务：配置、Secret、状态和 entry point 均由本仓库拥有；无须多服务 workspace。源码按 STD 0.1.0-draft.31 的 `src/<module>/`（本项目无软件子系统，故不用 `src/<subsystem>/<module>/`）分模块：`http_api`/`web_ui`/`inference`/`management`/`observability`/`libdiag`/`util`/`log` | 把历史 Slinky path 当成当前路径会造成双 authority | 用户 2026-09-24 指示；STD `0.1.0-draft.31`（`dbcf87a`） | ownership/deploy boundary 改变时重审 |
| LT-TL-019 | ~~`assurance.test-specification` 增补 §4 Common Mechanisms（共同机制）~~ → 已退役 | retired（随模板族退役） | STD `0.1.0-draft.56` 用 `tests.<level>-{test-scheme,test-design,test-plan,test-report}` 取代整个 `assurance.*` 家族。原 `llmtier-api-test-specification.md` / `llmtier-contract-test-specification.md` 的 140-Case 权威清单、定量覆盖模型与 Traceability 已迁入系统测试方案 [`llmtier-system-test-scheme`](../70_verification/system/llmtier-system-test-scheme.md)（§3 Case 清单唯一登记）；逐 Case 细节迁入 `tests.system-case`（`docs/70_verification/system/cases/<lowercased-case-id>.md`）。 | 旧项目的模板章节扩展不再适用；机制/环境共同契约改由 system-test-design/plan 承载 | 本轮 review | N/A |
| LT-TL-020 | ~~`assurance.test-plan`（`llmtier-test-plan.md`）~~ → 已退役 | retired（随模板族退役） | 该文原为 `assurance.test-plan`（invalid Template ID）。按 `template-selection.md`，项目级 runtime 端到端测试计划属 **system 层**，映射为 `tests.system-test-plan`：仍需要的内容（测试策略与覆盖模型、Test Types/Case Families、Entry/Exit 与 PASS/FAIL/BLOCKED/INVALID 判定口径、环境前置与证据规则、风险）已并入 [`llmtier-system-test-plan`](../70_verification/system/llmtier-system-test-plan.md)；Case 清单唯一登记在 `llmtier-system-test-scheme` §3；容量/耐久（原 ST-18/19/21）不在 tests 家族分母，转 scheme §4 Gap 由性能/运维专项承接。 | 双计划文档会造成 authority 漂移 | 本轮 review | N/A |
| LT-TL-021 | ~~`assurance.vv-plan`（`llmtier-vv-plan.md`）~~ → 已退役 | retired（随模板族退役） | 该文原为 `assurance.vv-plan`（invalid Template ID，vv-plan 已不存在）。按 `template-selection.md`：**正式验收不在 tests 家族**（"如何进行正式验收 → 验收活动，按项目 tailoring 承接"）。仍需要的 V&V 内容迁入系统测试方案/计划：verification 方法、测试层级与责任边界表、故障注入与恢复路径、判定与重测规则 → `llmtier-system-test-plan` §1/§3 与 `llmtier-system-test-scheme` §3–§4（其验收/validation 场景的承接见下方 LT-TL-022）。 | V&V 计划退役后若不显式承接验收，会造成"已验收"的误读 | 本轮 review | N/A |
| LT-TL-022 | 验收活动（acceptance / validation）承接 | **deferred（按 tailoring 承接，不在 tests 家族）** | 原 `assurance.vv-plan` 的 validation 目标（Piko 完整输入 text/tool loop、Slinky Memory 获得 embedding、Operator Web UI 一屏 tier 状态/CRUD/脱敏日志、服务恢复后分层确认）与验收判据**不属于 tests 家族**。按 `template-selection.md` 与 `repository-layout.md` §4.1.1，正式验收使用 `tests/acceptance/reports/<run-id>/`，报告模板由验收活动按项目 tailoring 选择；**当前 V0.3 candidate 阶段尚未启动正式验收**，系统测试 Gate 只给放行建议、不等于验收或上线授权。启动条件：真实 Piko / 真 Slinky Memory 联调可用且 `runtime_activation` 决策启动时。Owner：LLMTier + Piko + Slinky（consumer reviewer）。 | 把系统测试 PASS 误当客户验收，或把验收结论泄进 tests 家族 | 本轮 review | 启动验收时新增 ADR |
| LT-TL-023 | 单元测试方案/计划合并登记（`tests.unit-test-scheme`/`tests.unit-test-plan` 模板默认“单一模块/一模块一份”） | **tailored（合并为项目级一份，逐模块切片由 Case ID 前缀承担）** | `tests.unit-test-scheme` 模板要求绑定单一软件模块、`tests.unit-test-plan` 模板要求一模块一份。LLMTier 8 个模块（M001-M008）边界清晰，用户授权将单元层 Case 清单与作业编排合并为项目级一份，避免 8 份碎片文档；逐模块访问由 Case ID 前缀 `UT-API-*`/`UT-UI-*`/`UT-INF-*`/`UT-MGMT-*`/`UT-OBS-*`/`UT-DIAG-*`/`UT-UTIL-*`/`UT-LOG-*` 与来源列承担。合并只关登记位置，不改变 Case↔VRC 追溯。另：锁定模板 `tests.unit-case@2.3.2` 一 Case 一文档，本项目按“一个设计验证项（VRC）一个 Case”实现（当前 66 份，含覆盖洞新增与 2 个工具 Case），未按单个测试函数拆分为上百份。 | 8 份碎片文档造成清单漂移；或误按测试函数粒度产生大量无独立 Oracle 的 Case | 本轮 review | N/A |
| LT-TL-024 | 测试范围裁剪的**定稿 N/A**（系统方案 §4 与单元方案 §4 的收口） | **Tailored-N/A（不在 tests 家族；权威本表）** | 经代码/设计复核，以下条目按事实定稿（本表为其权威记录；各方案 §4 只引用本表）：①**浏览器/JS 宿主 → 已建立，RISK 关闭**——M002 `VRC-UI-001..006` 行为级与 M005 诊断页视觉子项（`VRC-OBS-001..005` 视觉部分）原登记为具名开放 RISK **`RISK-UI-EXEC-1`**（`UT-UI-001..010`/`UT-OBS-*` 仅做源码字符串契约，不执行 JS）。**本版已关闭**：引入真实浏览器 harness（headless Chrome over CDP，`tests/common/drivers/browser_driver.mjs`，node ≥ 22 内置 WebSocket，无 npm/下载）并在系统层新增真实执行 Case `ST-UI-001..010`（`tests/system/cases/ST-UI-001.py`，`-m ui`），在真实 DOM 与网络记录上执行 `VRC-UI-001..006` 与诊断页视觉子项；`UT-UI-*` 字符串契约保留为快速下位防线（权威登记见系统方案 §4、单元方案 §4、系统计划 §10-O6）。②**生产部署面**（`LT-SEC-003` TLS/SSO/MFA/CSRF、真实生产环境）——归验收活动（`LT-TL-022`）与运维手册，非 HTTP 黑盒分母。③**运维/恢复/容量活动**（`LT-OPS-003/004/005`、进程 crash/restart 恢复、备份/恢复演练、容量/耐久 FD/30min/50并发）——归运维手册与性能专项（`LT-TL-020`）。④**声明性/absence 约束**（`LT-PERF-003` 未测量不宣称 SLO、`LT-FUN-007`/`LT-INT-003`/`LT-REL-002` absence）——由静态契约与发布声明承接。⑤**上游模型答案质量**——内容非 Oracle（系统设计 §1）。⑥**实现/部署 Gate**（`LT-OPEN-03`）——设计已关闭、待部署证据。⑦**子系统测试级别**——无 `design.subsystem` 对象（`LT-TL-003`）。⑧**误报偏差**（OpenAPI `422`/probes `502`/Embeddings `provider_failure`）——经复核无偏差或已改声明对齐，无 Case 需要。 | 把 N/A 当 Gap 反复挂起，或误把视觉/运维活动写进运行层分母产生空 Case | 本轮 review | N/A |
| LT-TL-025 | 模块测试方案/计划合并登记（`tests.module-test-scheme`/`tests.module-test-plan` 模板默认“绑定单一软件模块/一模块一份”） | **tailored（合并为项目级一份，逐模块切片由 Case ID 前缀承担）** | `tests.module-test-scheme` 模板要求绑定单一软件模块、`tests.module-test-plan` 模板要求一模块一份。LLMTier 8 个模块（M001-M008）边界清晰，用户授权将模块层 Case 清单与作业编排合并为项目级一份，避免 8 份碎片文档（与单元层 **LT-TL-023** 同一处理方式）；逐模块访问由 Case ID 前缀 `MT-API-*`/`MT-UI-*`/`MT-INF-*`/`MT-MGMT-*`/`MT-OBS-*`/`MT-DIAG-*`/`MT-UTIL-*`/`MT-LOG-*` 与来源列承担（token 与单元方案一致，便于反查映射）。合并只关登记位置，不改变 Case↔VRC 追溯。模块层分母＝**四层**（方案 §6）：① 对外接口端到端行为 20 ＋ ② 内部分支 47 ＋ ③ 组合（判定表/配对）10 ＋ ④ 状态转换（迁移表）14 ＝ **91 条分母**，展开为 **68 个 Case**（方案 v0.1.0-draft.9；已全部建立并执行，报告 `llmtier-module-test-report-2026-10-02-04` 判 68/68 Case `PASS`）；8 个模块设计 §14 / ISD §9.1 的 33 个验证项（与单元层同一 VRC 集合）在本层只作**追溯**（附录 A），**不作分母**。测试边界＝整模块组装（内部单元真实、仅边界外替身，状态只经公开入口）。 | 8 份碎片文档造成清单漂移；或模块层退化为单元层复测 | 本轮 review | N/A |
| LT-TL-026 | 测试方案/计划工件文件名（STD test-standard §6.4 建议 `<stage>-test-scheme.md` / `<stage>-test-plan.md`，无独立前缀） | **tailored（保留项目前缀 `llmtier-<stage>-test-…`）** | 本项目自采用 STD 起即用 `llmtier-<stage>-test-scheme.md` / `llmtier-<stage>-test-plan.md`（如 `llmtier-unit-test-scheme.md`），与全仓设计/管理文档的项目前缀命名一致，且被 plan §7/报告与数百处交叉引用锚定。按 STD test-standard §6.4，scheme/plan「每阶段一份、用文件名 `<stage>-test-scheme.md` / `<stage>-test-plan.md` 引用」；本项目保留 `llmtier-` 前缀属**文件名裁剪**，Case 文件仍严格 `＝Case ID`（`UT-<OBJ>-<NNN>.py/.md`、`MT-…`、`ST-…`），**不改** Case 命名与工件落位。 | 若强制改名为无前缀会大面积断链且与项目文档命名惯例冲突；Case 命名不受影响 | 本轮 review | 若 STD 提供 scheme/plan 前缀的 project-namespace 机制则重审 |

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
| 2026-09-25 | draft.34 | draft.31–34：数据/接口/公共错误码统一、模块源码路径、ISD 编码就绪 | 见下 | `81e01c112676aea0814abcacbd3fc0cf461a10a0` |
| 2026-10-01 | draft.72 (`e424728`) | draft.72 `eef5c9d`：IT/ST case 脚本命名与报告结构对齐 UT/MT（`fix: MT review — reconcile support docs + template cross-refs`）；模块层测试方案/计划落地（LT-TL-025）；模板文件（`module-*`/`system-case`/`subsystem-case`/`unit-case`）哈希刷新，全项目 metadata `template_sha256` 同步 | 测试模板族 hash 更新 + 模块层新建 | `eef5c9d2e8f238d6884e84a85837565f5a4502f4` |
| 2026-10-02 | draft.72 (`eef5c9d`) | draft.72 `eaca6dc`：新增测试体系入口规范 `docs/test-standard.md`（分层总览、每层职责含**主要手段**、分层原则、通用规范 §6）；Case/工件命名与对象 ID 拆出至测试规范 §6.4（`software-object-identifiers.md` 收敛）；测试模板族清单指向测试规范 | 新增 `test-standard.md`，无模板哈希变化（仅 docs 变更）；本清单 §2 测试模板族与各方案/计划按主要手段复核 | `eaca6dcb9ca990bfb9b68ae1c08dfb5d9d4b5da9` |
| 2026-10-03 | draft.72 (`eaca6dc`) | draft.72 `f073396`：STD 重排 scheme 模板章节编号（1→8 连续，弃 1.5/1.6/1.7）并对账标题层级规则（叙述 ≤2 级、记录型 `#### N.N.N` 为锚点）；项目三层 scheme/plan/case 的章节引用随迁（方案 §1.5→§2、§3→§6、§4→§7、§5→§8；矩阵→§2.3；方法表→§2.4/§2.1/§2.2）；同版重锁附带修复 ST case 存量坏链（双 URL 尾巴与 §2.1/§2.4/§3.2/§4.8 悬空锚改指计划 §2/§3/§7 与方案 §6） | 模板仅叙述编号/空行变化、无字段语义变化；`verify-source-manifest` 通过 | `f07339644221f694f38e7bdda63cf5364114599b` |

**draft.26 tag → HEAD 变更要点**（22 commits）：
- `tests/` 子目录加 `unit/<module-id>/`、`{contract,integration,system,acceptance}/reports/`；测试报告（`assurance.test-report`）路径由 `docs/70_verification/reports/` 改为 `tests/{level}/reports/<run-id>/`
- `acceptance-report` 路径由 `docs/70_verification/acceptance/` 改为 `tests/acceptance/reports/`
- 新增启用模板候选：`design.software-system`、`design.subsystem`、`design.implementation`（按 §3 条件必需策略，当时 omit；后续 `design.implementation` 已改为**采用（separate）**，见 §2）
- 现有模板版本号提升：`design.definition` 2.1.1、`contracts.specification` 0.3.1、`interfaces.control` 0.3.1、`assurance.test-specification` 0.2.1 等（详见 `templates/catalog.json`）
- `path-policy.json` 升至 `0.2.0-draft.1`
- 新增 `ISD` 设计专项目录（`software/<component>/docs/isd/`）
- 大量软件/固件/FPGA 设计 strengthening 与示例补全（与 LLMTier 不直接相关）

**对本项目的影响**（已落地）：
- LLMTier 25 个 unit test 从 `tests/v03/` 与 `tests/` flat 重组为 `tests/unit/v03/` + `tests/contract/`（历史）
- **后续（STD `78876c9`，本版）**：可执行用例迁移到按 Case ID 命名的 STD 布局——单元 `tests/unit/cases/UT-<OBJ>-<NNN>.py`（文件名＝Case ID）、系统 `tests/system/cases/ST-<OBJ>-<NNN>.py`（含 `ST-UI-*`）、契约 `tests/contract/{api,schemas}/`、静态 `tests/static/documents/`；共享替身 `tests/common/fakes.py`、harness `tests/common/harness/`、浏览器驱动 `tests/common/drivers/browser_driver.mjs`、假上游 fixture `tests/fixtures/models/v03_fake_provider.py`。报告根维持 `tests/unit/reports/<run-id>/` 与 `tests/system/reports/<run-id>/`（见单元/系统测试计划 §7）。
- `tools/v03_smoke.py`（集成测试）→ `tests/integration/`
- `tools/v03_fake_provider.py`（测试 fixture）→ `tests/fixtures/models/v03_fake_provider.py`
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
`config/secrets/`、`state/`、`interfaces/`、`llm-tier-v03`。历史 Slinky 路径只可出现在
`docs/99_reference/` 或 provenance/evidence 中。本轮不改变机器契约或 Runtime Activation。
