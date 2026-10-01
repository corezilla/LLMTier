<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Scheme

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-scheme` |
| Document Version | `0.1.0-draft.12` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-test-scheme` |
| Template Version | `0.6.1` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/llmtier-system-test-scheme.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

<span style="color:#1f6feb"><em>**编写建议**：本模板是系统测试方案，与 design.software-system（系统设计阶段）一一对应。方案只登记测试分类与 Case 清单（每 Case 一行责任摘要），不写 Case 细节；逐 Case 展开一 Case 一文档（tests.system-case）。</em></span>

> **格式说明**：蓝色斜体为编写建议（指导如何填写，生成实例后保留）；灰色文字为虚构教学示例（以 `STD_TEMPLATE_EXAMPLE` 标记包裹，`new-design` 生成实例时自动剥离，不得当作项目事实或运行证据）；`<!-- TODO -->` 为待填槽位。颜色在 GitHub 等严格渲染器中降级为斜体/普通字，语义不变。

> 本方案绑定软件系统：父设计 Document ID 经 `--parent-document-id` 写入 metadata；系统设计 ID/版本在 §1 固定。

### 模板定位：方案、用例与计划的边界

<span style="color:#1f6feb"><em>**编写建议**：本方案对应系统设计阶段（design.software-system；总体设计的软件分支同用本模板）。分母来源是系统设计的端到端流程（§7）、对外接口（§8）、系统约束与预算，以及机制的端到端保证（design.system-mechanism §15 承接进入本分母——机制不单独立测试文档）。子系统层归 tests.subsystem-test-scheme；验收活动不在本家族，按项目 tailoring 承接。</em></span>

- **权威分工**：系统层测试的 Case 清单（ID、分类、优先级、责任摘要、设计状态）以本方案为唯一登记处；单 Case 展开归 `tests.system-case`（一 Case 一文档）；活动组织归 `tests.system-test-plan`。
- **只有摘要**：本方案每条 Case 只写责任摘要（要测什么），不写输入构造、Oracle 或步骤。
- **下层 PASS 不关闭本层**；本层 PASS 不关闭上层组合目标。

### 状态语义：用例状态

<span style="color:#1f6feb"><em>**编写建议**：本方案只持有 用例状态（Designed / Gap / Tailored-N/A）；实现状态（Planned/Implemented）在对应 case-design 文档，执行状态与 Verdict 只在 Run 报告。混层即违例。</em></span>

> 本文档对设计验证项（VRC/V-xxx）的引用规则：只引用 ID 与状态，不复制定义/判据；判据与契约权威归 design 与 tests.asset-design，本文档若细化执行断言需在变更时回溯设计修订并记录。

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 用例状态 | `Designed` / `Gap`（具名缺口）/ `Tailored-N/A` | 本方案 §3 清单 | 未设计写成已设计；N/A 无设计事实依据 |

<span style="color:#1f6feb"><em>**完成条件**：任一 Case 在本方案中只报设计状态；实现与执行状态可沿 Case ID 追到 case-design 文档与 Run 报告。</em></span>

## 1. 目标、范围与被测对象

<span style="color:#1f6feb"><em>**本节目的**：固定整软件系统组装层的对象与边界。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：被测系统与设计基线；真实子系统；外部依赖真实或边界替身及证明边界；不证明的真实环境与验收目标。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：虚构 EX-APP 方案覆盖启动/配置/停止流程与机制端到端。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：读者能说清系统层测什么、验收承接什么。</em></span>

- **被测对象、设计基线与父对象**：LLMTier V0.3 **软件系统**在安装后的**运行形态**——LAN 上的 `http_api` 网关进程（HTTP 入口/鉴权/序列化、推理编排与上游适配、Registry、观测读/写/注入、SQLite Store 等真实子系统）。设计基线 = `llmtier-system-design`（系统设计，本方案 `parent_document_id`）；被测运行版本以每次 Run 的 artifact pin 锁定（`git_commit` + `db_schema_version` + `openapi_version`），不以下游分支名代替。外部接口的**机器权威**是 `interfaces/openapi/llmtier.openapi.json`。
- **本阶段测试边界（真实组成 / 边界替身）**：被测路径上**全部真实子系统**——真实 HTTP 服务进程、真实 Registry 与 SQLite、真实鉴权与角色解析、真实 SSE 流。外部依赖按两类：**真实外部系统**（m5air/m5mac 上的 OMLX 上游 provider，经 LAN 以真实协议访问）与**受控边界替身**（B 类临时实例的 `_baseline_settings` 种子注册表与本地假上游 provider，其替身只证明**本服务**行为、不证明上游模型推理正确性）。两个环境：**A 类** = m5air 已部署实例（只读/观察/一次性无状态写，不污染 SQLite）；**B 类** = 临时本地实例（临时端口 + 临时 SQLite，承载创建/修改/删除/空库/无鉴权/注入/并发）。A/B 不共享 SQLite/端口/进程，A 类 PASS 不关闭 B 类，反之亦然。
- **不证明的组合保证及承接入口**：本方案不证明真实生产环境（生产 TLS/SSO/MFA、浏览器无 bearer）、不证明上游模型答案质量与推理正确性、不证明 FD 泄漏/30min 耐久/50 并发等容量结论、不证明备份/恢复演练与进程 crash/restart 后的只读运维保证。**真实生产环境与客户/项目验收**不在 tests 家族，按项目 tailoring 由验收活动承接（见 §4）。静态契约一致（`CT-*` 静态 PASS）不等于运行行为 PASS，反之亦然；本层 PASS 不关闭上层组合目标。

## 1.5 测试方法与测试设计技术

<span style="color:#1f6feb"><em>**本节目相**：固定系统层"怎么测"的方法论——单元层测试设计技术比较单一（mock 为主），上游测试常**多方法共存**，需逐一描述与边界。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：测试设计技术（按 Case 家族用哪些——等价类划分/边界值/状态转换/决策表/错误猜测/属性测试/变异测试等，写明对哪些 family 用哪种及不用哪种）；入场标准（设计文档到位、方案清单冻结、Case 实现就绪、替身 Verified、环境齐）；离场标准（分母每条来源有 Case 或缺口、Verdict 齐全、缺口有主、设计变更触发重跑）；自动化策略（哪些进 CI、单 Case 选择入口、断点/重跑规则、flaky 不掩盖根因）。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字——系统层方法（含注入/边界/调用序等具体细节）。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每个 §3 Case 行能指出所用方法与环境类型；入场/离场可判定；环境类型与 asset-design 契约对应；无未声明的环境依赖。</em></span>

| Case 家族 | 测试设计技术 | 环境类型引用 | 自动化与判定规则 |
|---|---|---|---|
| normal / boundary | 等价类划分 + 边界值抽样 + 契约字段比对 | A 类（m5air 真实实例） | pytest + `api_smoke_test.py`；CI 跑全集；失败不阻断后续但须复现 |
| negative | 错误猜测 + 反例驱动（按 §7.8 错误目录 `ERR-*`） | A/B 类 | 断言 HTTP status + 错误信封 `code`/`message`；不模糊注入 |
| concurrency | 状态机驱动 + 固定并发度/种子（`If-Match`/412、准入 429） | B 类临时实例 | 单 Case 选择入口；记录并发度与时间窗；flaky 不掩盖根因 |
| recovery | 故障注入（`fault_502`/`fault_503`/`stream_terminate`/`malformed_event`）+ 客户端断开 | B 类临时实例 | 注入须命中计数>0，否则标 INVALID；复现状态与修复状态分开记录 |
| security | 鉴权/授权/脱敏冒烟 + 角色隔离（`none`/`data`/`admin`） | A/B 类 | 断言 401/403 与脱敏；缺关键替身时降级为 Blocked |

### UI 类测试方法（按行为模式；规定 Case 怎么写与约束）

<span style="color:#1f6feb"><em>**本节目的**：把 UI 行为按**模式**固定下来——每种模式规定「构造什么状态 → 做什么操作 → 断言哪个 DOM → 断言哪个网络调用 → 什么证据」。UI Case 一律按本表择模式撰写；本表同时是 Case 的**约束**（不满足即视为 Case 不完备）。</em></span>

| 行为模式 | 构造（fixture/前置） | 操作 | **必须断言** | 证据 |
|---|---|---|---|---|
| **数据呈现（渲染）** | mock/构造底层数据：临时实例 DB 播种、诊断注入、或固定 API 返回；覆盖 **有值 / 未知 / 空 / 错误** 四态 | 打开页面或触发该区域加载 | 真实 DOM 呈现与数据**一致**：有值显示对应值；未知显示 `Unknown`/`Not refreshed`；**绝不臆造 0**；空显示空态；类型/单位/格式符合契约 | 截图 + 该区域 GET 的网络记录 |
| **交互 → 能力调用（按钮/菜单/表单）** | 目标对象存在且可操作（如某 deployment 可 Pause） | `click` / `submit`（必要时先 `fill`/`check`） | 发出的调用**正确**：方法 + 路径 + 查询/请求体 + 必要头（如 `If-Match`/`confirm`）；**不该调用时断言零调用**；调用失败时 UI 显示错误态而非沉默 | 截图 + `Network.*` 断言 |
| **数据变更（写路径）** | 初始值已知（先 GET/播种） | 在页面上执行编辑/删除/启停/重置 | **两侧都变**：①**服务端数据真的变了**（GET/DB 读回 == 期望）；②**页面重新渲染**反映新值（旧值消失）；非法输入被拒且不改数据 | 改前/改后截图 + 写调用 + 读回调用 |
| **状态转换** | 初始状态已知 | 触发转换（如 Idle→Paused→Idle） | 每个状态的**渲染**正确 + **转换调用**正确；非法转换被拒且 UI 不假装成功 | 截图 + 转换调用 |
| **错误 / 降级** | 注入 API 错误/超时/`5xx` | 触发该请求 | 显示**错误态**且**保留上一屏**（不空白、不臆造、不静默）；可恢复（重试后正常） | 截图 + 错误响应记录 |
| **导航 / 可见性** | 页面已加载 | 切换 tab/页 | `.page.active`（或等价）真的变了；断言**懒加载调用**按需触发（不重复、不遗漏） | 截图 + 网络记录 |
| **门控 / 确认（破坏性/开销性动作）** | 需确认的动作可用 | 先**不确认**点击 → 再确认 | **未确认时断言零调用**；确认后断言调用且成功；取消不产生副作用 | 截图 + 网络记录（前后各一） |
| **脱敏 / 安全呈现** | provider 配了 secret / 日志含敏感值 | 打开展示页或触发日志 | secret 值**永不出现**在 DOM/URL/截图/日志中；只显示脱敏标记 | 截图 + DOM 文本全扫描 |
| **幂等 / 防重** | 动作可触发 | 连点 / 重复提交 | 只发生**一次**有效调用（或幂等语义成立），页面不重复追加 | 网络记录**计数** |
| **边界呈现** | 极值数据（超长文本、大数、0/负、多行、多空字段） | 打开该区域 | 不溢出/不错位/不科学计数失真；与契约呈现规则一致 | 截图 |

**UI Case 约束（不满足即视为 Case 不完备）**：
- **自洽**：复用 B 类临时实例 + LAN 假上游；**不依赖** m5air；数据靠 fixture/注入/播种构造，不靠"碰巧存在"。
- **确定性**：用 `waitFor`/条件等待，**禁止固定 sleep**；断言前确保渲染完成；可重复跑同结果。
- **证据**：每 Case 必产出 **PNG 截图 + 网络日志**；失败保留现场，不截断。
- **独立**：不跨 case 共享可变状态；结束 `finally` 复位（清注入/还原数据/关浏览器）。
- **可证伪**：断言必须"改坏分支就变红"（变异心态）；**禁止**用源码字符串匹配（`assertIn` on `app.js`）替代行为断言。
- **负向也要断**：不仅断"发生了正确调用"，还要断"**不该调用时零调用**"、以及"失败不改数据"。
- **每 Case 必须写明**：模式（本表哪一行）、构造的状态、执行的操作、DOM 断言、网络断言、证据位置。

