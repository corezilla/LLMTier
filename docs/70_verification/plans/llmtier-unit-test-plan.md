<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Unit Test Plan

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-unit-test-plan` |
| Document Version | `0.1.0-draft.1` |
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

> 本计划绑定软件模块集合：`design_object_id` 按本计划约定记录为 `M001-M008`（见 §2）；ISD 基线在 §2 固定。
> **裁剪说明（tailored）**：模板默认“一模块一份计划”。本项目按用户授权将 8 个模块的单元层活动编排为一份项目级可执行作业指令（`M001-M008` 一次编排）；逐模块区分由 §1 构成表的模块切片与 Case ID 前缀（`UT-API-*`/`UT-UI-*`/`UT-INF-*`/`UT-MGMT-*`/`UT-OBS-*`/`UT-DIAG-*`/`UT-UTIL-*`/`UT-LOG-*`）承担。裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。
> 模板歧义记录：锁定模板 `tests.unit-test-plan@0.9.1` 同时存在 `### 3.5 环境实例分配` 与 `## 4. 环境实例分配`（内容重复）。本实例只保留 `## 4`，不复制模板内部重复章节；ENV 实例编号唯一登记于 §4。

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

- 验证对象：LLMTier 8 个软件模块（M001-M008）的单元层行为与错误分支；**不证明**组装后进程级流程、wire 互操作、浏览器 E2E 与真实上游 provider 协议（见方案 §1/§4）。
- 排除项及 tailoring 依据：性能/耐久归系统层；模块组装归 `tests.module-test-scheme`/`-plan`；验收不在本家族。依据见方案 §2/§4 与 [STD 裁剪清单](../../00_management/std-tailoring.md)。

| 构成层 | 文档 / 入口（Document ID 或缺口） | 覆盖责任摘要 | 条目状态 |
|---|---|---|---|
| 单元方案 ×1 | `llmtier-unit-test-scheme` v0.1.0-draft.1 | 8 模块 33 VRC 的清单与设计状态唯一登记 | Planned |
| Case 文档 ×33 | `UT-API-001…004`、`UT-UI-001…006`、`UT-INF-001…005`、`UT-MGMT-001…006`、`UT-OBS-001…005`、`UT-DIAG-001…004`、`UT-UTIL-001…002`、`UT-LOG-001` | 见方案 §3 每行责任摘要 | Planned |
| 测试资产 ×2（候选） | `tests.asset-design`（`FakeAdapter`/`FakeResponse`）；Gap G-UT-2 | 上游/HTTP 替身的契约与自检 | Blocked（G-UT-2） |
| 相邻层交接出口 | `tests.module-test-scheme`/`-plan`（组装后流程）、`llmtier-system-test-scheme`（wire/E2E） | 组合保证与验收承接 | Planned |

## 2. 被测基线与变更重跑范围

- 设计 / 源码 / 依赖基线：模块设计 M001 v0.1.0-draft.2、M002 v0.1.0-draft.2、M003 v0.1.0-draft.1、M004 v0.1.0-draft.2、M005 v0.1.0-draft.6、M006 v0.1.0-draft.6、M007 v0.1.0-draft.1、M008 v0.1.0-draft.1；对应 ISD `*-isd` 同版本；源码 `src/<module>/`；运行时 Python 3.14；测试框架 `pytest`；无外部服务依赖（provider 以 fake 替代）。
- 变更 → 重跑范围规则：
  - 模块公开入口签名变化（如 `Registry.update_service_level`、`ResponsesService.create`）→ 该模块方案重裁 + 该模块全部 Case 重跑。
  - 落库 schema/`migrations/` 变化 → `UT-UTIL-001/002` 及依赖落库的 Case 全量重跑。
  - 错误码/OpenAPI 事件子集变化 → `UT-API-*`、`UT-INF-*`、`UT-DIAG-*`、`UT-OBS-*` 受影响 Case 重跑并回溯设计修订。
  - 私有 helper 重构（不改公开行为）→ 仅受影响 Case 复跑。
  - 重跑生成新 Run 与新报告，不覆盖旧失败。

## 3. 执行前检（Go / No-Go）

> ENV 状态统一字段：本节「环境与工具」前检与 §5 Step 0 共享同一个“ENV 状态”变量——本节判定 Go/No-Go 后 ENV 状态置为 Ready/Blocked；§5 Step 0 按消费方索引构建 ENV 实例并跑 self-check（assets 的 Verified）；§8 报告产出读取此 ENV 状态字段；不在本节与 §5 重复定义同义词。

