<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Module Test Plan

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-module-test-plan` |
| Document Version | `0.1.0-draft.6` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-test-plan` |
| Template Version | `0.9.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | llmtier-implementation-plan |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/llmtier-module-test-plan.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本计划绑定软件模块集合：本计划编排 8 个软件模块 `M001-M008`（模块切片与 Case ID 前缀见 §1）；`design_object_id` 为本项目元数据可选字段，本计划 metadata 未写入该字段（合并计划跨 8 模块，单一 `design_object_id` 无法承载），模块归属改由 §1 构成表模块切片与 §5 批次承担；ISD 基线在 §2 固定。
> 本文档对设计验证项（VRC）的引用规则：只引用 ID 与状态，不复制定义/判据；ENV 实例编号归 tests.asset-design，本计划编排 ENV 编号与 Case 分配时若变更设计须回溯修订并记录。
> **裁剪说明（tailored）**：模板默认“一模块一份计划”。本项目按用户授权将 8 个模块的模块层活动编排为一份项目级可执行作业指令（`M001-M008` 一次编排，LT-TL-025）；逐模块差异由 §1 构成表的模块切片、§5 的执行批次与 Case ID 前缀（`MT-API-*`/`MT-UI-*`/`MT-INF-*`/`MT-MGMT-*`/`MT-OBS-*`/`MT-DIAG-*`/`MT-UTIL-*`/`MT-LOG-*`）承担。裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 模板定位：方案、用例、计划与报告的边界

- **权威分工**：Case 清单归 `tests.module-test-scheme`；单 Case 展开归 `tests.module-case`（一 Case 一文档）；本计划是**可执行作业指令**——执行者（含 Agent）按它从执行前检做到报告产出；执行结果与 Verdict 权威在 `tests.module-test-report` 与 Run 证据。
- **只索引**：构成表引用方案版本与 Case ID 范围，不复制清单或 Case 细节。
- **测试资产**：工具/夹具/替身/受控时钟的契约与自检在 `tests.asset-design`（一资产一文档，阶段共享；本层复用 `llmtier-unit-fakes`）；本计划 §5 Step 0 使其就位。
- **不是授权书**：按用户当前授权交付；计划到期不改判任何事实状态。

### 计划条目状态语义

| 条目状态 | 含义 | 禁止 |
|---|---|---|
| `Planned` | 已排入计划，方案与责任已定位 | 用 Planned 冒充已执行或已通过 |
| `Deferred` | 经批准裁剪或延后，有 tailoring 依据与恢复条件 | 无依据的“暂不做” |
| `Blocked` | 依赖缺失（设计缺口、环境、上游合同） | 不登记缺口就长期挂起 |

任一条目能报出状态、依据与下一步；计划里没有任何执行结论。

## 1. 目标、范围与测试构成

- 验证对象：LLMTier 8 个软件模块（M001 `http-api`、M002 `web-ui`、M003 `inference`、M004 `management`、M005 `observability`、M006 `libdiag`、M007 `util`、M008 `log`）的**整模块组装层**行为与错误分支（**灰盒**：内部单元真实、经公开入口驱动、允许断言内部分支/状态/调用序；仅边界替身）；**不证明**跨模块系统级流程、wire 互操作、OpenAPI 端到端一致性、浏览器 E2E 与真实上游 provider 协议（见方案 §1）。
- 构成＝模块方案×1 ＋ Case 文档×N（一 Case 一文档）＋ 测试资产（tests.asset-design）＋ 相邻层交接出口。**分母＝四层**（方案 §3）：① 对外接口端到端行为 20 ＋ ② 内部分支 47 ＋ ③ 组合（判定表/配对）10 ＋ ④ 状态转换（迁移表）14 ＝ **91 条分母**，展开为 **68 个 Case**；VRC 只作追溯（附录 A），**不作分母**。清单唯一登记于方案 §3，本表只索引。**异常/错误注入矩阵**（方案 §1.5.1：(a) 37 个对外 `code` ＋ (b) 8 类上游异常 ＋ (c) 8 类传输/时间病态）为跨家族手段清单，落点映射既有/新增 Case，不另设分母。
- 排除项及 tailoring 依据：性能/耐久归系统层；真实 provider 协议与 E2E 归 `llmtier-system-test-scheme`；M002 行为级（真实 JS 执行）归系统层 `ST-UI-*`。依据见方案 §2/§4 与 [STD 裁剪清单](../../00_management/std-tailoring.md)。

| 构成层 | 文档 / 入口（Document ID 或缺口） | 覆盖责任摘要 | 条目状态 |
|---|---|---|---|
| 模块方案 ×1 | `llmtier-module-test-scheme` v0.1.0-draft.6（方案 §3 四层分母清单；§1.5 注入类方法；§1.5.1 异常/错误注入矩阵；§1.6/§1.7 环境类型） | 8 模块四层分母（①20/②47/③10/④14）与 68 Case 的清单与设计状态唯一登记；异常/错误矩阵 53 条封闭核对 | Implemented |
| Case 文档 ×68（0/68 已建） | `docs/70_verification/module/cases/MT-<OBJ>-<NNN>.md`（68 份，**待建**） | 逐 Case 输入构造、Oracle 与运行入口；见方案 §3 每行责任摘要 | Planned（下一交付步建立） |
| 测试资产 ×1 | `llmtier-unit-fakes`（`docs/70_verification/unit/assets/llmtier-unit-fakes.md`；`FakeAdapter`/`AppFixture`，候选 ID `FAKE-LLMTIER-ADAPTER`） | 上游进程内 fake 与组装夹具的契约与自检（模块层复用） | Implemented（`Implemented`/`Unverified`；自检 Run 待录制） |
| 相邻层交接出口 | 单元计划（`llmtier-unit-test-plan`，下层）、`llmtier-system-test-scheme`（上层 wire/E2E） | 组合保证与验收承接；UT 去重规则见方案 §5 | Implemented |

## 2. 被测基线与变更重跑范围

- 设计 / 源码 / 依赖基线：模块设计 M001 `http-api` v0.1.0-draft.2、M002 `web-ui` v0.1.0-draft.2、M003 `inference` v0.1.0-draft.1、M004 `management` v0.1.0-draft.3、M005 `observability` v0.1.0-draft.6、M006 `libdiag` v0.1.0-draft.6、M007 `util` v0.1.0-draft.2、M008 `log` v0.1.0-draft.1；对应 ISD `*-isd` 同版本（版本固定见方案 §1.5）。
- artifact 基线 pin（执行时在 Run 记录中固化，禁止在文档正文伪造自身 commit）：被测源码 `src/<module>/`（`http_api`/`web_ui`/`inference`/`management`/`observability`/`libdiag`/`util`/`log`）的 git commit；落库 `schema`/`migrations/` 版本；OpenAPI/错误码事件子集版本（`interfaces/`）。
- 运行时不变量：Python 3.14（`python3 -m pytest`），`PYTHONPATH=src`；测试框架 `pytest`；无外部服务依赖（provider 以进程内 fake 替代，HTTP 仅绑 loopback，见方案 §1.6/§1.7）。
- 变更 → 重跑范围规则：
  - 模块公开入口签名变化（如 `Registry.update_service_level`、`ResponsesService.create`）→ 该模块方案重裁 ＋ 该模块全部 Case 重跑。
  - 模块内部单元实现变化（公开行为不变）→ 该模块全部 Case 重跑（组装层对内部真实，内部改动可能改变组装行为）。
  - 落库 schema / `migrations/` 变化 → `MT-UTIL-001/002/003` 及一切依赖落库的 Case 全量重跑。
  - 错误码 / OpenAPI 事件子集变化 → `MT-API-*`、`MT-INF-*`、`MT-DIAG-*`、`MT-OBS-*` 受影响 Case 重跑并回溯设计修订。
  - 重跑生成新 Run 与新报告，不覆盖旧失败。

## 3. 执行前检（Go / No-Go）

> ENV 状态统一字段：本节「环境与工具」前检与 §5 Step 0 共享同一个“ENV 状态”变量——本节判定 Go/No-Go 后 ENV 状态置为 Ready/Blocked；§5 Step 0 按消费方索引构建 ENV 实例并跑 self-check（assets 的 Verified）；§8 报告产出读取此 ENV 状态字段；不在本节与 §5 重复定义同义词。

| 前检项 | 判定事实 | 通过条件 | 不满足时 |
|---|---|---|---|
| 方案就绪度 | `llmtier-module-test-scheme` v0.1.0-draft.6；68 Case 四层分母清单（①20/②47/③10/④14）均登记；无 Gap 未关闭、Tailored-N/A 已具名（见方案 §4：G-TRANSPORT-BUDGET-1 为系统层具名 Gap）；§3.7 分母→Case 核对 0 未映射（含注入面/数据类型核对块与异常/错误矩阵核对块） | 四层分母闭合、版本固定且缺口有主 | Blocked＋登记缺口 |
| Case 实现状态盘点 | 68 份 `tests.module-case` 文档**当前 0/68 已建**（下一交付步建立）；建立后须各自 §7 指向 `tests/module/cases/MT-*.py` 并自述 `Implemented`；每份 §1 须声明其覆盖的分支/组合/迁移 ID（方案 §5） | 68/68 已建且测试代码可定位 | 未建/未实现 Case 标 NOT_RUN＋登记原因 |
| 分支/组合/迁移覆盖达标 | 方案 §3.7 核对：层②47 分支、层③10 组合行、层④14 迁移行**全部映射到 ≥1 Case**（0 未映射）；且 §1.5.1 异常/错误矩阵 (a)37+(b)8+(c)8 全部映射到 Case 或具名 Gap；未覆盖者须具名或 N/A | 91 条分母 + 53 条矩阵项每条有 Case 或具名缺口/N/A | 未映射分母不得进入执行；标 NOT_RUN 并登记 |
| 环境与工具（引用 tests.asset-design 的 Verified 状态） | `PYTHONPATH=src python3 -m pytest tests/module/cases -q` 可收集并执行（套件待建，收集数为随实现演进的可变量）；`tests/common/fakes.py` 提供 `AppFixture`/`FakeAdapter`；替身资产 `llmtier-unit-fakes` 已建（`Implemented`/`Unverified`） | 全量模块可收集执行且替身契约就位 | 收集失败或 Python/pytest 缺失→环境性 Blocked；替身契约缺→引用 `llmtier-unit-fakes`，不静默用它物 |
| 构建接线 / 隔离确认 | 模块层**不需要** LAN / m5air / 真实 provider；HTTP 仅绑 loopback `127.0.0.1:0` 临时端口（ENV-2），provider 用进程内 `FakeAdapter`（ENV-3），故障用确定性注入（ENV-4）；无 `PYTHONPATH=src` 外依赖 | 全量模块在本机隔离可运行，无 LAN 依赖 | 需外部服务→不属模块层，退回系统层登记 |
| 注入类方法就绪（方案 §1.5） | 注入类方法可用：**主手段＝边界替身返回错误**（`FakeAdapter`/本地 `FakeResponse` 进程内可配置返回错误数据/异常/终态，含 5xx/超时/断连/配额耗尽/坏数据/畸形流；模块层运行时真实 provider 不可控，故只用进程内 fake，任何 LAN provider endpoint 若启用须按 TS-003 用 LAN IP 192.168.1.x、禁止 127.0.0.1）；**可选补充＝产品诊断注入**（`PATCH /v1/deployments/{id}/diagnostics` 经 ENV-2 loopback 实例；六类 `fault_502`/`fault_503`/`rate_limit`/`delay`/`stream_terminate`/`malformed_event`，见 `src/libdiag/injections.py`） | 边界替身主手段就绪且可返回配置错误（判定＝模块对该错误的映射）；产品注入可用时作为补充，注入可命中（计数可观测） | 边界替身主手段缺→该注入 Case 标 `Blocked` 并登记缺口；产品注入能力缺→标注为「补充不可用」，**不使基线 Case 失效**，不得静默改用他物 |
| 代码 review | 被测模块（`src/<module>/`）通过 `tests.code-review-checklist` 必查项 | 无 BLOCKED 必查项 | BLOCKED 项不得进入测试 |

## 4. 环境实例分配（plan 编排）

> ENV 实例类型与方案 §1.7 一致；编号在本表唯一登记。ENV-1/ENV-2 为真实实现（无替身契约），ENV-3/ENV-4 依赖 `llmtier-unit-fakes` 组装契约。
> **裁剪声明**：pinned 计划含「契约校验（Verified/降级原因）」列；本项目 ENV-1/ENV-2 为真实依赖（无 tests.asset-design 契约文档），故本表以「状态」列（Ready/Blocked）承载校验结论，不单列契约校验列——此为已声明的裁剪，非遗漏；ENV-3/ENV-4 契约就位后其 Verified 结论写入 §5 Step 0 就绪清单。

| ENV 实例编号 | 环境类型 | 契约文档引用（tests.asset-design） | 具体配置/位置 | Owner | 分配给哪些 Case | 准备时限 | 状态 |
|---|---|---|---|---|---|---|---|
| ENV-1 | 组装隔离库 | 不适用（真实依赖） | `tempfile.TemporaryDirectory` + `Application`（`tests/common/fakes.py::AppFixture`）；`setUp` 建、`tearDown.close()` 销毁 | LLMTier | `MT-*` 全部（默认环境） | 每次执行前 | Ready |
| ENV-2 | loopback 组装 HTTP 实例 | 不适用（真实 socket） | `ThreadingHTTPServer((127.0.0.1, 0), handler_factory(app))` | LLMTier | `MT-API-*`、`MT-OBS-*`、`MT-DIAG-*` 中经 HTTP 的 Case、`MT-MGMT-*` 中经 HTTP 的 Case | 每次执行前 | Ready |
| ENV-3 | provider 进程内 fake | `llmtier-unit-fakes`（`docs/70_verification/unit/assets/llmtier-unit-fakes.md`；候选 ID `FAKE-LLMTIER-ADAPTER`） | `tests/common/fakes.py::FakeAdapter`（`FakeResponse` 为各测试模块本地 stub，不在此） | LLMTier | `MT-INF-*`、`MT-MGMT-004/005/010` | — | Ready（契约已建；自检 Run 待录制） |
| ENV-4 | 确定性注入 | `llmtier-unit-fakes`（组装夹具） | `LLMTIER_SLOW_ADAPTER_DELAY` / 诊断 `set_injections`（经公开入口配置） | LLMTier | `MT-INF-008/011`、`MT-OBS-004`、`MT-DIAG-003/005/007` | 每次执行前 | Ready |

## 5. 执行流程（逐 Case 作业序列）

> 失败处理与收口（在本流程图内统一）：FAIL → 保留首个失败现场 + 保留 Run 证据 + 禁止重跑覆盖原始失败 → 登记缺陷并关联 Case ID；BLOCKED → 标记环境性阻塞 + 整个 §5 执行流程停止 + 登记缺口 + 不静默换工具链；INVALID → 标记该 Case 注入未命中 + 复现状态与修复状态分开记录 → 不允许仅靠“重跑通过”掩盖；NOT_RUN → 标记未执行 + 登记原因（不在 §3 清单中静默消失）。
> 执行批次：按模块切片划分（§5.1），批次内逐 Case；失败不阻断非环境性后续 Case，除非环境性阻塞（如 Python/pytest 缺失）。

| Step | 动作 | 输入 / 依据 | 产出 |
|---|---|---|---|
| 0 | 资产就位：确认 ENV-1/ENV-2 就绪、`fakes.py` 在位、ENV-3/ENV-4 契约 `llmtier-unit-fakes` 就位并跑 self-check；确认注入类方法就绪（§3：边界替身主手段可返回配置错误、产品诊断注入 API 作可选补充） | `llmtier-unit-fakes`（`docs/70_verification/unit/assets/`）；§3 前检 | 就绪清单（Verified 或 Blocked 原因） |
| 0b | 数据注入前置：按方案 §1.5「数据注入」经**公开入口**播种初态（fixed tier/deployment/账本/snapshot/injection 行；`AppFixture.seed`），**禁止直写表/直改内部字段**；核对边界数据（2 MB/`limit`/512/极值）与冻结向量（SSE 字节帧/32-hex traceparent/base64/UI 资产）就位 | 方案 §1.5「数据注入」+ §1.5 规则 1 | 初态播种记录（公开入口路径，不入库证据） |
| 1 | 读取方案清单并按优先级（P0→P1）与批次排序；每模块内按 ①接口行为→②分支→③组合→④状态迁移 排序 | 方案 `llmtier-module-test-scheme` v0.1.0-draft.6 §3 | 执行队列 |
| 2 | 逐 Case：定位 Case 文档 | Case ID | 实施依据 |
| 3 | 按 Case 文档 §2–§7 执行前检与运行（按 §5.1 批次命令）；涉及注入的 Case 先按方案 §1.5 主手段（边界替身返回错误：5xx/超时/断连/配额耗尽/坏数据/畸形流）配置替身返回，或按存储/传输/准入面/产品注入（可选补充）配置并确认注入可命中 | Case 文档 §2–§7；方案 §1.5「错误/故障注入」 | Run 记录（含注入命中计数） |
| 4 | 判定并分路（PASS/FAIL/BLOCKED/INVALID）；注入 Case 命中计数=0 → `INVALID` | 断言与环境事实 | Verdict 归报告 |
| 5 | 全部 Case 走完后生成测试报告 | 本计划 §7/§8 | `tests.module-test-report` |

### 5.1 逐模块执行批次与命令（按分支/组合/迁移分批）

> 每批次＝一个模块切片；Case 范围为该模块**方案 §3 全部 Case 切片**（共 68 个 Case，module-case 文档待建）。命令为整批收集/执行入口，单 Case 用其文档 §7「单 Case 执行命令」（`-k` 或指定文件）。批次内 Case 不共享可变状态（ENV-1 每 Case 新建临时库）。
> **异常/错误注入矩阵随批执行（方案 §1.5.1）**：每批次另须执行该矩阵中归属本模块的 (a) `code` / (b) 上游异常类 / (c) 传输/时间病态行，并记录每行的 **mock 注入配置 + 模块映射结果**（code/status/终态）；c4/c5（broken pipe/RST）须在 ENV-2 真实 socket 上执行并记录 `aborted` 终态与 fd/许可复位证据。
> STD `eaca6dc`：模块可执行脚本平铺于 `tests/module/cases/`，**文件名＝Case ID**（`MT-<OBJ>-<NNN>.py`）。
> 共享替身 `AppFixture`/`FakeAdapter` 位于 `tests/common/fakes.py`。
> **按分支/组合/迁移分批执行**：每模块批次内按分母层顺序执行——先 ① 接口行为，再 ② 分支，再 ③ 组合，再 ④ 状态迁移；执行记录须标注每条 Case 覆盖的分支 ID / 组合 ID / 迁移 ID（方案 §3.7），便于核对“未覆盖的分支/迁移”，未执行到的分支/迁移须具名或 N/A。
> **注入类方法随批执行（方案 §1.5）**：每批次在 Step 0b 完成**数据注入播种**（初态经公开入口、边界数据/冻结向量就位；禁止直写表）后再跑；批次内凡涉及注入的 Case 须覆盖其所属**故障注入面**（上游/存储/传输/准入），并记录**注入命中计数**（=0 → `INVALID`，见 §7/§8）。注入面与批次的对应见下表「关联注入面/数据注入」列。

| 批次 | 模块（M-id） | Case 范围（该模块全切片） | 分支/组合/迁移分母（方案 §3.7） | 关联注入面 / 数据注入（方案 §1.5） | 批次执行命令 |
|---|---|---|---|---|---|
| B1 | `util`（M007） | `MT-UTIL-001…005` | 分支 M007×3 / 迁移 T12-T13 | 故障-存储面（库写失败/表损坏/迁移中途失败）；数据-初态（公开入口播种） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UTIL-*.py -q` |
| B2 | `log`（M008） | `MT-LOG-001…003` | 分支 M008×2 / 组合 K10 / 迁移 T14 | 故障-存储面（写失败）；数据-边界（512/`limit` 夹取） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-LOG-*.py -q` |
| B3 | `http-api`（M001） | `MT-API-001…013` | 分支 M001×9 / 组合 K1-K2 / 迁移（SSE 终态并入 K2） | 故障-传输面（客户端断开/超大流/畸形事件、**broken pipe c4 / RST c5（ENV-2 真实 socket）**）、上游面（5xx/超时）；数据-边界（2 MB body）、冻结向量（SSE 帧/32-hex traceparent） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-*.py -q` |
| B4 | `inference`（M003） | `MT-INF-001…019` | 分支 M003×15 / 组合 K4-K5 / 迁移 T1-T5 | 故障-上游面（边界替身返回 5xx·超时·断连·配额耗尽·坏数据·畸形流、**stall/hang c1·slow-response c2·超大 c3·截断流 c6·畸形帧 c7·并发超时+许可泄漏 c8·凭据缺失 a24/b8**；产品注入 fault_502/503·delay·rate_limit 作可选补充）、存储面（账本写失败）；数据-初态/冻结向量（base64 向量） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-*.py -q` |
| B5 | `management`（M004） | `MT-MGMT-001…011` | 分支 M004×6 / 组合 K3/K6-K7 / 迁移 T6-T8 | 故障-存储面（bootstrap 中途失败回滚）、固定 tier 删除 `fixed_service_level`（a16）；数据-初态/边界（cursor/`limit`） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-*.py -q` |
| B6 | `observability`（M005） | `MT-OBS-001…004` | 分支 M005×3 / 迁移 T9 | 故障-存储面（观测库写失败 fail-open）、诊断注入；数据-诊断注入（`PATCH /v1/deployments/{id}/diagnostics`） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-OBS-*.py -q` |
| B7 | `libdiag`（M006） | `MT-DIAG-001…007` | 分支 M006×5 / 组合 K4/K8-K9 / 迁移 T9-T11 | 故障-上游面（`stream_terminate`/`malformed_event`）、存储面（诊断写入失败）；数据-诊断注入/冻结向量 | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-*.py -q` |
| B8 | `web-ui`（M002） | `MT-UI-001…006` | 分支 M002×4 | 数据-冻结向量（UI 资产字符串） | `PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-*.py -q` |
| BALL | 全量回归（8 模块） | 全部 68 Case | 91 条分母全覆盖 | 「mock 返回」6 类 + 存储/传输/准入 3 面 + 4 数据注入类 + **§1.5.1 异常/错误矩阵 53 条** | `PYTHONPATH=src python3 -m pytest tests/module/cases -q` |