**UI 方法模式 → Case 覆盖**（本表每行均有真实浏览器 Case 承接；逐 Case 模式标签见各 Case 文档 §1「UI 方法模式」）：

| 行为模式 | 承接 Case |
|---|---|
| 数据呈现（渲染） | `ST-UI-001`（有值）、`ST-UI-004`（未知/空态，绝不臆造 0） |
| 交互 → 能力调用 | `ST-UI-002`（tab 点击 → 正确调用；Home 零调用负向） |
| 数据变更（写路径） | `ST-UI-003`（Pause 启停，**两侧都变**：服务端读回 + 页面重渲染） |
| 状态转换 | `ST-UI-003`（Idle→Paused→Idle） |
| 错误 / 降级 | `ST-UI-007`（注入 500，保留上一屏 + 可恢复） |
| 导航 / 可见性 | `ST-UI-006`（诊断子 tab 切换 + 懒加载按需/零调用负向） |
| 门控 / 确认 | `ST-UI-005`（未确认零调用、确认后一次 POST） |
| 脱敏 / 安全呈现 | `ST-UI-008`（secret 不落 DOM/URL/日志） |
| 幂等 / 防重 | `ST-UI-009`（连点一次有效调用、页面不重复追加） |
| 边界呈现 | `ST-UI-010`（极值文本不溢出/不注入） |

### 测试设计技术选型表（按 Case 家族）

<span style="color:#1f6feb"><em>**本节目的**：固定本层"怎么测"——按 Case 家族显式选用的设计技术与反模式；技术选择归本表不在 §1.5 灰例中重复。</em></span>

| Case 家族 | 选用的设计技术 | 选用理由 | 不选用的反模式 |
|---|---|---|---|
| normal | 等价类划分 + 契约字段比对 | 覆盖合法输入空间，验证主路径 | 不用全部输入矩阵（规模爆炸） |
| boundary | 边界值（上下限/`limit=1`/batch 33/`max_output_tokens=10`） | 边界是缺陷高发区，验证边界 + 边界附近 1 步 | 不用随机/模糊测试（不可复现） |
| negative | 错误猜测 + 反例驱动（错误目录 `ERR-*`） | 异常路径以设计已识别的反例为准 | 不用模糊异常注入（无 Oracle / 无归因） |
| concurrency | 状态机驱动 + 固定并发度/种子 | 并发语义需可控时序；`If-Match`/412 串行化 | 不用随机并发（不可复现 + flaky） |
| recovery | 故障注入 + 有界重试 + 复位阶梯 | 恢复路径与回滚基线需在失败路径覆盖 | 不用"重试即可"模拟恢复（掩盖根因） |
| performance | 单 Case 基线采样 + 观察断言（准入上限/超时/`Retry-After`） | 本层只保留时序/预算类可观察断言，非容量结论 | 不用负载/容量压测（本层不负责系统预算，见 §4 容量/耐久裁决） |
| security | 鉴权/授权/脱敏冒烟 + 角色隔离 | 上游/集成层已覆盖语义，本层验证暴露面 | 不用模糊安全测试（不可复现 + 上游责任） |

## 1.6 替身使用策略与边界

<span style="color:#1f6feb"><em>**本节目相**：固定系统层替身的使用，让 §3 清单的替身选择可解释可复核。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：替身决策准则（按所有权/可控性/真实性分类——内部真实/边界 fake/真协议测试实例/容器等）；替身形态（mock/fake/stub/spy 的取舍与代价）；替身保真度——契约与自检归 `tests.asset-design`（一资产一文档），方案与 Case 只引用其 ID 不复制行为；交互断言 vs 返回值断言（优先返回值，必要时断言关键调用序，但不耦合内部实现）；反模式（不 mock 你不拥有的接口、不 mock 值对象/纯数据、不为凑覆盖率而 mock、不过度断言内部细节）；与 §1 边界、§3 Case 清单、`tests.system-case` §2 替身选择一致。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字——系统层替身矩阵。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每个 §3 Case 行能指出替身类型与契约文档 ID；替身矩阵与 asset-design 一一对应；反模式逐项被排除并有理由。</em></span>

| 协作者类型 | 替身形态 | 替身契约文档（tests.asset-design） | 决策理由 |
|---|---|---|---|
| 被测路径内部子系统（HTTP/Registry/SQLite/鉴权/SSE） | 真实（不替身） | — | 被测对象本体，mock 即失去系统层意义 |
| 上游 OMLX provider（`192.168.1.9:9000`/`192.168.1.8:9000`） | 真协议访问（A 类）；受控假上游（B 类） | 假上游契约（tests.asset-design） | 只证明本服务行为，不证明模型推理正确性 |
| 时钟/时间窗 | 真实系统时间 + 相对窗口断言 | — | 系统层不推进时钟，只用相对时间窗 |

## 1.7 测试环境类型（方案定义）

<span style="color:#1f6feb"><em>**本节目相**：固定本层"在哪类环境上跑"——列出环境**类型**（抽象类别）及其行为/真伪与契约文档（tests.asset-design 或产品规范）；同一类型可多套实例（多 docker 用于并行），具体**实例编号与分配**由 `tests.system-test-plan` §4 编排，Case 在 §2 通过「环境类型 + ENV 实例编号」引用，不在本文档重复描述环境本身。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字——系统层测试环境类型（含契约与用法具体细节）+ 环境拓扑（ENV 类型 → ENV 实例 → 被测对象）。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每个 §3 Case 行能指出所用环境类型；类型与 asset-design 契约对应；无未声明的环境依赖。</em></span>

| 环境类型 | 行为/真伪 | 契约文档 | 在本层用例中的角色 |
|---|---|---|---|
| A 类：m5air 已部署实例 | 真实（只读/观察/一次性无状态写，不污染 SQLite） | `m5air-deploy-guide.md`/`m5air-operations-manual.md` | 只读观察面与无状态写用例（HEALTH/DP-*/只读 ADM-*） |
| B 类：执行机临时实例 | 真实进程＋临时端口＋临时 SQLite | `testing-standard.md`（TS-002/TS-003） | CRUD/空库/无鉴权/注入/并发用例（`_baseline_settings` 种子） |
| UI 类：真实浏览器 over CDP（复用 B 类实例） | **驱动**：真实 headless Chrome/Chromium（`LLMTIER_BROWSER`）经 CDP 驱动真实 `src/web_ui`，node ≥22 内置 WebSocket、无 npm/下载。**交互操作**：`click`（真实 `el.click()`）、`fill`（设 `value` 并派发 `input`+`change`）、`submit`、`check`、`waitFor`。**观测与断言**：真实 DOM 查询、`.page.active`、以及 CDP `Network.*`（请求/响应/请求头）断言（`assert`/`assertText`/`assertActive`/`assertNetwork`/`assertRequestHeader`/`assertNetworkCount`/`assertNoNetwork`/`waitForNetwork`；支持步骤级命名截图）。**证据**：每 Case 产出 PNG 截图（`Page.captureScreenshot`，含改前/改后等命名截图）＋网络日志，落 `tests/system/artifacts/<case>/`。**判定**：步骤级 DOM 断言＋网络断言（行为级，非源码字符串）。**边界**：hermetic 临时实例＋LAN 假上游；无浏览器/node<22 → 整类 SKIP（非缺口） | `testing-standard.md`（TS-002/TS-003）＋ `tests/common/drivers/browser_driver.mjs` | UI 行为级用例（`ST-UI-001..010`）：页面渲染/交互能力调用/tab 切换/数据变更（两侧）/用量未知/门控确认/诊断页/错误降级与恢复/脱敏/幂等防重/边界呈现（同源 `/ui/`，`-m ui`） |

<span style="color:#6e7681">**拓扑**（ENV 类型 → ENV 实例 → 被测对象）：</span>

- **ENV 类型 A（m5air 实例）** → ENV 实例编号由 `tests.system-test-plan` §4 分配 → 被测对象＝m5air 上的 `http_api` 进程（`192.168.1.9:8181`）。
- **ENV 类型 B（临时实例）** → 每 run 随机空闲端口＋`tempfile.mkdtemp(prefix="llmtier_b_")` 临时 SQLite → 被测对象＝执行机本机 `http_api` 子进程。

**总体说明**：A/B 不共享 SQLite/端口/进程且不并行（A 类 PASS 不关闭 B 类，反之亦然）；A 类就绪失败只 skip A 类，B 类用各自临时实例照跑（A/B 独立判定）；A 类写用例 teardown 后复位，B 类整班销毁；缺关键环境时**按类**降级为 Blocked 并登记缺口（A 类缺 m5air 就绪 / B 类缺 LAN IP 或基线 probe 不健康），不静默换工具链。**B 类静默 skip 提示**：执行机无 RFC1918 LAN IP 时 `_detect_lan_ip()` 使 B 类 fixtures `pytest.skip`，须以 Run 记录的 skip 计数核对，不得当 PASS（详见 plan §6-B）。

> 环境拓扑（ENV 类型 → ENV 实例 → 被测对象）以本表与上下两条为准；STD 模板附带的 `system-env-topology.svg` 为虚构教学图，本项目未引入（项目图资产统一存 `docs/assets/diagrams/`）。

## 2. 测试分类体系

<span style="color:#1f6feb"><em>**本节目的**：固定本阶段的测试分类体系与适用裁剪。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：采用 STD 统一家族词表（normal/boundary/negative/concurrency/recovery/security/performance/endurance），逐类声明本阶段适用性与裁剪依据；不适用不等于没写 Case，须在 §4 给事实。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字分类示例。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：分类体系可裁剪可追溯，每个适用分类在 §3 清单中至少有 Case 或缺口。</em></span>

| 分类（STD 家族词表） | 本阶段适用性 | 裁剪依据 |
|---|---|---|
| normal | 适用 | 50 个 Case：各端点正向契约（清单/精确返回/SSE 成功/embedding/CRUD 正常流/健康就绪等）。 |
| boundary | 适用 | 7 个 Case：大小写与 URL 编码、`limit=1` 分页、`max_output_tokens=10`、batch 33、分页重放等边界。 |
| negative | 适用 | 57 个 Case：校验/鉴权/资源冲突/上游错误/存储不可用等拒绝路径（含 400/401/403/404/409/412/413/429/503）。 |
| concurrency | 适用 | 7 个 Case：准入饱和 429+`Retry-After`（`ST-RESP-020`、`ST-EMB-008`）、`If-Match`/412 串行化并发编辑、注入变更与在途流（`ST-PROV-005/06/07`、`ST-DEPL-004`、`ST-SL-004`）。 |
| recovery | 适用 | 26 个 Case：故障注入（`fault_502`/`fault_503`/`stream_terminate`/`malformed_event`）、上游/存储失败、客户端断开、账本崩溃/重启恢复（`ST-USAGE-009`）、`/readyz` degraded/not_ready、schema 引导不可用。 |
| security | 适用 | 16 个 Case：认证/授权/角色隔离、LAN trust、无鉴权配置、secret 不泄露、审计与日志脱敏、别名命名空间鉴权。 |
| performance | 裁剪 | 纯软件、无 FPGA/硬件时序；本阶段只保留**时序/预算类可观察断言**（准入队列上限、超时路径、`Retry-After`），**不发布 SLO/容量结论**。功耗/容量压测（FD 泄漏、30min 耐久、50 并发）不在本方案分母内；原 `llmtier-test-plan`（已退役）的 ST-18/19/21 容量项现按 §4 Tailored-N/A（非缺口）由运维/性能专项承接（tailoring）。 |
| endurance | 裁剪 | 长稳/耐久另立专项，不在本方案分母内（tailoring）；见 §4 容量/耐久裁决（Tailored-N/A）。 |