| 前检项 | 判定事实 | 通过条件 | 不满足时 |
|---|---|---|---|
| 方案就绪度 | `llmtier-unit-test-scheme` v0.1.0-draft.1，33 VRC 均有 Case；缺口 G-UT-1/G-UT-2 已登记 | 分母闭合且版本固定 | Blocked＋登记缺口 |
| Case 实现状态盘点 | 33 个 unit-case 文档均记录测试代码位置；`tests/unit/v03` 当前收集 197 个测试，全部 `Implemented`（本阶段验证执行 `197 passed`，非正式 Run） | 覆盖 33 VRC 的测试函数均 Implemented 或明确跳过登记 | 未实现项标 NOT_RUN 并登记 |
| 环境与工具（引用 tests.asset-design 的 Verified 状态） | `python3 --version`≥3.11；`pytest` 可用；`tests/unit/v03/fakes.py` 在位；替身资产 `tests.asset-design` 未建（G-UT-2） | Python/pytest/fixtures 可用且替身契约就位 | 工具缺失→环境性 Blocked；替身契约缺→登记 G-UT-2，不静默用它物 |
| 构建接线（全量交付构建 / 消费者链接实际库） | `PYTHONPATH=src python3 -m pytest tests/unit/v03 -q` 可收集并执行 | 全量单元可运行 | 收集失败→Blocked＋缺口 |

## 4. 环境实例分配（plan 编排）

| ENV 实例编号 | 环境类型 | 契约文档引用（tests.asset-design） | 具体配置/位置 | Owner | 分配给哪些 Case | 准备时限 | 状态 | 契约校验（Verified/降级原因） |
|---|---|---|---|---|---|---|---|---|
| ENV-1 | 隔离 Python 临时库 | 不适用（真实依赖） | `tempfile.TemporaryDirectory` + `Application`（`tests/unit/v03/fakes.py::AppFixture`） | LLMTier | `UT-*` 全部（默认环境） | 每次执行前 | Ready | 真实 SQLite，无替身契约 |
| ENV-2 | loopback 测试 HTTP 实例 | 不适用（真实 socket） | `ThreadingHTTPServer((127.0.0.1, 0), handler_factory(app))` | LLMTier | `UT-API-002`、`UT-API-003`、`UT-DIAG-004`、`UT-OBS-002`、`UT-OBS-004` | 每次执行前 | Ready | 临时端口，真实 handler 栈 |
| ENV-3 | provider 进程内 fake | 待建（G-UT-2；候选 ID `FAKE-LLMTIER-ADAPTER`） | `tests/unit/v03/fakes.py::FakeAdapter` / `FakeResponse` | LLMTier | `UT-INF-001…005`、`UT-MGMT-005`、`UT-MGMT-006` | 替身文档建立前 | Blocked（G-UT-2） | 契约未建：允许执行但不得声称证明真实 provider 协议 |

## 5. 执行流程（逐 Case 作业序列）

| Step | 动作 | 输入 / 依据 | 产出 |
|---|---|---|---|
| 0 | 资产就位：按消费索引构建全部依赖测试资产并跑自检 | `tests.asset-design` 文档（G-UT-2 未建，标 Blocked） | 就绪清单（Verified 或 Blocked 原因） |
| 1 | 读取方案清单并按优先级排序 | 方案 `llmtier-unit-test-scheme` v0.1.0-draft.1 §3 | 执行队列 |
| 2 | 逐 Case：定位 Case 文档 | Case ID | 实施依据 |
| 3 | 按 Case 文档执行前检与运行 | Case 文档 §2–§7 | Run 记录 |
| 4 | 判定并分路（PASS/FAIL/BLOCKED/INVALID） | 断言与环境事实 | Verdict 归报告 |
| 5 | 全部完成后生成测试报告 | 本计划 §8 | `tests.unit-test-report` |