| 阶段门 | 目的 | 进入条件 |
|---|---|---|
| 1 最小真实链 | 打通 `Store`+`Application`+`FakeAdapter` 组装 | B1 `MT-UTIL-001`、B5 `MT-MGMT-001` 通过 |
| 2 规模控制面 | 覆盖路由/鉴权/准入/错误信封 | B3、B4 `MT-INF-004/007` 通过 |
| 3 完整业务 | 覆盖推理/向量/诊断/观测/日志/UI 契约 | B4、B6、B7、B8、B2 通过 |
| 4 恢复 / 全量回归 | 边界替身返回错误（主）与产品注入（补充）+ 全量复跑 + 分支/组合/迁移覆盖核对 + **异常/错误矩阵封闭核对** | B4 `MT-INF-003/008/009/012/013…019`、B3 `MT-API-012/013`、B5 `MT-MGMT-011`、B1 `MT-UTIL-002/004/005`、B7 `MT-DIAG-007`、B6 `MT-OBS-004` 通过（产品注入命中计数 > 0），BALL 通过，§3.7 分母核对 0 未映射（含注入面核对块与异常/错误矩阵 (a)37+(b)8+(c)8 核对块） |

- 失败（FAIL）处理路径：保留现场与 Run 证据 → 登记缺陷并关联 Case ID → 继续后续 Case；不重跑覆盖原失败。
- 阻塞/无效（BLOCKED/INVALID）处理路径：BLOCKED（Python/pytest 缺失或 Case 文档未建、注入手段缺）→ 环境性阻塞整批停并登记；INVALID（**注入未命中（命中计数=0）**/并发未交错/loopback 实例未起）→ 修 Case 或标无效，不记 PASS（见方案 §1.5「注入类方法」与 §5 注入规则）。