> 上表与 §3 清单交叉核对：normal 50 + boundary 7 + negative 57 + concurrency 7 + recovery 26 + security 16 = **163**。未列入的任何 STD 家族分类在本阶段**不适用**（见 §4 裁决）。



## 3. 覆盖分母与 Case 清单

<span style="color:#1f6feb"><em>**本节目的**：把 design.software-system 的适用来源 ID 转成 Case 清单——测试分母的唯一登记。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：一个来源 ID 至少一条记录（可多 Case 分担，分别写责任摘要）；以设计文档（design §12/§14）的验证项 VRC 清单为分母逐项对账：每个 VRC 至少一个 Case——验证项是设计声明的必测点，本清单只引用其 ID 不复制定义、不做附录；Case ID 稳定且唯一（ST-<对象>-<NNN>）；责任摘要只写“要测什么、边界在哪”，不写输入与 Oracle；设计状态按状态语义；未实现与 NOT_RUN 不删；不适用转 §4。</em></span>

> 来源 ID 与设计验证项（VRC）的边界：本表登记 ID+责任摘要；判据/Oracle/Owner/契约权威归 design 与 tests.asset-design，不在此行复写；变更设计时同步 VRC 同步本清单。
<span style="color:#1f6feb"><em>**抽象示例**：见下表灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每个适用来源 ID 有 Case 或缺口；每个设计验证项（VRC）至少一个 Case 或在 §4 登记缺口；每个 Case ID 可追到（或计划有）case-design 文档。</em></span>

| 来源 ID / 固定版本 | 设计验证项 ID | Case ID | 分类（STD 家族） | 优先级 | 责任摘要（要测什么） | 设计状态 | 上级组合验证入口 |
|---|---|---|---|---|---|---|---|
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-API-002 | ST-HEALTH-001 | normal | P0 | healthz 始终存活 | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003 | ST-HEALTH-002 | normal | P0 | readyz 就绪=全部 tier 可用 | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003 | ST-HEALTH-003 | recovery | P1 | readyz degraded | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003、VRC-UTIL-001 | ST-HEALTH-004 | recovery | P0 | readyz not_ready（无 deployment） | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003、VRC-UTIL-001 | ST-HEALTH-005 | recovery | P1 | readyz bootstrap 失败 | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-API-002、VRC-MGMT-003 | ST-HEALTH-006 | normal | P1 | 健康端点无需鉴权 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-002 | ST-MODEL-001 | normal | P0 | 列出全部可见 tier | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | ST-MODEL-002 | normal | P0 | 精确返回模型 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | ST-MODEL-003 | negative | P0 | 大小写敏感（小写） | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | ST-MODEL-004 | negative | P1 | 大小写敏感（全大写） | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | ST-MODEL-005 | negative | P1 | URL 编码尾空格不匹配 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | ST-MODEL-006 | negative | P0 | 不存在模型 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-002 | ST-MODEL-007 | boundary | P1 | capabilities 固定 12 键 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-001 | normal | P0 | 流式成功 + 事件序列 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-002 | negative | P0 | stream=false 被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-003 | normal | P1 | 推理输出结构（不含内容 oracle） | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-004 | normal | P1 | tools 透传 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-005 | negative | P0 | unknown model 路由失败 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-006 | normal | P0 | stream=true 唯一受理形态 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-007 | negative | P0 | store=true 被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-008 | negative | P0 | 缺 model | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-009 | negative | P0 | 禁字段 previous_response_id | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-010 | boundary | P1 | max_output_tokens 截断 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | ST-RESP-011 | recovery | P0 | 注入上游 502 → provider_failure | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-012 | negative | P2 | conversation_id 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-013 | negative | P2 | truncation 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-014 | negative | P2 | max_tokens 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-015 | negative | P2 | temperature 接受 / top_p 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-016 | recovery | P1 | 非法 JSON body | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-017 | recovery | P1 | embedding-only 等级发 Responses | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-018 | recovery | P2 | body 超 2 MB | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-004 | ST-RESP-019 | recovery | P1 | 全部候选不健康 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-004 | ST-RESP-020 | concurrency | P1 | 准入饱和 → 429 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-021 | recovery | P1 | 客户端中途断开 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | ST-RESP-022 | recovery | P1 | 注入上游 503 → provider_unavailable | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-003 | ST-RESP-023 | recovery | P1 | 上游非 5xx → provider_error | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-024 | recovery | P1 | provider 凭据缺失 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | ST-RESP-025 | recovery | P1 | 上游契约错误 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | ST-RESP-026 | recovery | P1 | 流截断注入 stream_terminate | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | ST-RESP-027 | recovery | P1 | 畸形事件注入 malformed_event | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001、VRC-INF-002 | ST-EMB-001 | normal | P0 | 基本 embedding | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | ST-EMB-002 | normal | P0 | base64 编码 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-002 | ST-EMB-003 | normal | P1 | 不变量（同输入 ×5） | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | ST-EMB-004 | negative | P0 | unknown model | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-002 | ST-EMB-005 | boundary | P2 | batch 33 不强制上限 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | ST-EMB-006 | negative | P1 | dimensions 与冻结空间不符 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | ST-EMB-007 | negative | P2 | 非法 encoding_format | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-004 | ST-EMB-008 | concurrency | P1 | embeddings 准入饱和 429 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | ST-EMB-009 | recovery | P1 | embeddings 上游契约错误 502 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-004 | ST-EMB-010 | recovery | P1 | embeddings 上游不可用 503 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-001 | normal | P0 | 时间窗查询 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-002 | normal | P1 | 请求后可见记录 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-003 | boundary | P1 | cursor 分页 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-004 | negative | P2 | 过期 cursor | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-005 | negative | P1 | 缺 from/to | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-006 | normal | P1 | 主体隔离：data 只见自身，admin 见全局 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-007 | boundary | P1 | 分页重放幂等 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | ST-USAGE-008 | recovery | P1 | store 不可用不返回空页 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage）；机制 §15 计量（T-MET-CRASH） | VRC-INF-004、VRC-MGMT-006 | ST-USAGE-009 | recovery | P0 | 账本崩溃/重启恢复（orphan unknown 不回填 0） | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-001 | normal | P0 | 列出 providers | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-002 | normal | P0 | 创建 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-003 | normal | P0 | 获取 provider 详情 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-004 | negative | P0 | 不存在 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ST-PROV-005 | concurrency | P0 | 更新 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ST-PROV-006 | concurrency | P0 | 更新缺 If-Match | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ST-PROV-007 | concurrency | P1 | 过期 ETag | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-008 | normal | P0 | 删除 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ST-PROV-009 | negative | P1 | 删除缺 If-Match | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-010 | negative | P1 | 删除被引用 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-011 | negative | P1 | kind 枚举校验 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-012 | normal | P2 | secret_ref 格式 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ST-PROV-013 | normal | P2 | usage 子对象更新 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-014 | security | P0 | provider 不泄露 secret | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-015 | negative | P1 | 创建 provider data token 403 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ST-PROV-016 | negative | P1 | 更新 provider data token 403 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ST-PROV-017 | negative | P1 | 删除 provider data token 403 | 已设计 | — |
| 系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models） | VRC-MGMT-001 | ST-PMOD-001 | normal | P1 | provider 上游模型目录 | 已设计 | — |
| 系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models） | VRC-MGMT-001 | ST-PMOD-002 | negative | P1 | 不存在 provider | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006 | ST-PUSAGE-001 | normal | P1 | 读取 provider usage 快照 | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006、VRC-DIAG-004 | ST-PUSAGE-002 | negative | P1 | 刷新缺确认 | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006、VRC-DIAG-004 | ST-PUSAGE-003 | normal | P1 | 刷新带确认 | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006 | ST-PUSAGE-004 | negative | P1 | usage 未知 provider | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-001 | normal | P0 | 列出 deployments | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-002 | normal | P0 | 创建 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-003 | normal | P0 | 获取 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-002 | ST-DEPL-004 | concurrency | P1 | 更新 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-005 | normal | P0 | 删除 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-006 | negative | P1 | capabilities 缺字段 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-007 | negative | P1 | capabilities 未知字段 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-008 | negative | P1 | 引用不存在 provider | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-002 | ST-DEPL-009 | negative | P1 | provider_id 不可 PATCH | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-010 | negative | P1 | 创建 deployment data token 403 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-002 | ST-DEPL-011 | negative | P1 | 更新 deployment data token 403 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ST-DEPL-012 | negative | P1 | 删除 deployment data token 403 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-001 | normal | P0 | 列出 service-levels | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-002 | negative | P1 | 创建非 fixed tier | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-012 | negative | P1 | 创建已存在 fixed tier | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-003 | normal | P0 | 获取 service-level | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-004 | concurrency | P1 | 更新 service-level | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-013 | negative | P1 | 更新非法字段 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-005 | negative | P0 | 删除 fixed tier | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-006 | negative | P2 | 成员能力不一致 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-007 | negative | P2 | 冻结向量空间冲突 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-008 | recovery | P2 | 内部错误信封（非数组输入） | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-009 | negative | P1 | 创建 service-level data token 403 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-010 | negative | P1 | 更新 service-level data token 403 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ST-SL-011 | negative | P1 | 删除 service-level data token 403 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ST-PROBE-001 | negative | P0 | 探测缺确认 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ST-PROBE-002 | normal | P1 | 探测带确认 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ST-PROBE-003 | negative | P1 | 探测未知 deployment | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-INF-004 | ST-RUNTIME-001 | normal | P1 | 运行时快照 | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-INF-004 | ST-RUNTIME-002 | security | P1 | 运行时快照负向（角色） | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-API-002 | ST-RUNTIME-003 | security | P2 | 运行时快照缺凭据 401 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ST-STATS-001 | normal | P1 | 统计聚合 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ST-STATS-002 | normal | P2 | 分组 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ST-STATS-003 | negative | P1 | 缺时间窗 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ST-STATS-004 | negative | P1 | 统计接口 data token 403 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ST-AUDIT-001 | security | P0 | 审计事件 + 脱敏 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-006 | ST-AUDIT-002 | boundary | P1 | 审计分页 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ST-AUDIT-003 | negative | P1 | 审计非法分页参数 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ST-AUDIT-004 | negative | P1 | 审计接口 data token 403 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ST-LOGS-001 | security | P0 | 脱敏日志 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ST-LOGS-002 | negative | P1 | 缺时间窗 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ST-LOGS-003 | negative | P1 | 日志接口 data token 403 | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ST-AUSAGE-001 | normal | P1 | 管理面 usage | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ST-AUSAGE-002 | boundary | P1 | 管理面分页 | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ST-AUSAGE-003 | normal | P1 | 清空 usage（admin + 审计） | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | ST-OBSDIAG-001 | normal | P1 | 读取诊断开关 | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | ST-OBSDIAG-002 | normal | P1 | 更新诊断开关 | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | ST-OBSDIAG-003 | negative | P2 | 开关更新非法值 | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | ST-OBSSNAP-001 | normal | P1 | 快照页（脱敏） | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | ST-OBSSNAP-002 | recovery | P2 | 快照无效 cursor | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | ST-OBSSNAP-003 | recovery | P1 | 诊断快照 store 不可用 503 | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | ST-OBSSTATS-001 | normal | P1 | 诊断统计窗口 | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | ST-OBSSTATS-002 | negative | P1 | 统计缺 since/until | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | ST-OBSSTATS-003 | recovery | P1 | 诊断统计 store 不可用 503 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | ST-OBSTRACE-001 | normal | P1 | trace 列表去重 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | ST-OBSTRACE-002 | recovery | P2 | trace 列表分页/游标 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | ST-OBSTRACE-003 | recovery | P1 | 诊断 trace store 不可用 503 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | ST-OBSDEPL-001 | normal | P0 | 读取 deployment 注入配置 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | ST-OBSDEPL-002 | normal | P0 | 写入故障注入 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | ST-OBSDEPL-003 | negative | P1 | 注入未知 deployment | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | ST-OBSDEPL-004 | negative | P1 | 非法注入项 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | ST-OBSDEPL-005 | recovery | P1 | 写入故障注入 store 不可用 503 | 已设计 | — |
| 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） | VRC-DIAG-002 | ST-OBSREQTRACE-001 | normal | P1 | 请求全生命周期 trace | 已设计 | — |
| 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） | VRC-DIAG-002 | ST-OBSREQTRACE-002 | negative | P1 | 未知 request_id | 已设计 | — |
| 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） | VRC-API-002 | ST-OBSREQTRACE-003 | security | P1 | 请求追踪负向（角色） | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-001 | ST-OBSALIAS-001 | normal | P1 | 别名 diagnostics（GET+PATCH） | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | ST-OBSALIAS-002 | normal | P2 | 别名 diagnostics/snapshots | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | ST-OBSALIAS-003 | normal | P2 | 别名 trace | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-004 | ST-OBSALIAS-004 | normal | P2 | 别名 deployments diagnostics（GET+PATCH） | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | ST-OBSALIAS-005 | normal | P2 | 别名 diagnostics/stats | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | ST-OBSALIAS-006 | normal | P2 | 别名 diagnostics/traces | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-001 | security | P0 | Data 端点 LAN trust 无 token | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-002 | security | P0 | 错误 bearer | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-003 | security | P0 | Data token 访问 admin 面 | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-004 | security | P0 | Admin 端点 LAN trust 无 token | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-005 | security | P0 | 公共端点无需 token | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-006 | security | P2 | 空 bearer | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-MGMT-003 | ST-AUTH-007 | security | P0 | 未配置鉴权 | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-008 | security | P1 | 别名命名空间需 admin | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-009 | security | P1 | 管理面未授权优先于资源存在性 | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | ST-AUTH-010 | security | P1 | 缺/非法凭据 401 | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；系统设计 §8 同源 `/ui/` 静态服务 | VRC-UI-001 | ST-UI-001 | normal | P1 | 真实浏览器渲染页面与 Provider 行（来自 API 数据） | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1） | VRC-UI-001 | ST-UI-002 | normal | P1 | 真实浏览器 tab 切换改可见区并触发对应 API | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`RULE-UI-ETAG`/`RULE-UI-PAUSE` | VRC-UI-003 | ST-UI-003 | boundary | P1 | 真实浏览器确认门控 Pause 发 If-Match PATCH 并重渲染 | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`RULE-UI-UNKNOWN` | VRC-UI-004 | ST-UI-004 | normal | P0 | 真实浏览器用量未知渲染 Unknown 不臆造零点 | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`RULE-UI-PROBE` | VRC-UI-005 | ST-UI-005 | boundary | P1 | 真实浏览器未确认探测不触网、确认后 POST | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`F-UI-DIAG`/`R-OBS-05` | VRC-UI-006 | ST-UI-006 | normal | P1 | 真实浏览器诊断页 4 tabs 与 Disabled 视觉 | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`RULE-UI-TIERSTATE`/`reportLoadFailure` | VRC-UI-002 | ST-UI-007 | recovery | P0 | 真实浏览器注入 API 错误显示错误态并保留上一屏（并可恢复） | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；系统设计 §8 同源 `/ui/` 静态服务；脱敏契约（provider 视图仅暴露 `has_secret`） | VRC-UI-001 | ST-UI-008 | security | P1 | 真实浏览器配了 secret 的 provider 只显示脱敏标记，secret 值不落 DOM/URL/日志（§1.5 脱敏/安全呈现模式） | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`RULE-UI-PROBE` | VRC-UI-005 | ST-UI-009 | boundary | P1 | 真实浏览器探测按钮连点只发一次有效调用、页面不重复追加（§1.5 幂等/防重模式） | 已设计 | — |
| 模块设计 web-ui §14（ISD §9.1）；`esc()` 转义契约 | VRC-UI-001 | ST-UI-010 | boundary | P2 | 真实浏览器极值文本渲染不溢出、不注入、不破坏布局（§1.5 边界呈现模式） | 已设计 | — |