| 阶段门 | 目的 | 进入条件 |
|---|---|---|
| 1 最小真实链 | 打通 `Store`+`Application`+`FakeAdapter` | `UT-UTIL-*`、`UT-MGMT-001` 通过 |
| 2 规模控制面 | 覆盖路由/鉴权/准入/错误信封 | `UT-API-*`、`UT-INF-004/005` 通过 |
| 3 完整业务 | 覆盖推理/向量/诊断/观测/日志/UI 契约 | `UT-INF-001/002/003`、`UT-DIAG-*`、`UT-OBS-*`、`UT-LOG-001`、`UT-UI-*` 通过 |
| 4 恢复 / 全量回归 | 故障注入与全量复跑 | `UT-INF-003`、`UT-UTIL-002`、`UT-DIAG-003`、`UT-OBS-003` 通过 |

- 失败（FAIL）处理路径：保留现场与 Run 证据 → 登记缺陷并关联 Case ID → 继续后续 Case；不重跑覆盖原失败。
- 阻塞/无效（BLOCKED/INVALID）处理路径：BLOCKED（Python/pytest 缺失或替身契约缺）→ 环境性阻塞整批停并登记 G-UT-2；INVALID（注入未命中/并发未交错/loopback 实例未起）→ 修 Case 或标无效，不记 PASS。

## 6. 环境操作（搭建 / 复位 / 隔离 / 清理）

- 环境搭建与复位操作：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`；每个 Case 在 `setUp` 建 `AppFixture`（新临时目录 + 新 SQLite），`tearDown` 调 `close()` 销毁临时目录 → 每 Case 天然复位。
- 隔离键与清理：隔离键＝`TemporaryDirectory` 路径（每 Case 唯一）；HTTP 实例用 `127.0.0.1:0` 随机端口；并发 Case `join` 后才销毁输入；无跨 Case 共享状态。
- 复位阶梯与时限（软复位→重启→驱动恢复）：无外部资源；单 Case 单进程超时默认 30s；fixture 重建即复位（无阶梯）。若 loopback 实例未就绪，`tearDownClass` 必须 `shutdown()`+`server_close()` 并确认端口释放，失败不得只 kill 进程后继续。

## 7. 证据与 Run 记录规则

- Run ID 规则与证据位置：`run-YYYYMMDD-NN`；证据位置 `tests/unit/<module>/reports/<run-id>/`（本轮无录制 Run；首次执行时按此落位并附正式报告 metadata）。
- 保存内容与脱敏要求：命令、Python 版本、源码 commit、pytest stdout/退出码、失败种子与并发交错样本、ENV 实例编号；不保存 secret/正文，日志样例须为已脱敏 `[REDACTED]` 形式。
- 重跑规则：重跑生成新 Run，不覆盖旧失败；INVALID 需记录复现状态与修复状态分开。

## 8. 报告产出与 Gate 规则

- 报告生成时机与模板：全部 Case 走完（或出口准则触发）后生成 `tests.unit-test-report` 实例。**当前无录制 Run（G-UT-1），本阶段不生成报告实例**；报告在首次执行后生成。
- Gate 建议规则：覆盖闭合（33 VRC 均有 PASS/NOT_RUN 说明）且缺口 G-UT-1/G-UT-2 有 Owner/Gate；存在 FAIL 时报告按分级给条件接受/拒绝建议，不越权批准。

## 9. 责任、排期与风险

| 构成项 / 风险 | Owner | 时间窗 / 最晚 Gate | 冲突或缓解出口 |
|---|---|---|---|
| 方案维护 | LLMTier | 本迭代 / 执行前 | VRC 变更时同步方案 §3/附录 A |
| Case 编写与执行 | LLMTier（含 Agent） | 按 §5 序列 | 失败不阻断非环境性后续 Case |
| 实测基线漂移（模块设计与 ISD 版本不一致） | LLMTier | 执行前 | 以模块设计 §14/ISD §9.1 为准，冲突回溯设计修订 |
| 替身契约缺失 G-UT-2 | LLMTier | 首次执行前 | 补建 `tests/asset-design`；关闭前不声称真实 provider 协议 |
| 无录制 Run G-UT-1 | LLMTier | 首次执行 | 执行后按 §7/§8 补报告 |

## 10. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| G-UT-1 单元测试正式报告与 Run 证据缺失 | LLMTier / 首次执行后的报告评审 | 真实执行 `tests/unit/v03` 并生成 `tests.unit-test-report` |
| G-UT-2 替身契约文档 `tests.asset-design` 未建 | LLMTier / 首次执行前 | 建立 `FakeAdapter`/`FakeResponse` 资产文档并在方案 §1.6 填 ID |