## 6. 环境操作（搭建 / 复位 / 隔离 / 清理）

- 环境搭建与复位操作（不需要 m5air / LAN）：`PYTHONPATH=src python3 -m pytest tests/module/cases -q`；每个 Case 在 `setUp` 建 `AppFixture`（新临时目录 + 新 SQLite + 真实组装栈），`tearDown` 调 `close()` 销毁临时目录 → 每 Case 天然复位。无“软复位→重启→驱动恢复”阶梯（无外部共享资源）。
- 隔离键与清理：隔离键＝`TemporaryDirectory` 路径（每 Case 唯一）；ENV-2 HTTP 实例用 `127.0.0.1:0` 随机端口、`setUpClass` 起、`tearDownClass` `shutdown()`+`server_close()` 并确认端口释放；ENV-4 注入经公开入口在每 Case 前重置；并发 Case `join` 后才销毁输入；无跨 Case 共享状态。若 loopback 实例未就绪，必须 `shutdown()`+`server_close()` 后重建，失败不得只 kill 进程后继续。
- 单环境串行注意：模块层无单实例资源争用；若并行执行多批次，各批次仅共享只读源码，ENV-1 临时库与 ENV-2 随机端口天然隔离。

## 7. 证据与 Run 记录规则

- Run ID 规则与证据位置：`run-YYYYMMDD-NN`。**位置**：STD `path-policy.json` 指定模块报告根为 `tests/module/reports/`；本计划据此使用**单一证据根** `tests/module/reports/<run-id>/`。**逐 Case 结果平铺**：按 STD `repository-layout §4.1.1`，逐 Case 结果写作 `reports/<run-id>/<Case ID>.json`（如 `MT-API-001.json`），不嵌套 `cases/<case-id>/manifest.json`；正式报告 `module-test-report.md` 与 `case-status.json` / `test-run.env` 同在 Run 根。机器输出（`junit.xml`、`pytest.log`）放 `tests/module/reports/<run-id>/artifacts/`（默认不入 Git，按 CI 保留策略）。**现状**：证据根 `tests/module/reports/` **待首次执行建立**（本轮仅交付 scheme/plan；case 与执行在下一交付步）。
- 保存内容与脱敏要求：命令、Python 版本、被测源码 commit、`PYTHONPATH`、pytest stdout/退出码、失败种子与并发交错样本、ENV 实例编号；不保存 secret/正文，日志样例须为已脱敏 `[REDACTED]` 形式（与 `MT-LOG-001` 断言一致）。
- **注入类方法证据（方案 §1.5 / §1.5.1）**：凡使用注入的 Case（主手段「mock 返回」6 类 + 存储/传输/准入 3 面 + 数据注入 4 类 + §1.5.1 异常/错误矩阵 53 条），Run 记录须保存**注入承接证据**——边界替身返回的配置（错误类型/状态码/错误体，如配额耗尽的 429 体、stall/hang 的「accept 后不回字节」、截断流的 early EOF 位置）与模块映射结果（错误码/status/分支走向/SSE 终态 `aborted`），或产品注入的**注入命中计数**与类型/参数（如 `fault_502`/`stream_terminate_after_events`）、注入生效阶段的 trace 或落库行，以及数据注入的**公开入口播种路径**（证明经公开入口而非直写表）。**传输/时间病态专证**：c4/c5（broken pipe/RST）须附 ENV-2 真实 socket 的客户端断开方式与 `aborted(client disconnected)` trace/许可复位、fd 基线不泄漏证据；c1/c2 须附超时参数（`connect_timeout_ms`/`stream_idle_timeout_ms`）与命中证据；c8 须附 `_inflight` 归零证据。产品注入命中计数=0 即 `INVALID`，须记录复现状态与修复状态分开。
- 状态映射（Run 级）：pytest 单测试函数失败（`F`）→ 该 Case `FAIL`；pytest 收集/执行错误（`E`，含 import/fixture 错误）→ 该 Case `BLOCKED`（环境性）或按结论归 `FAIL`（断言性），不得静默记为 PASS；`skipped` → `NOT_RUN` 并登记原因，不计入 PASS；**注入未命中（命中计数=0）**/并发未交错 → `INVALID`。
- 重跑规则：重跑生成新 Run，不覆盖旧失败；INVALID 需记录复现状态与修复状态分开。