**Case 总数：173（设计数）**（分类：normal 53 / boundary 11 / negative 57 / concurrency 7 / recovery 27 / security 17；环境 A 102 / B 61 / UI 10；Priority P0 47 / P1 98 / P2 25）。**设计数 = 已实现数 173**：原 163 个设计 Case 均有 `ST-*.py`（文件名＝Case ID）自动化入口（`--collect-only` 实际 collect=176 项，多出者为参数化/双臂测试——`-m api_a`＝105、`-m api_b`＝71）；**真实浏览器 UI Case（`ST-UI-001..010`，环境列 `UI`/`-m ui`）由 `tests/system/cases/ST-UI-001.py` + `tests/common/drivers/browser_driver.mjs`（headless Chrome over CDP）实现**，取代此前仅有的源码字符串契约（关闭 `RISK-UI-EXEC-1`）；本版按 §1.5 UI 方法表补齐 `ST-UI-008`（脱敏/安全呈现）、`ST-UI-009`（幂等/防重）、`ST-UI-010`（边界呈现），并使 `ST-UI-003` 落实「两侧都变」、`ST-UI-007` 落实「可恢复」。逐 Case 的输入/执行/Oracle/判定/证据/清理见 `tests.system-case` 文档（`cases/<lowercased-case-id>.md`），本方案不展开。

**设计验证项覆盖**：本清单 `设计验证项 ID` 取自各 Case 的 `tests.system-case` 文档所声明的设计验证项（`ST-RESP-016`/`ST-RESP-023` 两 Case 的 case 文档未声明，按系统设计 §7.8 错误目录 `ERR-REQ-JSON`→`VRC-INF-001`、`ERR-PROVIDER-FAIL`→`VRC-INF-003` 反查补全；未新增任何 VRC ID）。设计文档（系统设计 §7/§8/§14、机制 §15、模块设计 §14、ISD §9.1）共声明 **33 个设计验证项**；本清单覆盖 **20 个**（较上版新增 `VRC-UI-001..006` 六项——由新增的真实浏览器 Case `ST-UI-001..010` 直接承接），**13 个无系统层 Case**（逐项裁决见 §4 本版审计重分类：**13 项为 (a) COVERED**——模块级验证项有真实**单元行为测试**直接断言，指向具体 `test_*`；原 3 项 (c) REAL HOLE 中 `VRC-UI-001..006` 已由真实浏览器执行关闭 `RISK-UI-EXEC-1`，`VRC-OBS-*` 纯视觉子项中「诊断页 tabs/Disabled 实际渲染」已由 `ST-UI-006` 承接、其余视觉子项已由 `ST-UI-002/006` 覆盖诊断页渲染）。逐项覆盖数：`VRC-INF-001` 31、`VRC-MGMT-006` 21、`VRC-MGMT-001` 22、`VRC-MGMT-002` 22、`VRC-API-002` 13、`VRC-DIAG-002` 15、`VRC-DIAG-004` 15、`VRC-MGMT-003` 9、`VRC-INF-002` 5、`VRC-DIAG-001` 4、`VRC-INF-004` 7、`VRC-UI-001` 4、`VRC-UI-002` 1、`VRC-UI-003` 1、`VRC-UI-004` 1、`VRC-UI-005` 2、`VRC-UI-006` 1、`VRC-LOG-001` 3、`VRC-UTIL-001` 2、`VRC-INF-003` 1。

### 3.6 需求（`LT-*`）到 Case 的可追溯映射（§3 的 §3.6-等价节）

