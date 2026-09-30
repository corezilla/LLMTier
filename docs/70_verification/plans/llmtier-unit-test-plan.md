<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Unit Test Plan

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-unit-test-plan` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.unit-test-plan` |
| Template Version | `0.9.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | llmtier-implementation-plan |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-unit-test-plan.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本计划绑定软件模块集合：本计划编排 8 个软件模块 `M001-M008`（模块切片与 Case ID 前缀见 §1）；`design_object_id` 为本项目元数据可选字段，本计划 metadata 未写入该字段（合并计划跨 8 模块，单一 `design_object_id` 无法承载），模块归属改由 §1 构成表模块切片与 §5 批次承担；ISD 基线在 §2 固定。
> **裁剪说明（tailored）**：模板默认“一模块一份计划”。本项目按用户授权将 8 个模块的单元层活动编排为一份项目级可执行作业指令（`M001-M008` 一次编排，LT-TL-023）；逐模块差异由 §1 构成表的模块切片、§5 的执行批次与 Case ID 前缀（`UT-API-*`/`UT-UI-*`/`UT-INF-*`/`UT-MGMT-*`/`UT-OBS-*`/`UT-DIAG-*`/`UT-UTIL-*`/`UT-LOG-*`）承担。裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 模板定位：方案、用例、计划与报告的边界

- **权威分工**：Case 清单归 `tests.unit-test-scheme`；单 Case 展开归 `tests.unit-case`（一 Case 一文档）；本计划是**可执行作业指令**——执行者（含 Agent）按它从执行前检做到报告产出；执行结果与 Verdict 权威在 `tests.unit-test-report` 与 Run 证据。
- **只索引**：构成表引用方案版本与 Case ID 范围，不复制清单或 Case 细节。
- **测试资产**：工具/夹具/替身/受控时钟的契约与自检在 `tests.asset-design`（一资产一文档，阶段共享）；本计划 §5 Step 0 使其就位。
- **不是授权书**：按用户当前授权交付；计划到期不改判任何事实状态。

### 计划条目状态语义

| 条目状态 | 含义 | 禁止 |
|---|---|---|
| `Planned` | 已排入计划，方案与责任已定位 | 用 Planned 冒充已执行或已通过 |
| `Deferred` | 经批准裁剪或延后，有 tailoring 依据与恢复条件 | 无依据的“暂不做” |
| `Blocked` | 依赖缺失（设计缺口、环境、上游合同） | 不登记缺口就长期挂起 |

任一条目能报出状态、依据与下一步；计划里没有任何执行结论。

## 1. 目标、范围与测试构成

- 验证对象：LLMTier 8 个软件模块（M001 `http-api`、M002 `web-ui`、M003 `inference`、M004 `management`、M005 `observability`、M006 `libdiag`、M007 `util`、M008 `log`）的单元层行为与错误分支；**不证明**组装后进程级流程、wire 互操作、OpenAPI 端到端一致性、浏览器 E2E 与真实上游 provider 协议（见方案 §1）。
- 构成＝单元方案×1 ＋ Case 文档×N（一 Case 一文档）＋ 测试资产（tests.asset-design）＋ 相邻层交接出口。分母＝8 模块设计 §14 / ISD §9.1 声明的 33 个验证项（展开为 64 个 Case，方案 §3）；清单唯一登记于方案 §3，本表只索引。
- 排除项及 tailoring 依据：性能/耐久归系统层；模块组装归 `tests.module-test-scheme`/`-plan`；真实 provider 协议与 E2E 归 `llmtier-system-test-scheme`。依据见方案 §2/§4 与 [STD 裁剪清单](../../00_management/std-tailoring.md)。

| 构成层 | 文档 / 入口（Document ID 或缺口） | 覆盖责任摘要 | 条目状态 |
|---|---|---|---|
| 单元方案 ×1 | `llmtier-unit-test-scheme` v0.1.0-draft.3（方案 §3 清单；§1.6/§1.7 环境类型） | 8 模块 33 VRC（64 Case）的清单与设计状态唯一登记 | Planned |
| Case 文档 ×64 = ×33 已建 + ×31 待建 | 已建：`UT-API-001…004`、`UT-UI-001…006`、`UT-INF-001…005`、`UT-MGMT-001…006`、`UT-OBS-001…005`、`UT-DIAG-001…004`、`UT-UTIL-001…002`、`UT-LOG-001`；待建见方案 §5（`docs/70_verification/specifications/unit-case-*.md`） | 逐 Case 输入构造、Oracle 与运行入口；见方案 §3 每行责任摘要 | Planned |
| 测试资产 ×1（候选） | `tests.asset-design`（`FakeAdapter`，候选 ID `FAKE-LLMTIER-ADAPTER`）；缺口 G-UT-2。`FakeResponse` 为各测试模块本地 stub，非共享资产，不单列 | 上游进程内 fake 的契约与自检 | Blocked（G-UT-2） |
| 相邻层交接出口 | `tests.module-test-scheme`/`-plan`（组装后流程）、`llmtier-system-test-scheme`（wire/E2E） | 组合保证与验收承接 | Planned |

## 2. 被测基线与变更重跑范围

- 设计 / 源码 / 依赖基线：模块设计 M001 `http-api` v0.1.0-draft.2、M002 `web-ui` v0.1.0-draft.2、M003 `inference` v0.1.0-draft.1、M004 `management` v0.1.0-draft.2、M005 `observability` v0.1.0-draft.6、M006 `libdiag` v0.1.0-draft.6、M007 `util` v0.1.0-draft.1、M008 `log` v0.1.0-draft.1；对应 ISD `*-isd` 同版本（版本固定见方案 §1.5）。
- artifact 基线 pin（执行时在 Run 记录中固化，禁止在文档正文伪造自身 commit）：被测源码 `src/<module>/`（`http_api`/`web_ui`/`inference`/`management`/`observability`/`libdiag`/`util`/`log`）的 git commit；落库 `schema`/`migrations/` 版本；OpenAPI/错误码事件子集版本（`interfaces/`）。
- 运行时不变量：Python 3.14（`python3 -m pytest`），`PYTHONPATH=src`；测试框架 `pytest`；无外部服务依赖（provider 以进程内 fake 替代，见方案 §1.6/§1.7）。
- 变更 → 重跑范围规则：
  - 模块公开入口签名变化（如 `Registry.update_service_level`、`ResponsesService.create`）→ 该模块方案重裁 ＋ 该模块全部 Case 重跑。
  - 落库 schema / `migrations/` 变化 → `UT-UTIL-001/002` 及一切依赖落库的 Case 全量重跑。
  - 错误码 / OpenAPI 事件子集变化 → `UT-API-*`、`UT-INF-*`、`UT-DIAG-*`、`UT-OBS-*` 受影响 Case 重跑并回溯设计修订。
  - 私有 helper 重构（不改公开行为）→ 仅受影响 Case 复跑。
  - 重跑生成新 Run 与新报告，不覆盖旧失败。

## 3. 执行前检（Go / No-Go）

> ENV 状态统一字段：本节「环境与工具」前检与 §5 Step 0 共享同一个“ENV 状态”变量——本节判定 Go/No-Go 后 ENV 状态置为 Ready/Blocked；§5 Step 0 按消费方索引构建 ENV 实例并跑 self-check（assets 的 Verified）；§8 报告产出读取此 ENV 状态字段；不在本节与 §5 重复定义同义词。

| 前检项 | 判定事实 | 通过条件 | 不满足时 |
|---|---|---|---|
| 方案就绪度 | `llmtier-unit-test-scheme` v0.1.0-draft.3；64 Case 清单（33 VRC）均登记；缺口 G-UT-1/G-UT-2/G-UT-3/G-UT-4 已登记（G-UT-3/G-UT-4 见方案 §4） | 分母闭合且版本固定 | Blocked＋登记缺口 |
| Case 文档盘点 | 33 个 unit-case 文档已建（`docs/70_verification/specifications/unit-case-UT-*.md`），均记录测试代码位置于 `tests/unit/v03/*.py`（§7），并**自述** `Implemented`；但其中部分 §7 映射为近似映射（如 `UT-UI-005` 映射 `test_stats_page_present`/`test_diagnostics_page` 与其 VRC 责任不完全对应，且 case 文档自带"若与设计 VRC 不一致，以设计修订回溯后重裁"免责）→ 前检不得将近似映射一律当已实现；方案 §5 列出的 31 个新 Case 文档待建（未建前不得称 `Implemented`） | 已建 Case 有可定位的测试函数，近似映射逐条登记待回溯；待建 Case 先入清单 | 未能对应到测试函数或映射待回溯的 Case 标 NOT_RUN＋登记原因；待建 Case 标 NOT_RUN |
| 环境与工具（引用 tests.asset-design 的 Verified 状态） | `PYTHONPATH=src python3 -m pytest tests/unit/v03 -q` 可收集并执行（当前收集 197 个测试）；`tests/unit/v03/fakes.py` 仅定义 `AppFixture`/`FakeAdapter`（**无 `FakeResponse`**；`FakeResponse` 是 `test_account_usage.py`/`test_provider_openai.py` 各自的本地 stub）；替身资产 `tests.asset-design` 未建（G-UT-2） | 全量单元可收集执行且替身契约就位 | 收集失败或 Python/pytest 缺失→环境性 Blocked；替身契约缺→登记 G-UT-2，不静默用它物 |
| 构建接线 / 隔离确认 | 单元层**不需要** LAN / m5air / 真实 provider / 真实端口路由；HTTP 测试仅绑 loopback `127.0.0.1:0` 临时端口（ENV-2），provider 用进程内 `FakeAdapter`（ENV-3）；无 `PYTHONPATH=src` 外依赖 | 全量单元在本机隔离可运行，无 LAN 依赖 | 需外部服务→不属单元层，退回模块/系统层登记 |

## 4. 环境实例分配（plan 编排）

> ENV 实例类型与方案 §1.7 一致；编号在本表唯一登记。ENV-1/ENV-2 为真实实现（无替身契约），ENV-3 为进程内 fake（契约待建 G-UT-2）。
> **裁剪声明**：pinned 计划 §3.5 的 ENV 表含「契约校验（Verified/降级原因）」列；本项目 ENV-1/ENV-2 为真实依赖（无 tests.asset-design 契约文档），仅 ENV-3 有资产契约，故本表以「状态」列（Ready/Blocked）承载校验结论，不单列契约校验列——此为已声明的裁剪，非遗漏；ENV-3 契约就位后其 Verified 结论写入 §5 Step 0 就绪清单。

| ENV 实例编号 | 环境类型 | 契约文档引用（tests.asset-design） | 具体配置/位置 | Owner | 分配给哪些 Case | 准备时限 | 状态 |
|---|---|---|---|---|---|---|---|
| ENV-1 | 隔离 Python 临时库 | 不适用（真实依赖） | `tempfile.TemporaryDirectory` + `Application`（`tests/unit/v03/fakes.py::AppFixture`）；`setUp` 建、`tearDown.close()` 销毁 | LLMTier | `UT-*` 全部（默认环境） | 每次执行前 | Ready |
| ENV-2 | loopback 测试 HTTP 实例 | 不适用（真实 socket） | `ThreadingHTTPServer((127.0.0.1, 0), handler_factory(app))`（仅 `test_diagnostics.py`、`test_app_startup.py` 使用 `ThreadingHTTPServer`/`handler_factory`） | LLMTier | 实际消费 `ThreadingHTTPServer`/`handler_factory` 的 Case：`UT-DIAG-004`（HTTP 注入契约类）、`UT-OBS-004`（HTTP cursor 契约）；`UT-MGMT-001` 的 `test_app_startup.py::test_handler_factory` 亦属 ENV-2 | 每次执行前 | Ready |
| ENV-3 | provider 进程内 fake | 待建（G-UT-2；候选 ID `FAKE-LLMTIER-ADAPTER`） | `tests/unit/v03/fakes.py::FakeAdapter`（`FakeResponse` 为各测试模块本地 stub，不在此） | LLMTier | `UT-INF-001…005`、`UT-MGMT-005`、`UT-MGMT-006` | 替身文档建立前 | Blocked（G-UT-2） |

## 5. 执行流程（逐 Case 作业序列）

> 失败处理与收口：FAIL → 保留首个失败现场 + 保留 Run 证据 + 禁止重跑覆盖原始失败 → 登记缺陷并关联 Case ID；BLOCKED → 标记环境性阻塞 + 整个流程停止 + 登记缺口 + 不静默换工具链；INVALID → 标记该 Case 注入未命中 + 复现状态与修复状态分开记录 → 不允许仅靠“重跑通过”掩盖；NOT_RUN → 标记未执行 + 登记原因（不在 §3 清单中静默消失）。
> 执行批次：按模块切片划分（§5.1），批次内逐 Case；失败不阻断非环境性后续 Case，除非环境性阻塞（如 G-UT-2 替身契约缺）。

| Step | 动作 | 输入 / 依据 | 产出 |
|---|---|---|---|
| 0 | 资产就位：确认 ENV-1/ENV-2 就绪、`fakes.py` 在位；ENV-3 契约未建标 Blocked（G-UT-2）并跑 self-check | `tests.asset-design` 文档（G-UT-2 未建） | 就绪清单（Verified 或 Blocked 原因） |
| 1 | 读取方案清单并按优先级（P0→P1→P2）与批次排序 | 方案 `llmtier-unit-test-scheme` v0.1.0-draft.3 §3 | 执行队列 |
| 2 | 逐 Case：定位 Case 文档 | Case ID | 实施依据 |
| 3 | 按 Case 文档 §2–§7 执行前检与运行（按 §5.1 批次命令） | Case 文档 §2–§7 | Run 记录 |
| 4 | 判定并分路（PASS/FAIL/BLOCKED/INVALID） | 断言与环境事实 | Verdict 归报告 |
| 5 | 全部 Case 走完后生成测试报告 | 本计划 §7/§8 | `tests.unit-test-report` |

### 5.1 逐模块执行批次与命令

> 每批次＝一个模块切片；Case 范围为该模块**方案 §3 全部 Case 切片**（已建 33 份 Case 文档 + 该模块的待建 Case），⚠ 标记的待建 Case 当前无测试函数，按 NOT_RUN 计入（见 §3 前检）。命令为整批收集/执行入口，单 Case 用其文档 §7「单 Case 执行命令」（`-k` 或指定文件）。批次内 Case 不共享可变状态（ENV-1 每 Case 新建临时库）。
> 「覆盖测试文件」列为**已建 Case 的测试文件映射**（文件→Case 关系逐条对应，便于批次范围核对）；待建 Case 的测试文件在其文档建立后补入。

| 批次 | 模块（M-id） | Case 范围（该模块全切片） | 覆盖测试文件（文件→Case） | 批次执行命令 |
|---|---|---|---|---|
| B1 | `util`（M007） | `UT-UTIL-001…002`；⚠待建 `UT-UTIL-003…004` | `test_store.py`、`test_store_schema.py` → `UT-UTIL-001/002` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_store.py tests/unit/v03/test_store_schema.py -q` |
| B2 | `log`（M008） | `UT-LOG-001`；⚠待建 `UT-LOG-002` | `test_logs.py` → `UT-LOG-001` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_logs.py -q` |
| B3 | `http-api`（M001） | `UT-API-001…004`；⚠待建 `UT-API-005…013` | `test_errors.py`、`test_health.py` → `UT-API-001/004`；`test_auth.py` → `UT-API-002`；`test_sse.py` → `UT-API-003` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_errors.py tests/unit/v03/test_health.py tests/unit/v03/test_auth.py tests/unit/v03/test_sse.py -q` |
| B4 | `inference`（M003） | `UT-INF-001…005`；⚠待建 `UT-INF-006…009` | `test_responses.py` → `UT-INF-001`；`test_embeddings.py` → `UT-INF-002`；`test_usage.py`、`test_provider_openai.py`、`test_runtime_snapshot.py` → `UT-INF-003/005`；`test_routing.py`、`test_models.py` → `UT-INF-004` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_responses.py tests/unit/v03/test_embeddings.py tests/unit/v03/test_usage.py tests/unit/v03/test_provider_openai.py tests/unit/v03/test_runtime_snapshot.py tests/unit/v03/test_routing.py tests/unit/v03/test_models.py -q` |
| B5 | `management`（M004） | `UT-MGMT-001…006`；⚠待建 `UT-MGMT-007…011` | `test_app_startup.py` → `UT-MGMT-001`；`test_registry.py` → `UT-MGMT-002`；`test_admin.py`、`test_audit.py`、`test_logs.py` → `UT-MGMT-003`；`test_admin.py`、`test_usage.py`、`test_admin_stats.py` → `UT-MGMT-004`；`test_admin.py`、`test_health.py` → `UT-MGMT-005`；`test_account_usage.py` → `UT-MGMT-006` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_app_startup.py tests/unit/v03/test_registry.py tests/unit/v03/test_admin.py tests/unit/v03/test_audit.py tests/unit/v03/test_account_usage.py -q` |
| B6 | `observability`（M005） | `UT-OBS-001…005`；⚠待建 `UT-OBS-006…007` | `test_diagnostics.py`（含 HTTP 契约类）→ `UT-OBS-001/003/004`；`test_admin_stats.py` → `UT-OBS-002` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_diagnostics.py tests/unit/v03/test_admin_stats.py -q` |
| B7 | `libdiag`（M006） | `UT-DIAG-001…004`；⚠待建 `UT-DIAG-005…008` | `test_diagnostics.py` → `UT-DIAG-001/002/004`；`test_runtime_snapshot.py`、`test_app_startup.py`（`_UnavailableDiagnostics` 路径）→ `UT-DIAG-003` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_diagnostics.py tests/unit/v03/test_runtime_snapshot.py tests/unit/v03/test_app_startup.py -q` |
| B8 | `web-ui`（M002） | `UT-UI-001…006`；⚠待建 `UT-UI-007…010` | `test_webui_contract.py` → `UT-UI-001…006` | `PYTHONPATH=src python3 -m pytest tests/unit/v03/test_webui_contract.py -q` |
| BALL | 全量回归（8 模块） | 全部 64 Case（33 已建 + 31 待建） | `tests/unit/v03/*.py` | `PYTHONPATH=src python3 -m pytest tests/unit/v03 -q` |

| 阶段门 | 目的 | 进入条件 |
|---|---|---|
| 1 最小真实链 | 打通 `Store`+`Application`+`FakeAdapter` | B1、B5 中 `UT-MGMT-001` 通过 |
| 2 规模控制面 | 覆盖路由/鉴权/准入/错误信封 | B3、B4 `UT-INF-004/005` 通过 |
| 3 完整业务 | 覆盖推理/向量/诊断/观测/日志/UI 契约 | B4、B6、B7、B8、B2 通过 |
| 4 恢复 / 全量回归 | 故障注入与全量复跑 | B4 `UT-INF-003`、B1 `UT-UTIL-002`、B7 `UT-DIAG-003`、B6 `UT-OBS-003` 通过，BALL 通过 |

- 失败（FAIL）处理路径：保留现场与 Run 证据 → 登记缺陷并关联 Case ID → 继续后续 Case；不重跑覆盖原失败。
- 阻塞/无效（BLOCKED/INVALID）处理路径：BLOCKED（Python/pytest 缺失或替身契约缺）→ 环境性阻塞整批停并登记 G-UT-2；INVALID（注入未命中/并发未交错/loopback 实例未起）→ 修 Case 或标无效，不记 PASS。

## 6. 环境操作（搭建 / 复位 / 隔离 / 清理）

- 环境搭建与复位操作（不需要 m5air / LAN）：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`；每个 Case 在 `setUp` 建 `AppFixture`（新临时目录 + 新 SQLite），`tearDown` 调 `close()` 销毁临时目录 → 每 Case 天然复位。无“软复位→重启→驱动恢复”阶梯（无外部共享资源）。
- 隔离键与清理：隔离键＝`TemporaryDirectory` 路径（每 Case 唯一）；ENV-2 HTTP 实例用 `127.0.0.1:0` 随机端口、`setUpClass` 起、`tearDownClass` `shutdown()`+`server_close()` 并确认端口释放；并发 Case `join` 后才销毁输入；无跨 Case 共享状态。若 loopback 实例未就绪，必须 `shutdown()`+`server_close()` 后重建，失败不得只 kill 进程后继续。
- 单环境串行注意：单元层无单实例资源争用；若并行执行多批次，各批次仅共享只读源码，ENV-1 临时库与 ENV-2 随机端口天然隔离。

## 7. 证据与 Run 记录规则

- Run ID 规则与证据位置：`run-YYYYMMDD-NN`。**位置决定（诚实声明）**：STD `repository-layout §4.1.2` / `verification.md` 示例为 `tests/unit/<module>/reports/<run-id>/`（`<module>`＝方案 §3 的模块切片名 `M001` 等，而非源码目录名）。本项目**实际被测套件位于 `tests/unit/v03/`**，`tests/unit/<module>/` 目录**当前不存在**，且 STD 的 `<module>` 与方案的源码目录名（如 `http_api`）不一致；故本计划**裁剪为单一证据根** `tests/unit/v03/reports/<run-id>/`（以套件目录为根，避免与 `v03` 并列再建同名 `reports` 于非源码路径），并在首次执行前将该证据根登记到项目 `repository-layout` 说明。正式报告与 metadata 同在 Run 目录，机器输出放 `tests/unit/v03/reports/<run-id>/artifacts/`（默认不入 Git，按 CI 保留策略）。本轮无录制 Run，首次执行时按此落位。
- 保存内容与脱敏要求：命令、Python 版本、被测源码 commit、`PYTHONPATH`、pytest stdout/退出码、失败种子与并发交错样本、ENV 实例编号；不保存 secret/正文，日志样例须为已脱敏 `[REDACTED]` 形式（与 `UT-LOG-001` 断言一致）。
- 状态映射（Run 级）：pytest 单测试函数失败（`F`）→ 该 Case `FAIL`；pytest 收集/执行错误（`E`，含 import/fixture 错误）→ 该 Case `BLOCKED`（环境性）或按结论归 `FAIL`（断言性），不得静默记为 PASS；`skipped` → `NOT_RUN` 并登记原因，不计入 PASS；注入未命中/并发未交错 → `INVALID`。
- 重跑规则：重跑生成新 Run，不覆盖旧失败；INVALID 需记录复现状态与修复状态分开。

## 8. 报告产出与 Gate 规则

- 报告生成时机与模板：全部 Case 走完（或出口准则触发）后生成 `tests.unit-test-report` 实例，落位见 §7。**当前无录制 Run（G-UT-1），本阶段不生成报告实例**；报告在首次执行后按此规则生成。整体 BLOCKED（环境性，如 Python/pytest 缺失）→ 该轮不生成 report 实例，只记缺口与原因；部分 Case FAIL/INVALID → 仍生成 report（含完整 FAIL/INVALID 记录），不掩盖。
- Gate 建议规则：单元层闭合的**分母＝方案 §3 的 64 Case 清单**（非 33 VRC）。闭合条件＝全部 64 Case 有 `PASS`；`NOT_RUN`/`BLOCKED` 只对**非 P0** Case 计入闭合，且必须逐条给出**具名原因 + Owner**（不得只写状态）。**P0 Case 不得以 `NOT_RUN` 关闭**——任一 P0 Case 处于 `NOT_RUN`/`BLOCKED` 即整体未闭合，Gate 判 No-Go，缺口登记并指定 Owner/恢复条件。缺口 G-UT-1/G-UT-2/G-UT-3/G-UT-4 须各有 Owner/Gate。存在 FAIL 时报告按分级给条件接受/拒绝建议，不越权批准。33 份已建 Case 文档中 §7 映射待回溯的近似映射 Case，在回溯裁决前其 `PASS` 不被承认（按 `NOT_RUN`＋原因处理）。
- **层级边界**：单元层 `PASS` **不等于**契约层/系统层结论，`PASS` 不替代也不蕴含上层通过；局部通过不关闭上层组合目标（wire/E2E/真实 provider 协议由 `llmtier-system-test-scheme` 承接）。报告须显式声明"unit PASS ≠ contract/system PASS"。

## 9. 责任、排期与风险

| 构成项 / 风险 | Owner | 时间窗 / 最晚 Gate | 冲突或缓解出口 |
|---|---|---|---|
| 方案维护 | LLMTier | 本迭代 / 执行前 | VRC 变更时同步方案 §3/附录 A |
| Case 编写与执行 | LLMTier（含 Agent） | 按 §5 序列与 §5.1 批次 | 失败不阻断非环境性后续 Case |
| 实测基线漂移（模块设计与 ISD 版本不一致） | LLMTier | 执行前 | 以模块设计 §14/ISD §9.1 为准，冲突回溯设计修订 |
| 替身契约缺失 G-UT-2 | LLMTier | 首次执行前 | 补建 `tests/asset-design`；关闭前不声称证明真实 provider 协议 |
| 无录制 Run G-UT-1 | LLMTier | 首次执行 | 执行后按 §7/§8 补报告 |
| TS-003（LAN IP）适用性：`fakes.py` 的 `127.0.0.1` 是 `seed()` 写入的**占位 provider endpoint**（`http://127.0.0.1:9`，不真正拨号），`test_auth.py` 的 `127.0.0.1` 是 `unauthenticated_principal` 的**客户端 IP 字符串**（loopback 来源判定），二者**均非真实 provider endpoint** | LLMTier | 执行前确认 | 单元层不触真实 provider，TS-003 的“生产 provider endpoint 用 LAN IP”约束在**系统/契约层**强制；本层 `127.0.0.1` 属占位/来源字符串，须在 Run 记录中说明并复核不泄露到非单元层配置 |

## 10. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| G-UT-1 单元测试正式报告与 Run 证据缺失 | LLMTier / 首次执行后的报告评审 | 真实执行 `tests/unit/v03` 并按 §7/§8 生成 `tests.unit-test-report` 实例于 `tests/unit/v03/reports/<run-id>/`（证据根见 §7 位置决定） |
| G-UT-2 替身契约文档 `tests.asset-design` 未建 | LLMTier / 首次执行前 | 建立 `FakeAdapter` 资产文档并在方案 §1.6 填 ID（`FakeResponse` 为各测试模块本地 stub，不纳入） |
| G-UT-3 M002 六项 VRC 行为级断言缺口（当前仅字符串契约） | LLMTier / M002 web-ui；恢复条件＝引入 JS 行为测试宿主（node/jsdom）后 `UT-UI-001…010` 由字符串契约升级为行为断言（方案 §4） | 关闭前 `VRC-UI-001..006` 的行为级覆盖保持未闭合，Gate 不判其行为级闭合 |
| G-UT-4 M005 浏览器呈现（诊断页 tabs/Disabled 视觉）缺口 | LLMTier / M002/M005；视觉与交互归 M002 承担（系统/E2E）（方案 §4） | 关闭前单元层不重复登记；由 M002 系统/E2E 层承接并确认 |
| TS-003 与单元层 loopback 的边界确认 | LLMTier / 首次执行前 | 确认单元层 loopback `127.0.0.1` 仅用于本地测试实例（`TestClient`/`ThreadingHTTPServer` 临时端口），非 provider endpoint；LAN IP 约束由系统/契约层强制；在 Run 记录备注 |

<!-- 交付自查：执行者能否只凭本计划从 Go/No-Go 走到报告产出；计划里是否出现任何执行结论或 Verdict；到期条目是否被偷偷改判？ -->