## 8. 报告产出与 Gate 规则

- 报告生成时机与模板：全部 Case 走完（或出口准则触发）后生成 `tests.module-test-report` 实例，落位见 §7。整体 BLOCKED（环境性，如 Python/pytest 缺失或 68 份 Case 文档未建）→ 该轮不生成 report 实例，只记缺口与原因；部分 Case FAIL/INVALID → 仍生成 report（含完整 FAIL/INVALID 记录），不掩盖。
- Gate 建议规则：模块层闭合的**分母＝方案 §3 的 68 Case 四层清单**（①接口行为 20 / ②分支 47 / ③组合 10 / ④迁移 14，非 33 VRC）。闭合条件＝全部 68 Case 有 `PASS`；`NOT_RUN`/`BLOCKED` 只对**非 P0** Case 计入闭合，且必须逐条给出**具名原因 + Owner**。**P0 Case 不得以 `NOT_RUN` 关闭**——任一 P0 Case 处于 `NOT_RUN`/`BLOCKED` 即整体未闭合，Gate 判 No-Go。存在 FAIL 时报告按分级给条件接受/拒绝建议，不越权批准。
- **分支/组合/迁移覆盖达标门**：报告须附方案 §3.7 分母→Case 核对结果——层②47 分支、层③10 组合行、层④14 迁移行**全部映射到 ≥1 Case**；未覆盖的分支/迁移必须**具名**（列出分支 ID / 迁移 ID）或标 `Tailored-N/A`（附设计事实依据），否则 Gate 判 No-Go。**不得以“整体 PASS 比例”掩盖未覆盖分支。**
- **注入类方法命中门**：报告须附注入类方法核对结果——方案 §1.5 的**「mock 返回」6 类（5xx/超时/断连/配额耗尽/坏数据/畸形流）+ 存储/传输/准入 3 面 + 数据注入 4 类（初态/边界/诊断/冻结向量）全部映射到 ≥1 Case**（方案 §3.7 注入面核对块 0 未映射）。**主手段（边界替身返回错误）**：判定＝模块对该错误的映射，替身按配置返回错误即成立；**产品注入（可选补充）**：凡使用产品注入的 Case **命中计数 > 0**，未命中（计数=0）即 `INVALID`，不得以 `PASS` 关闭，未修复即整体未闭合、Gate 判 No-Go。数据注入须附经公开入口播种的证据（禁止直写表）。**不得以“重试即恢复”掩盖根因。**
- **异常/错误矩阵封闭门（新增）**：报告须附方案 §1.5.1 异常/错误注入矩阵的**逐行封闭核对**——(a) 37 个对外 `code`（Oracle ＝ `src/`）、(b) 8 类上游异常、(c) 8 类传输/时间病态，**每条映射到 ≥1 Case 或具名 Gap**；未映射项必须具名（列出 a/b/c 编号）或 `Tailored-N/A`（附设计事实），否则 Gate 判 No-Go。**每一项都必须有「mock 如何注入 → 实测映射（code/status/终态）」证据对**；c4/c5 须为 ENV-2 真实 socket 证据。**不得以“某类已覆盖”合并掩盖单个 `code`/单项病态。**
- **层级边界**：模块层 `PASS` **不等于**系统层结论，`PASS` 不替代也不蕴含上层通过；**单元层 PASS 不关闭本层**（本层分母独立来自模块设计 §14），**本层 PASS 不关闭上层**（wire/E2E/真实 provider 协议由 `llmtier-system-test-scheme` 承接）。报告须显式声明"module PASS ≠ system PASS"。