> 命名沿用已退役 `llmtier-api-test-specification` §3.6 的链式定义（`LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case 家族），**不新增顶层章节**（本节是 §3 的子节）。链的**唯一权威来源**是需求文档 [`llmtier-requirements.md`](../../10_requirements/llmtier-requirements.md) 的 `LT-*` 条目、系统设计、机制需求与 `CT-*` 静态契约；本节只登记映射，不复制定义。Case 家族按 Case ID 前缀分组，成员以 §3 清单为准（含本版新增 23 个 Case）。任一 case 文档的"目的/来源"字段可回指本表。

| Case 家族（按 §3 前缀） | 需求 `LT-*` | 机制需求 `R-*` | 设计验证 `VRC-*` | 机制 `T-*` | 契约 `CT-*` |
|---|---|---|---|---|---|
| `ST-HEALTH-*` | LT-FUN-006、LT-OPS-001 | R-CFG-02、R-TRUST-04 | VRC-API-002、VRC-MGMT-003、VRC-UTIL-001 | T-TRUST-NOCFG、T-OBS | CT-OPS-001 |
| `ST-MODEL-*` | LT-FUN-002 | R-INF-04、R-INF-07 | VRC-INF-001/002 | T-TRUST-ENDPOINTS | CT-MODEL-001 |
| `ST-RESP-*` | LT-FUN-001/008、LT-INT-001/006、LT-PERF-001、LT-REL-001 | R-INF-01..06、R-TRUST-01、R-TRUST-02 | VRC-INF-001/003/004、VRC-DIAG-004 | T-STREAM、T-TOOLS、T-QUEUE、T-TIMEOUT、T-DISCONNECT、T-OBS-INJECT | CT-DP-001、CT-BOUNDARY-001、CT-ADM-001 |
| `ST-EMB-*` | LT-FUN-003、LT-OPEN-02 | R-INF-04/05/07 | VRC-INF-001/002/004 | T-QUEUE（准入）、T-STREAM（无） | CT-EMB-001 |
| `ST-USAGE-*` | LT-FUN-004、LT-INT-004/005/007、LT-REL-003 | R-MET-01..04 | VRC-MGMT-006、VRC-INF-004 | T-MET-FINAL、T-MET-PAGE、T-MET-RESET、T-MET-UNKNOWN、T-MET-CRASH（`ST-USAGE-009`） | CT-USAGE-001、CT-STORE-001 |
| `ST-PROV-*` | LT-FUN-005、LT-SEC-001、LT-INT-008、LT-REL-004 | R-CFG-01、R-CFG-03 | VRC-MGMT-001/002 | T-CFG-CAS、T-CFG-SECRET、T-CFG-DELREF、T-CFG-BADREF、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ST-PMOD-*` | LT-FUN-005 | R-CFG-01 | VRC-MGMT-001 | T-CFG-SECRET | CT-ADMIN-001 |
| `ST-PUSAGE-*` | LT-FUN-005/006、LT-OPS-002 | R-CFG-01、R-OBS-01 | VRC-MGMT-006、VRC-DIAG-004 | T-CFG-SECRET | CT-ADMIN-001、CT-OPS-001 |
| `ST-DEPL-*` | LT-FUN-005、LT-INT-008 | R-CFG-01 | VRC-MGMT-001/002 | T-CFG-CAS、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ST-SL-*` | LT-FUN-005、LT-PERF-002 | R-CFG-01 | VRC-MGMT-002 | T-CFG-SPACE、T-CFG-CAS、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ST-PROBE-*`/`ST-RUNTIME-*`/`ST-STATS-*`/`ST-AUDIT-*`/`ST-LOGS-*`/`ST-AUSAGE-*` | LT-FUN-005/006、LT-OPS-002/006、LT-SEC-002/004、LT-INT-002 | R-OBS-01/02、R-MET-03、R-CFG-01、R-INF-03 | VRC-MGMT-003/006、VRC-LOG-001、VRC-DIAG-001、VRC-INF-004 | T-OBS、T-MET-RESET、T-MET-PAGE | CT-ADMIN-001、CT-LOG-001、CT-OPS-001、CT-USAGE-001 |
| `ST-OBSDIAG-*`/`ST-OBSSNAP-*`/`ST-OBSSTATS-*`/`ST-OBSTRACE-*`/`ST-OBSDEPL-*`/`ST-OBSREQTRACE-*`/`ST-OBSALIAS-*` | LT-FUN-005、LT-OPS-006、LT-INT-002/007、LT-SEC-002 | R-OBS-01..06 | VRC-DIAG-001/002/004 | T-OBS-SWITCH、T-OBS-SNAP、T-OBS-STATS、T-OBS-TRACE、T-OBS-INJECT | CT-ADMIN-001、CT-LOG-001 |
| `ST-AUTH-*` | LT-INT-001、LT-SEC-001 | R-TRUST-01..04 | VRC-API-002、VRC-MGMT-003 | T-TRUST-BEARER、T-TRUST-LAN、T-TRUST-SHARED、T-TRUST-NOCFG、T-TRUST-LEAK、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ST-UI-*`（真实浏览器 UI） | LT-FUN-005（控制台）、LT-OPS-006（可观测） | R-OBS-05 | VRC-UI-001..006 | T-UI-*（T-UI-01..12 相位）、T-OBS-SWITCH（诊断页） | CT-ADMIN-001（同源 API）、RULE-UI-* |

**需求覆盖结论（35 项 `LT-*`）**：上表以"家族级"重建追溯链，**26 项有 Case 家族承接**（`LT-FUN-001..006/008`、`LT-INT-001/002/004/005/006/007/008`、`LT-OPEN-02`、`LT-OPS-001/002/006`、`LT-PERF-001/002`、`LT-REL-001/003/004`、`LT-SEC-001/002/004`），**9 项不在本运行层分母**（逐项见下方「需求缺口裁决」，**全部定稿 Tailored-N/A，无具名 Gap**）：`LT-FUN-007`、`LT-INT-003`、`LT-REL-002`（静态 absence/边界，由 `CT-BOUNDARY-001`/`CT-SCOPE-001`、`tests/system/st_04_forbidden_scan.py` 与 `tests/contract/test_contract_semantics_v03.py` 承接，非本运行层分母）；`LT-OPS-003/004/005`、`LT-OPEN-03`（运维/实现 Gate 承接，权威＝运维手册与 release 文档）；`LT-PERF-003`（声明性约束，权威＝release §7）；`LT-SEC-003`（生产 TLS/SSO 部署面，权威＝`std-tailoring` `LT-TL-022`）。**家族级覆盖 ≠ 逐 Case 文档均引用该 `LT-*`**：本表是设计级映射权威，不要求每个 case 文档重复列出家族内全部 `LT-*`；case 文档按需引用其直接相关者。原评审以"逐 case 文档字面出现"计数（18/35）低估了这些家族级承接；本表按 STD 需求→Case 追溯语义重建。

## 4. 不适用与缺口裁决

<span style="color:#1f6feb"><em>**本节目的**：区分“不适用”与“尚未设计”。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：Tailored-N/A 必须引用设计章节事实；Gap 须有 Owner 与恢复条件；两者都不从分母静默消失。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每条裁决有事实或 Owner；无“顺手 N/A”。</em></span>

> **模块级验证项裁决依据（本版审计重分类，重要）**：下表中模块级验证项（`VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`、`VRC-UI-001..006`）是**模块设计 §14 的验证项**，系统层清单不承载其中内部行为者。**本项目未采用独立模块测试层**——不存在 `tests.module-test-scheme`（需 `LT-TL-023` 同级授权，当前无）。各模块 §14 验证项的**行为级承接方**是 `llmtier-unit-test-scheme` §3（被测模块内部真实、仅替换进程外上游），**不是**任何"模块测试设计"。本版按任务要求**逐项审计并按事实重分类**（不再一律写成 `Tailored-N/A`）：
>
> - **(a) COVERED（16 项）**：`VRC-API-001/003/004`、`VRC-INF-005`、`VRC-UTIL-002`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`（**行为级**）——均有**真实单元行为测试**（非字符串契约）直接断言，逐项证据见下表。系统层清单不重复承载，但**它们是真实被验证的**，不是"缺失"。
> - **(c) REAL HOLE → 本版已关闭（原 7 项 → 0 项）**：`VRC-UI-001..006` 与 `VRC-OBS-*` 的**纯视觉/真实 JS 执行子项**原为具名开放 RISK `RISK-UI-EXEC-1`（本项目 harness 原无浏览器/JS 宿主，`UT-UI-*`/`UT-OBS-*` 只做**字符串契约断言**）。**本版引入真实浏览器 harness（headless Chrome over CDP）并新增系统层 Case `ST-UI-001..010`，在真实 DOM 与真实网络上执行 UI 行为，`RISK-UI-EXEC-1` 关闭**（见下表第二行与系统计划 §10-O6）。`UT-UI-*` 的字符串契约保留为**快速下位防线**，不再单独承担行为验证。
> - **(a) COVERED（新增浏览器行为级，6 项）**：`VRC-UI-001..006` 现由 `ST-UI-001..010`（真实浏览器）直接承接，逐项映射见下表。

> **本表裁决口径（本版审计）**：适用性裁决分三类——**(a) COVERED**（有真实行为测试，指向具体 case/test，含真实浏览器 UI Case）、**(b) OUT-OF-SCOPE**（不在 tests 家族，引用 STD tailoring/设计/ADR 权威）、**(c) REAL HOLE**（登记为具名、有 Owner 的 RISK 或补 Case）。**本版 (c) 归零**：唯一 REAL HOLE `RISK-UI-EXEC-1` 已由真实浏览器执行关闭，无"静默 N/A"。

| 来源 ID / 事实依据 | 裁决（Tailored-N/A / 已关闭 / 已覆盖） | Owner / 权威与恢复条件 |
|---|---|---|
| **子系统测试级别** | Tailored-N/A | 本项目**无 `design.subsystem` 设计文档**：LLMTier 是纯软件系统，软件系统设计（`llmtier-system-design`）直接展开为模块（M001/M003/M004/M005/M006/M007 等），不存在软件子系统对象。故不采用 `tests.subsystem-test-scheme`；系统层方案直接承接系统设计 §7/§8 与机制端到端的测试分母。若将来引入 `design.subsystem`，本裁决须重新评审并补建子系统方案。 |
| 验收活动 | Tailored-N/A（不在 tests 家族） | 客户/项目验收与 release 放行授权**不属于 tests 家族**（STD 模板选择规则：验收按项目 tailoring 承接）。本方案不承载验收判定；`Gate` 只给放行建议，不等于验收或上线授权。 |
| 真实生产环境（TLS 反向代理、生产 SSO/MFA、浏览器无 bearer、HttpOnly/CSRF） | **Tailored-N/A（定稿；非 Gap；不在 tests 家族）** | Owner：运维/安全。**权威**：STD 模板选择规则（验收/生产部署活动按项目 tailoring 承接，不在 tests 家族）＋ `std-tailoring.md` `LT-TL-022`（验收/运行时激活为 deferred）＋ `llmtier-release-and-operations.md` §10（目标 runbook）、§11（production acceptance 前置）。**事实**：production TLS/SSO/CSRF 是反向代理/部署面行为，本项目测试 harness 是 LAN 上 HTTP 黑盒，无 TLS/SSO 终止端；`runtime_activation=false`（OpenAPI `x-llmtier-runtime-activation=false`），激活证据属运维 Gate。故**不写空 Case**；`LT-SEC-003` 同此裁决。恢复条件＝生产部署面可用且 `runtime_activation` 决策启动后，由验收活动（`LT-TL-022`）承接。 |
| 上游模型答案质量与推理正确性 | **Tailored-N/A（定稿；非 Gap；不在测试分母）** | Owner：模型/推理。**权威**：`llmtier-requirements.md` `LT-PERF-003`/§10「静态 PASS 不证明实现上线」＋ `llmtier-system-design` §1 范围（本系统不拥有模型权重/推理正确性，上游 OMLX 为外部依赖）＋ `std-tailoring.md` `LT-TL-020`（内容评测不在 tests 家族）。**事实**：本方案只断言结构/事件序列/字段契约，不把模型内容当 Oracle（系统设计 §8）；内容评测需独立统计口径与评测集，属模型评测专项。故**不写空 Case**。恢复条件＝定义独立内容 Oracle 与统计口径后另立评测专项。 |
| 容量/耐久（FD 泄漏、30min 耐久、50 并发） | **(b) OUT-OF-SCOPE**（Tailored-N/A；本层不测，非缺口） | Owner：性能/运维。**权威**：设计 [`llmtier-system-design` §11.1](../../20_system_design/llmtier-system-design.md) 明示"V0.3 **不承诺尚未测量的吞吐/延迟 SLO**"，只固定单节点保护预算（并发许可 1、队列 32、等待 30s 等**时序/预算类**断言，已由 `ST-RESP-020`/`ST-EMB-008` 覆盖）；容量/耐久不是系统层组合保证。`std-tailoring.md` `LT-TL-020`（原 ST-18/19/21 容量项转专项）＋`LT-TL-024`（定稿 N/A）。**事实**：harness 是功能性 pytest 黑盒（`tests/system/cases/*`＋`tests/common/harness/runner_system_a.sh / runner_system_b.sh`），无负载驱动/无 FD 采样器/无长稳计时器。故不在本方案分母内。恢复条件：另立性能/运维专项（自有负载工具与计时器）执行，结果不合并进本方案分母。**分类结论：(b)，非 (c)**——设计本身不要求该行为，不是测试漏做。 |
| 进程 crash/restart 后的运维恢复、备份/恢复演练 | **Tailored-N/A（定稿；运维承接；非 Gap）** | Owner：运维。**权威**：`m5air-operations-manual.md` §12（停止/重启 ≤60s）、§14（冷备份/恢复流程）、§15（更新/回滚）；`llmtier-release-and-operations.md` §6/§10（升级/恢复目标 runbook）。**事实**：运维级恢复/备份演练是运维活动（`LT-OPS-003/004/005`），不是 HTTP 运行层行为；本层不做破坏性 DB 构造。**注**：账本在崩溃/重启后的**核心不变量**（orphan unknown 不回填 0，`T-MET-CRASH`）已由 `ST-USAGE-009` 覆盖；`LT-OPS-005` 的 QuerySnapshot TTL 由 `ST-USAGE-004`（过期 cursor）间接覆盖。恢复条件＝真实 systemd/备份密钥/restore rehearsal 交付后由运维专项执行（`LT-OPEN-03` implementation gate）。 |
| `ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`/`ERR-UTIL-TXN` 的 envelope code | Tailored-N/A（下层承接；非 Gap——4 项均有单元宿主） | Owner：M007/M004。**关闭事实（本版代码复核）**：4 项 envelope code 均由 `llmtier-unit-test-scheme` §3 的真实单元用例直接断言（被测模块内部真实、仅隔离临时库，`http_api.errors.ApiError` 的 `status`/`code` 逐一相等）：`bootstrap_required`＝`UT-MGMT-001::test_empty_store_without_settings_is_bootstrap_required`；`bootstrap_invalid`＝`UT-MGMT-001::test_missing_section_fails`/`test_env_secret_ref_unavailable_fails`/`test_file_secret_ref_missing_fails`；`schema_unknown`＝`UT-UTIL-002::test_legacy_store_without_schema_meta_rejected`；`schema_version_mismatch`＝`UT-UTIL-002::test_version_mismatch_rejected`；`schema_integrity_failed`＝`UT-UTIL-004::test_integrity_failure_is_503`；`store_path_unsafe`＝`UT-UTIL-001::test_symlink_path_rejected`；`E-UTIL-NESTED-TXN`＝`UT-UTIL-004::test_nested_transaction_is_409`。**本层不测的理由（事实）**：`/readyz` 503 body 为 `ReadinessView` 而非 `ErrorEnvelope`（无 `code`）；其余需破坏性构造（symlink DB、嵌套事务）从 HTTP 无法无破坏触发。`ERR-BOOT` 的表现层另由 ST-HEALTH-004/05 覆盖。 |
| 非受信来源的真实"缺凭据" 401 | Tailored-N/A（下层承接；非 Gap——单元宿主存在） | Owner：代码 owner（`src/http_api/auth.py`）。**关闭事实**：A/B 受信网段无法构造非受信来源，但 `src/http_api/auth.py::authenticate`/`unauthenticated_principal` 可用合成非受信地址（如 `8.8.8.8`）直接单元验证：`unauthenticated_principal("8.8.8.8", Headers(), role)` 返回 `None`，随后 `authenticate(Headers(), role)` 抛 `ApiError(401, "authentication_required")`——由 `llmtier-unit-test-scheme` §3 `UT-API-008::test_non_trusted_address_without_credential_is_401` 覆盖。系统层 ST-AUTH-010 仍以非法授权方案（`Basic`）触发同一 401 分支。本层无系统级构造，缺口按"单元级已覆盖"关闭。若引入显式 env 门控须重新评审。 |
| `VRC-INF-005`（观测 fail-open / 不二次校验，M003；模块设计 inference §14.5） | **(a) COVERED**（真实单元行为测试） | Owner：M003。**证据**：`tests/unit/cases/UT-DIAG-003.py::InferenceFailOpenTests::test_inference_result_unchanged_when_diagnostic_writes_fail`（drop 全部诊断表后 `result["status"]=="completed"`、`usage.total_tokens==3`）；`::test_usage_ledger_still_measured_when_diagnostic_writes_fail`（`measurement_status=="measured"`）；`::test_upstream_fault_still_surfaces_when_diagnostic_writes_fail`（观测写失败时仍能抛出 `503 provider_unavailable`）。**不二次校验**：`InferenceNoSecondAuthTests::test_inference_path_does_not_call_authenticate`（patch 全部 auth 入口为 `_boom` 仍 `completed`）。系统层 `ST-RESP-011/22/26/27` 另以注入覆盖表现面。 |
| `VRC-UTIL-002`（事务/初始化/拒绝，M007；模块设计 util §14.2、`ERR-PATH-UNSAFE`） | **(a) COVERED**（真实单元行为测试） | Owner：M007。**证据**：`tests/unit/cases/UT-UTIL-001.py::StoreSchemaTests::test_version_mismatch_rejected`、`::test_legacy_store_without_schema_meta_rejected`、`::test_symlink_path_rejected`（`ERR-PATH-UNSAFE`）；`tests/unit/cases/UT-UTIL-003.py::IntegrityMappingTests::test_integrity_failure_is_503`（`schema_integrity_failed`）、`::NestedTransactionTests::test_nested_transaction_is_409`（`E-UTIL-NESTED-TXN`）、`::test_txn_context_reuses_caller_connection`（回滚/复用）。均断言异常 `status`/`code`，非字符串契约。 |
| `VRC-API-001/003/004`（M001 分发/错误、body/SSE、静态与健康；模块设计 http-api §14.1/§14.3/§14.5/§14.6） | **(a) COVERED**（真实单元行为测试，loopback HTTP） | Owner：M001。**证据（VRC-API-001）**：`test_app_dispatch.py::DispatchTests::test_unknown_route_is_404_not_found`、`::test_unhandled_error_is_500_and_logged`、`::test_read_path_store_failure_is_503_usage_store_unavailable`；`test_app_startup.py::test_valid_bootstrap`/`::test_missing_settings_not_ready`。**（VRC-API-003）**：`test_app_dispatch.py::BodyTests::test_body_over_2mb_is_413`、`::test_invalid_json_is_400`、`::test_top_level_non_object_is_400`、`::test_non_integer_content_length_is_400`；`test_sse.py`（首帧 `response.created`、序号单调、terminal 唯一、`[DONE]`）。**（VRC-API-004）**：`test_app_dispatch.py::test_directory_traversal_is_404`、`::test_ui_root_serves_index`、`ReadinessStatusTests`、`BootstrapErrorTests`。 |
| `VRC-MGMT-004/005`（M004 分页与清空、探测；模块设计 management §14.4/§14.5） | **(a) COVERED**（真实单元行为测试） | Owner：M004。**证据（VRC-MGMT-004）**：`tests/unit/cases/UT-MGMT-001.py::AdminCursorExpiryTests::test_expired_admin_cursor_is_400`、`::test_malformed_offset_cursor_is_400_not_500`；`ResetUsageScopeTests::test_reset_by_model_only`/`::test_reset_by_deployment_only`/`::test_reset_by_model_and_deployment`/`::test_reset_all`（范围矩阵）。**（VRC-MGMT-005）**：`ProbeUnreachableTests::test_unreachable_probe_is_unhealthy_persisted`（不可达→`unhealthy` 落库）；`test_health.py::ProbeTests::test_probe_persists`/`::test_probe_unknown_deployment`/`::test_probe_invalid_status`。系统层 `ST-USAGE-*`/`ST-AUSAGE-*`/`ST-PROBE-*` 以表现层 Case 交叉印证。 |
| `VRC-DIAG-003`（M006 libdiag fail-open；模块设计 libdiag §14.3） | **(a) COVERED**（真实单元行为测试） | Owner：M006。**证据**：`tests/unit/cases/UT-DIAG-003.py::FailOpenTests::test_record_trace_failure_is_swallowed`、`::test_record_latency_failure_is_swallowed`、`::test_capture_snapshot_failure_returns_none`、`::test_cleanup_failure_returns_zero`、`::test_failed_write_is_warned_to_operator_log`；`test_app_dispatch.py::UnavailableDiagnosticsTests::test_degrades_to_unavailable_observer`/`::test_inference_still_succeeds_when_diagnostics_unavailable`。均真实调用被测服务并断言不阻断。 |
| `VRC-OBS-001..005`（M005 observability：开关/查询脱敏/注入/关联标识/诊断页；模块设计 observability §14.1–§14.5） | **(a) COVERED（行为级）＋ 视觉子项已由真实浏览器承接** | Owner：M005（视觉子项 Owner：M002 web-ui）。**行为级证据**：`tests/unit/cases/UT-DIAG-001.py::SwitchTests`（开关默认关/运行时切换）、`tests/unit/cases/UT-API-007.py::SnapshotRedactionTests::test_query_secret_is_not_stored_in_snapshot`（`?token=` 不落库）、`::test_trace_stage_url_also_stripped`、`::DiagnosticsAvailabilityTests::test_snapshots_store_failure_is_503_not_empty_page`、`::CorrelationObservabilityTests::test_explicit_correlation_id_is_echoed`/`::test_traceparent_trace_id_is_extracted`；`test_diagnostics_gaps.py::InjectionPriorityTests`。**视觉子项**（诊断页 tabs/Disabled 真实渲染）现由真实浏览器 Case `ST-UI-006`（4 tabs 渲染/切换 + `#snapshots-body`/`#dstats-body` 真实绘制 `Disabled`）与 `ST-UI-002`（tabs 切换 API）承接——原 `RISK-UI-EXEC-1` 已关闭。 |
| `VRC-UI-001..006`（M002 web-ui：加载/编辑鉴权/Pause/用量未知/探测确认/诊断页；模块设计 web-ui §14.1–§14.7） | **(a) COVERED（真实浏览器执行，本版关闭 `RISK-UI-EXEC-1`）** | Owner：M002 web-ui。**关闭证据**：新增真实浏览器系统层 Case `ST-UI-001`（`VRC-UI-001` 页面渲染 + Provider 行来自 API）、`ST-UI-002`（`VRC-UI-001` tab 切换改可见区并触发 API）、`ST-UI-003`（`VRC-UI-003` 确认门控 Pause 发 `If-Match` PATCH 并重渲染）、`ST-UI-004`（`VRC-UI-004` 用量未知渲染 Unknown 不臆造零点）、`ST-UI-005`（`VRC-UI-005` 未确认探测不触网、确认后 POST）、`ST-UI-006`（`VRC-UI-006` 诊断页 4 tabs 与 Disabled 视觉）、`ST-UI-007`（`VRC-UI-002` 注入 API 错误显示错误态并保留上一屏）、`ST-UI-008`（`VRC-UI-001` 脱敏/安全呈现：secret 不落 DOM/URL/日志）、`ST-UI-009`（`VRC-UI-005` 幂等/防重：探测连点只发一次）、`ST-UI-010`（`VRC-UI-001` 边界呈现：极值文本不溢出/不注入）。实现＝`tests/system/cases/ST-UI-001.py` + `tests/common/drivers/browser_driver.mjs`（headless Chrome over CDP，hermetic 临时实例 + LAN fake provider）；运行＝`PYTHONPATH=src python3 -m pytest tests/system/cases -m ui -q`；证据＝每 Case PNG 截图 + 网络日志。`UT-UI-001..010` 的源码字符串契约保留为快速下位防线，**不再单独承担行为验证**。 |
| **`RISK-UI-EXEC-1`（原开放 RISK —— 本版已关闭）** | **Closed — 已引入真实浏览器执行；风险消解** | **Owner：M002 web-ui（视觉子项共同 Owner：M005）。** **关闭事实**：引入真实浏览器 harness（headless Chrome over CDP，`tests/common/drivers/browser_driver.mjs`），新增系统层 Case `ST-UI-001..010` 在真实 DOM 与真实网络（CDP `Network.*`）上执行 UI 行为，`VRC-UI-001..006` 与 `VRC-OBS-*` 诊断页视觉子项**已由真实执行验证**；行为回归（分支顺序错误、DOM 未渲染、事件未绑定）现可被 `-m ui` 用例发现。**关闭条件达成**：原条件＝"引入浏览器/JS 宿主 → 将 `UT-UI-*` 升级为真实执行断言"——已由浏览器执行替代（保留字符串契约为下位防线）。**重评触发**：新增/修改任一 UI 行为分支时，须同步 `ST-UI-*`。 |
| ~~`POST /v1/responses` 声明的 `422`（OpenAPI）~~ **已关闭（无偏差）** | **Closed — 无偏差，无需 Case** | Owner：M001 http-api/规格。**结案事实**：复核 `interfaces/openapi/llmtier.openapi.json` `/v1/responses` 的 responses 恰为 `200/400/401/404/429/502/503`，**不含 422**；`grep -rn "422" src/` 零命中、`grep -rn "422" docs/20_system_design` 零命中。实现与设计一致使用 `400 invalid_json`（`app.py:161-162` `_body()`；系统设计 §7.8 `ERR-REQ-JSON`），已由 `ST-RESP-016` 覆盖、schema 级违例由 `ST-RESP-008/12..15` 覆盖。原条目所称"OpenAPI 声明的 422"为过时陈述：OpenAPI 从未声明 422。**无偏差可消**，条目关闭。 |
| ~~`POST /v1/probes` 声明的 `502`（OpenAPI）~~ **已关闭（改声明对齐实现）** | **Closed — 按观测语义改契约声明** | Owner：M004 管理/M003 推理/规格。**裁决**：探测是**观测**，上游不可达/失败是观测结果而非接口错误——`OpenAIProvider.probe` 对**所有**上游异常 `except Exception: return False`（`providers/openai.py:144-145`），`AdminService.probe` 据此返回 `200 ProbeResult{status:"unhealthy"}` 并落库 health（`admin.py:119-122`）；模块设计 M004 §4.2「探测失败 → `unhealthy`」、health 枚举「`unhealthy`：探测失败」为设计意图权威，单元测试 `test_management_gaps.py::test_unreachable_probe_is_unhealthy_persisted` 锁定该行为。故**改声明对齐实现**：已从 OpenAPI `/v1/probes` 删除 `502 ProviderFailure`（并入 `404 NotFound`）；系统设计 §8、`llmtier-api-reference.md` §3.2 同步为"无 502"；`http-api-design.md`、机制 `inference-stream.md` §5 原即无 502。`ST-PROBE-002/03` 已覆盖 200/404 表现。**偏差消除，条目关闭**。 |
| ~~Embeddings 的 `provider_failure`（`fault_502` 注入码）~~ **已关闭（不可达声明已移除）** | **Closed — 对齐已实现契约** | Owner：M003 推理/规格。**裁决**：`provider_failure` 仅在 `ResponsesService.create` 的注入分支产生（`responses.py:110`）；`EmbeddingsService.create` **不读** `enabled_injection`，无故障注入路径，该码在 Embeddings 不可达。设计不要求 Embeddings 注入（系统 §7.8 承接索引 `ERR-PROVIDER-INJECTED` 仅登记 `/v1/responses`；机制 `observability.md` 注入仅作用于推理流）。故移除"Embeddings `provider_failure`"声明，确认 Embeddings 错误码恰为可达集：`400`（`invalid_request`/`unsupported_model`/`unsupported_dimensions`/`invalid_json`/`request_too_large`）、`404 model_not_found`、`429 rate_limit_exceeded`、`502 provider_contract_error`、`503 provider_unavailable`/`provider_secret_unavailable`/`usage_store_unavailable`；OpenAPI `/v1/embeddings` 与系统 §7.8 一致。`ST-EMB-009`（502 契约错误）/`ST-EMB-010`（503 不可用）已覆盖可达集。**偏差消除，条目关闭**；若未来为 Embeddings 增加注入支持须重评。 |