## 9. 责任、排期与风险

| 构成项 / 风险 | Owner | 时间窗 / 最晚 Gate | 冲突或缓解出口 |
|---|---|---|---|
| 方案维护 | LLMTier | 本迭代 / 执行前 | VRC 变更时同步方案 §3/附录 A |
| Case 文档编写与执行 | LLMTier（含 Agent） | 下一交付步 / 按 §5 序列与 §5.1 批次 | 失败不阻断非环境性后续 Case |
| 组装真伪边界被破坏（内部被打桩） | LLMTier | 执行前 | 按方案 §1.5 规则 2 复核，破坏即 Case 不完备 |
| 实测基线漂移（模块设计与 ISD 版本不一致） | LLMTier | 执行前 | 以模块设计 §14/ISD §9.1 为准，冲突回溯设计修订 |
| TS-003（LAN IP）适用性：模块层 `127.0.0.1` 为 loopback 测试 HTTP 实例与占位 provider endpoint（不真正拨号） | LLMTier | 执行前确认 | 模块层不触真实 provider，TS-003「生产 provider endpoint 用 LAN IP」约束在系统/契约层强制；本层须在 Run 记录中说明并复核不泄露到非模块层配置 |

## 10. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| 68 份 `tests.module-case` 文档未建（`MT-*`） | LLMTier / 首次执行前 | 下一交付步建立 68 份文档，写入 `docs/70_verification/module/cases/`，各自 §7 指向 `tests/module/cases/MT-*.py`，§1 声明覆盖的分支/组合/迁移 ID 与 §1.5.1 矩阵行 |
| 模块可执行套件 `tests/module/cases/` 与 Run 证据未录 | LLMTier / 首次执行 | 按 §5.1 批次实现并执行，产出 `tests/module/reports/<run-id>/` 后生成 `tests.module-test-report` |
| M002 行为级（真实 JS 执行）承接 | LLMTier / M002 | 已由系统层 `ST-UI-001..010` 承接（`RISK-UI-EXEC-1` 已关闭）；本层仅静态产物/契约组装 |

<!-- 交付自查：执行者能否只凭本计划从 Go/No-Go 走到报告产出；计划里是否出现任何执行结论或 Verdict；到期条目是否被偷偷改判？ -->