> **三项具名缺口结案（本版审计复核，含设计意图核对）**：任务要求"读设计意图再判断是否 code 缺行为"，本版逐项按 **code + OpenAPI + 设计意图** 三方核对，结论 **全部为 (b) 声明对齐 / 无偏差，无 code 缺陷**：
> - **项 1 `POST /v1/responses` `422`**：`interfaces/openapi/llmtier.openapi.json` 该 operation responses 恰为 `200/400/401/404/429/502/503`（**无 422**，程序化核验通过）；`src/` 与 `docs/20_system_design` 无 `422`；设计意图＝`400 invalid_json`（§7.8 `ERR-REQ-JSON`）。**无偏差**，`ST-RESP-016` 覆盖。
> - **项 2 `POST /v1/probes` `502`**：设计意图权威＝`management-design.md` §4.2/§14.5「探测失败 → `unhealthy`」＋`health.py apply_probe_result` 四值枚举；代码对**所有**上游异常 `probe()→False`（`providers/openai.py:144-145`）并返回 `200 {status:"unhealthy"}`、落库（`admin.py:119-122`）。**设计本就不要求 502**——探测是观测而非接口错误，故"502 声明"为过时文档，已改 OpenAPI 对齐实现。`ST-PROBE-002/03` + `UT-MGMT-010::test_unreachable_probe_is_unhealthy_persisted` 覆盖。**code 正确，无缺陷**。
> - **项 3 Embeddings `provider_failure`**：设计意图权威＝§7.8 承接索引 `ERR-PROVIDER-INJECTED | /v1/responses`（**仅 responses**）；代码 `EmbeddingsService.create` **不读** `enabled_injection`（`embeddings.py`；`provider_failure` 仅在 `responses.py:112` 产生）。**设计不要求 Embeddings 注入**，故"provider_failure"声明为不可达，已移除对齐。`ST-EMB-009`（502 `provider_contract_error`）/`ST-EMB-010`（503）覆盖可达集。**code 正确，无缺陷**。
>
> 三项均**不触发 code 修改**；均从 Gap 清单关闭，非重新登记。**未以"只改文档"掩盖任何设计-代码错配**——每项先核对设计意图，确认设计本就如此。

### 需求缺口裁决（`LT-*`，对照 §3.6）

`LT-*` 需求共 **35 项**；§3.6 家族级重建后 **26 项有 Case 家族承接**，下列 **9 项**无本运行层 Case，按事实逐项**定稿裁决**（**全部 Tailored-N/A，非 Gap**）：4 项为 absence/声明性静态契约（由 `CT-*` 与单元契约测试承接），4 项为运维/生产部署活动、1 项为实现 Gate，均不在 tests 家族分母（权威：`std-tailoring.md` `LT-TL-020`/`LT-TL-022`）。**本表无具名 Gap**。

| 需求 `LT-*` / 事实依据 | 裁决（Tailored-N/A） | Owner / 权威与恢复条件 |
|---|---|---|
| `LT-FUN-007`（不保存/压缩 Agent 历史、不执行工具、不创建 Session/Conversation、不管理 backend KV） | Tailored-N/A（范围外：absence 静态契约） | Owner：LLMTier。**非 HTTP 运行层可测**——属"不存在"断言，由静态契约 `CT-BOUNDARY-001` 与 `tests/system/st_04_forbidden_scan.py` 承接（`x-llmtier-architecture-boundary` 全 false、OpenAPI/manifest 无 forbidden path/header），并由契约测试 `tests/contract/test_contract_semantics_v03.py::test_stateless_boundary_and_minimal_extension_are_explicit`（`x-llmtier-architecture-boundary` 全 false）与 `::test_no_removed_public_schema_or_header` 加强（范围与非目标见退役规格 §11.2；当前运行层只测 current `/v1/*`）。 |
| `LT-INT-003`（不定义 SourceInstance/Idempotency-Key/Invocation/recovery/Seat/Cost/compatibility） | Tailored-N/A（范围外：absence 静态契约） | Owner：LLMTier。由静态契约 `CT-SCOPE-001`/`CT-BOUNDARY-001` 与 `st_04_forbidden_scan.py` 承接（forbidden path 扫描）；契约测试 `test_contract_semantics_v03.py::test_no_removed_public_schema_or_header`（无 `SourceInstance`/`Idempotency-Key`/`InvocationView`/`CapacitySnapshot`/`CostEvidence`/`RecoveryItem`）与 `::test_cost_is_not_in_current_contract`、`::test_current_consumer_paths_are_minimal`（无 `/v1/invocations`/`/v1/capacity/*`/`/v1/compatibility`/`/v1/recovery-items`/`/v1/clients`/`/v1/sources`）为真实承接，非运行层分母。 |
| `LT-REL-002`（内部可靠性/retry/防重不得创建对外 Invocation/recovery/session contract） | Tailored-N/A（范围外：absence 静态契约） | Owner：LLMTier。同 `LT-INT-003`（`CT-SCOPE-001`）：absence 由 `st_04_forbidden_scan.py` ＋ `test_contract_semantics_v03.py::test_no_removed_public_schema_or_header` 承接；`test_cost_is_not_in_current_contract` 断言 `usage_policy.cost_supported=false`。 |
| `LT-PERF-003`（未测量前不得宣称 production latency/throughput/availability SLO） | Tailored-N/A（范围外：声明性约束） | Owner：LLMTier。属发布声明约束，非运行行为。**权威**：`llmtier-requirements.md` §6 注（容量/Seat 等为内部实现或历史候选，非外部契约）＋ `llmtier-release-and-operations.md` §7（"当前没有 production latency/throughput/error budget 或 provider measured SLO；这些是安全上限而非 SLO"）。恢复条件＝SLO 专项测量后另立。 |
| `LT-SEC-003`（production Web UI 同源 TLS 反代 SSO/MFA、HttpOnly/CSRF、浏览器无 bearer、不加账号/登录 API） | **Tailored-N/A（定稿；非 Gap；不在 tests 家族）** | Owner：运维/安全。**权威**：`std-tailoring.md` `LT-TL-022`（验收/生产部署活动 deferred，不在 tests 家族）＋ `llmtier-release-and-operations.md` §10/§11（反向代理终止 TLS、runbook、activation BLOCKED）。**事实**：本方案为 LAN HTTP 黑盒，无 TLS/SSO 终止端；浏览器无 bearer 由 UI 契约 `UT-UI-001::test_no_bearer_storage`（`test_webui_contract.py` 断言 `app.js` 无 `localStorage`/`Bearer `）在单元层以静态契约承接，Web UI 行为级见 `VRC-UI-001..006` 裁决。不加账号/登录 API 由 `LT-INT-003` 的 absence 静态契约承接。恢复条件＝生产部署面可用且激活决策启动后由验收活动补测。 |
| `LT-OPS-003`（restart/reload/restore 使用自有 runbook，不建跨系统恢复状态机） | **Tailored-N/A（定稿；运维承接；非 Gap）** | Owner：运维。**权威**：`m5air-operations-manual.md` §12（停止/重启）、§14（备份/恢复）、§15（更新/回滚）；`llmtier-release-and-operations.md` §10（单节点启动/重启/恢复 Runbook）。**事实**：runbook 是运维 prose 活动，非 HTTP 运行层行为；本方案不建跨系统恢复状态机（`LT-REL-002` absence）。恢复条件＝runbook 执行记录落地（随 `LT-OPEN-03` 实现 Gate）。 |
| `LT-OPS-004`（恢复确认分层检查 process/config/model availability/Usage store，仅授权后 smoke） | **Tailored-N/A（定稿；运维承接；非 Gap）** | Owner：运维。**权威**：`llmtier-release-and-operations.md` §10 步骤 5–6（停止→保全→恢复备份→离线 integrity→只读启动→Registry/Usage/Audit 抽样→受授权 smoke）；`m5air-operations-manual.md` §8（启动验证）、§14.2（恢复后检查 Registry/Usage/Audit）。**事实**：分层恢复检查与授权 smoke 是运维流程；无副作用 health/readiness 读取由本层 `ST-HEALTH-*` 运行层承接，真实 provider smoke 需 operator 授权（`LT-FUN-006`）。恢复条件＝运维分层恢复检查执行记录落地。 |
| `LT-OPS-005`（单节点 systemd 基线、优雅摘流 ≤60s、QuerySnapshot TTL 15min、Usage/Audit 保留 30/90 天、加密备份 7日+4周、RPO 24h/RTO 4h、release 前隔离 restore 演练） | **Tailored-N/A（定稿；运维承接；非 Gap；TTL 已间接触及）** | Owner：运维。**权威**：`llmtier-release-and-operations.md` §9（retention TTL、加密备份 7日+4周、RPO 24h/RTO 4h、release 前隔离 restore）、§10（systemd、摘流 ≤60s）；`m5air-operations-manual.md` §12/§14。**事实**：systemd/保留策略/加密备份/restore rehearsal 属运维专项，本层无对应 harness；QuerySnapshot TTL 由本层 `ST-USAGE-004`（过期 cursor→400）间接验证；Usage/Audit 保留期由 `UT-MGMT-009`（`reset_usage` 范围）与 `UT-LOG-002`（`page` 边界）在单元层部分承接。恢复条件＝真实 systemd/备份密钥/restore rehearsal 交付后由运维专项执行（`LT-OPEN-03`）。 |
| `LT-OPEN-03`（单节点 Linux + TLS 反代 + systemd + 加密备份 + runbook；design closed / implementation gate） | **Tailored-N/A（定稿；实现 Gate，非测试缺口）** | Owner：LLMTier。**权威**：`llmtier-requirements.md` §11（`LT-OPEN-03` 设计已关闭、待实施证据）＋ `llmtier-system-design` §16（`LT-OPEN-03` design closed / implementation gate）＋ `llmtier-release-and-operations.md` §10（"真实 systemd unit、代理/SSO 配置、备份密钥和 restore rehearsal 尚未交付，因此 activation 仍 BLOCKED"）。**事实**：这是**实现/部署 Gate**，不是测试设计缺口——设计已关闭，缺的是部署证据（真实单节点 Linux 基线 + TLS/systemd/加密备份）。本方案（测试方案）不承载部署证据；恢复条件＝runtime activation 前完成部署证据。 |

## 5. 文档联动与清单变更规则

<span style="color:#1f6feb"><em>**本节目的**：固定方案—用例—计划的联动规则，防三处漂移。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：新 Case 先入本清单再建 case-design 文档（文档 ID＝Case ID）；清单变更须同步计划构成表；写明方案冻结/版本规则。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：清单与 case-design 文档一一对应；计划只引用不复制。</em></span>

- **方案冻结与变更规则**：Case 清单随系统设计基线**冻结**；系统设计或机制变更导致分母变化时，本方案升版并同步 `tests.system-test-plan` 的构成表。Case ID 一经登记**不复用、不改名**；新增 Case 取同家族下一个未占用序号（含补丁后缀，如 `ST-SL-012`）；废弃 Case 标 `superseded`，不删除、不重编号。
- **与 case-design / 计划的同步规则**：**新 Case 先入本清单 §3，再建 case-design 文档**；case-design 文档路径固定为 `docs/70_verification/system/cases/<lowercased-case-id>.md`（例：`ST-RESP-001` → `cases/st-resp-001.md`），文档 ID = Case ID；`tests.system-test-plan` 只引用本方案版本，不复制 Case 清单。本方案只登记 Case **设计状态**（Designed/Gap/Tailored-N/A），不承载实现状态（在 case-design 文档）与执行状态/Verdict（只在 Run 报告）。
- **case 文档的测试方法声明（强制契约条款）**：每份 `tests.system-case` 文档 §1 **必须**含一条 `- **测试方法（§1.5 方法表行）**：<technique(s)>` 列表项（**不新增章节**），指名本方案 §1.5 家族表/UI 方法表的**确切技术行**；技术须由该 Case 的**实际分类 + 步骤/断言**推导，跨两类时并列，**禁止**按分类照抄而不读步骤。该条款与 `system/cases/README.md`「模板契约」一致；缺失或不诚实声明即视为 Case 不完备。
- **本方案的退役与吸收映射**：本方案**唯一吸收并取代**旧 `assurance.test-specification` 家族的 `llmtier-api-test-specification`（140-Case 权威清单、定量覆盖模型、Traceability、环境与共同机制）与 `llmtier-contract-test-specification`（静态契约 `CT-*` 的 runtime 落地边界）。二者已从 `docs/70_verification/specifications/` 退役（git rm）；其原 Case ID 与数量（140）作为基线**保持不变**（不重命名、不重编号），逐 Case 细节现由 `tests.system-case` 文档承载；本版在该基线上按覆盖洞评审（`coverage_review`）**新增 23 个 Case**（`ST-EMB-008..10`、`ST-PROV-015..`、`ST-OBS*-003..`、`ST-USAGE-009`、`ST-RESP-026/27` 等，见 §3），清单总数 140 → **163**。
- **需求到本方案的可追溯入口**：本方案各 Case 家族的追溯链 `LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case **已重建并落于 §3.6**（由退役 `llmtier-api-test-specification` §3.6 与需求文档重建；不再依赖已退役 source）。需求缺口（9 项 `LT-*`）见 §4「需求缺口裁决」；逐 Case 的 Run 侧追迹另由 case 文档与 Run manifest 的 `target_artifact` 锁定。

### 未决项与歧义记录（本方案自记录）

> 以下为实施本方案时发现的 STD 读数歧义；本方案按"采取 STD 读数并显式登记"处理，未静默猜测。列出以提请 STD 维护者裁决。

1. **（已关闭）Case ID 命名语法**：原模板 §3 示例使用 `SYS-<对象>-<NNN>` 语法，与 LLMTier 既有 Case ID 前缀（`ST-HEALTH-*`/`DP-*`/`ADM-*`/`OBS-*`/`ST-AUTH-*`/`ST-UI-*`）不一致。**关闭事实**：STD `78876c9` 在 `docs/software-object-identifiers.md` §2 正式codify Case ID 格式为 **`<阶段前缀>-<对象>-<NNN>`**（系统测试 `ST`；`<对象>`＝被测对象 token；`<NNN>` 三位十进制）。本方案**已按新规范完成迁移**：全部系统层 Case ID 由旧族名重命名为 `ST-<对象>-<NNN>`（对象 token 映射见 §3 及各 case 文档），Stage 前缀为 `ST`（不再是 `SYS`）。旧 ID→新 ID 映射记录于 `docs/98_migration/llmtier-case-id-migration.md`（迁移记录，非现行引用）。
2. **"未决项章节"**：任务要求"在方案的未决项章节记录歧义"，但 `tests.system-test-scheme` 模板**没有**未决项章节（正文仅 §1–§5，另有附录 A）。**采取读数**：遵守"匹配模板精确章节集、不得自创章节"，将未决项作为 §5 内的具名小节记录，而非新增顶层章节。
3. **`来源 ID` 粒度**：模板要求"一个来源 ID 至少一条记录"。原规格以 route×method×role×error-code 为覆盖分母，未给"来源 ID"独立编号。**采取读数**：按系统设计 §8 接口/机制分组作为来源 ID（如"系统设计 §8 Responses 接口"），一个来源对应多条 Case；不新造记录编号。
4. **`design_level` 取值**：`new-design` 对 `tests.system-test-scheme` 未在层级映射中登记，生成默认 `cross-level`；STD 指南称系统方案"对应 design.software-system（系统设计阶段）"。**采取读数**：metadata 置 `design_level=system`、`domain=[software]`（与系统层语义一致）；`validate-design` 不对此强制，故为语义读数而非工具强制。
5. **（已关闭）逐 Case 设计文档的入站链接（跨任务移交）**：原记录为"140 份 `tests.system-case` 文档仍指向已退役的 `../llmtier-api-test-specification.md`，重写前 `validate-design docs` 会报告 `link.missing`"。**关闭事实**：并行工作项已完成 case 文档重写——当时全部 141 份 case 文档（140 Case + README）**均不再**引用任何退役规格（0 处），且全部以真实路径引用本方案（`llmtier-system-test-scheme.md`）；`validate-design docs` 不再报告该类 `link.missing`。本条歧义已消解，保留以存档（其后按覆盖洞新增的 23 份 case 文档同样不引用退役规格）。

## 附录 A. 本层设计验证项 VRC 汇集（对照用）

<span style="color:#1f6feb"><em>**本节目的**：把设计文档声明的本层验证项 VRC 汇集于此，供逐项对照 §3 清单的覆盖。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：VRC 清单以设计文档（design §12/§14）为唯一权威，本附录只登记 ID 与要验证什么，不复制判据/Oracle 定义；设计变更时本附录同步；每个 VRC 必须在 §3 清单有至少一个 Case，否则登记缺口。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：本附录 VRC 集合与设计文档一致；每个 VRC 在 §3 清单有 Case 或缺口。</em></span>

**本层 VRC 集合（33 项）**：`VRC-API-001`、`VRC-API-002`、`VRC-API-003`、`VRC-API-004`、`VRC-INF-001`、`VRC-INF-002`、`VRC-INF-003`、`VRC-INF-004`、`VRC-INF-005`、`VRC-MGMT-001`、`VRC-MGMT-002`、`VRC-MGMT-003`、`VRC-MGMT-004`、`VRC-MGMT-005`、`VRC-MGMT-006`、`VRC-DIAG-001`、`VRC-DIAG-002`、`VRC-DIAG-003`、`VRC-DIAG-004`、`VRC-LOG-001`、`VRC-OBS-001..005`、`VRC-UI-001..006`、`VRC-UTIL-001`、`VRC-UTIL-002`。来源＝各 Case `tests.system-case` 文档所声明者（`ST-RESP-016`/`ST-RESP-023` 按系统设计 §7.8 错误目录反查补全）。

| 设计验证项 ID | 要验证什么（名称/责任） | 设计来源 | §3 Case 覆盖 |
|---|---|---|---|
| `VRC-API-002` | HTTP 入口/鉴权/序列化与健康表现 | 系统设计 §12 | ST-HEALTH-001..06、ST-AUTH-001..10、ST-RUNTIME-002/03、ST-OBSREQTRACE-003 |
| `VRC-MGMT-003` | 就绪/审计/未配置鉴权语义 | 系统设计 §12 | ST-HEALTH-002..05、ST-AUDIT-001/03/04、ST-AUTH-007 |
| `VRC-MGMT-006` | 用量/统计/分页口径 | 系统设计 §12 | ST-USAGE-001..09、ST-PUSAGE-*、ST-STATS-001..04、ST-AUSAGE-*、ST-AUDIT-002 |
| `VRC-MGMT-001` | Provider/Deployment 管理语义 | 系统设计 §12 | ST-PROV-001..15/17、ST-PMOD-001/02、ST-DEPL-001/03/05/06/07/08/10/12 |
| `VRC-MGMT-002` | 更新/并发/ETag 与 Service Level 语义 | 系统设计 §12 | ST-PROV-005..07/09/13/16、ST-DEPL-004/09/11、ST-SL-001..11 |
| `VRC-INF-001` | 推理/模型/嵌入路由与请求契约 | 系统设计 §12 | ST-MODEL-001..07、ST-RESP-001..25、ST-EMB-001..09 |
| `VRC-INF-002` | 推理输出/能力集结构契约 | 系统设计 §12 | ST-MODEL-001/07、ST-EMB-003/05 |
| `VRC-INF-003` | 上游非 5xx → provider_error | 系统设计 §12 | ST-RESP-023 |
| `VRC-INF-004` | 准入饱和/候选健康/运行时快照 | 系统设计 §12 | ST-RESP-019/20、ST-EMB-008/10、ST-USAGE-009、ST-RUNTIME-001 |
| `VRC-DIAG-001` | 诊断开关读写 | 系统设计 §12 | ST-OBSDIAG-001..03、ST-OBSALIAS-001 |
| `VRC-DIAG-002` | 诊断快照/统计/trace/请求追踪 | 系统设计 §12 | ST-OBSSNAP-001..03、ST-OBSSTATS-001..03、ST-OBSTRACE-001..03、ST-OBSREQTRACE-001/02、ST-OBSALIAS-002..06 |
| `VRC-DIAG-004` | 故障注入配置与探测 | 系统设计 §12 | ST-RESP-011/22/26/27、ST-PUSAGE-002/03、ST-PROBE-001..03、ST-OBSDEPL-001..05、ST-OBSALIAS-004 |
| `VRC-LOG-001` | 日志/审计脱敏 | 系统设计 §12 | ST-LOGS-001..03 |
| `VRC-UTIL-001` | 存储引导/就绪引导表现 | 系统设计 §12 | ST-HEALTH-004/05 |
| `VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`（行为级） | 模块级验证项（无系统层 Case；**行为级由单元层真实行为测试覆盖**） | 模块设计 §14、ISD §9.1 | §4 裁决：**(a) COVERED**——逐项列为真实 `test_*`（见 §4 表），非字符串契约 |
| `VRC-UI-001` | M002 web-ui 加载与状态 | 模块设计 web-ui §14.1、ISD §9.1.1 | ST-UI-001、ST-UI-002、ST-UI-008、ST-UI-010 |
| `VRC-UI-002` | M002 web-ui 编辑/鉴权 | 模块设计 web-ui §14.2、ISD §9.1.2 | ST-UI-007 |
| `VRC-UI-003` | M002 web-ui Pause 边界 | 模块设计 web-ui §14.3、ISD §9.1.3 | ST-UI-003 |
| `VRC-UI-004` | M002 web-ui 用量未知不填零 | 模块设计 web-ui §14.5、ISD §9.1.4 | ST-UI-004 |
| `VRC-UI-005` | M002 web-ui 探测付费确认 | 模块设计 web-ui §14.4、ISD §9.1.5 | ST-UI-005、ST-UI-009 |
| `VRC-UI-006` | M002 web-ui 诊断页 | 模块设计 web-ui §14.7、ISD §9.1.6 | ST-UI-006 |
| `VRC-OBS-*` 纯视觉子项 | M005 诊断页 tabs/Disabled 真实渲染 | 模块设计 observability §14、ISD §9.1 | §4 裁决：**(a) COVERED**——由真实浏览器 `ST-UI-006`（4 tabs/Disabled 真实绘制）与 `ST-UI-002` 承接；原 `RISK-UI-EXEC-1` 已关闭 |



<!-- 交付自查：每个适用来源 ID 是否都有 Case 或具名缺口；清单里的每个 Case ID 是否都有（或计划有）对应 case-design 文档；方案里是否混入了输入构造或 Oracle 细节？ -->
