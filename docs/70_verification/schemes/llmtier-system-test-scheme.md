<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Scheme

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-scheme` |
| Document Version | `0.1.0-draft.10` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-test-scheme` |
| Template Version | `0.6.1` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/schemes/llmtier-system-test-scheme.md` |
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
| concurrency | 适用 | 7 个 Case：准入饱和 429+`Retry-After`（`DP-RESP-20`、`DP-EMB-08`）、`If-Match`/412 串行化并发编辑、注入变更与在途流（`ADM-PROV-05/06/07`、`ADM-DEPL-04`、`ADM-SL-04`）。 |
| recovery | 适用 | 26 个 Case：故障注入（`fault_502`/`fault_503`/`stream_terminate`/`malformed_event`）、上游/存储失败、客户端断开、账本崩溃/重启恢复（`DP-USAGE-09`）、`/readyz` degraded/not_ready、schema 引导不可用。 |
| security | 适用 | 16 个 Case：认证/授权/角色隔离、LAN trust、无鉴权配置、secret 不泄露、审计与日志脱敏、别名命名空间鉴权。 |
| performance | 裁剪 | 纯软件、无 FPGA/硬件时序；本阶段只保留**时序/预算类可观察断言**（准入队列上限、超时路径、`Retry-After`），**不发布 SLO/容量结论**。功耗/容量压测（FD 泄漏、30min 耐久、50 并发）不在本方案分母内；原 `llmtier-test-plan`（已退役）的 ST-18/19/21 容量项现按 §4 Tailored-N/A（非缺口）由运维/性能专项承接（tailoring）。 |
| endurance | 裁剪 | 长稳/耐久另立专项，不在本方案分母内（tailoring）；见 §4 容量/耐久裁决（Tailored-N/A）。 |

> 上表与 §3 清单交叉核对：normal 50 + boundary 7 + negative 57 + concurrency 7 + recovery 26 + security 16 = **163**。未列入的任何 STD 家族分类在本阶段**不适用**（见 §4 裁决）。



## 3. 覆盖分母与 Case 清单

<span style="color:#1f6feb"><em>**本节目的**：把 design.software-system 的适用来源 ID 转成 Case 清单——测试分母的唯一登记。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：一个来源 ID 至少一条记录（可多 Case 分担，分别写责任摘要）；以设计文档（design §12/§14）的验证项 VRC 清单为分母逐项对账：每个 VRC 至少一个 Case——验证项是设计声明的必测点，本清单只引用其 ID 不复制定义、不做附录；Case ID 稳定且唯一（SYS-<对象>-<NNN>）；责任摘要只写“要测什么、边界在哪”，不写输入与 Oracle；设计状态按状态语义；未实现与 NOT_RUN 不删；不适用转 §4。</em></span>

> 来源 ID 与设计验证项（VRC）的边界：本表登记 ID+责任摘要；判据/Oracle/Owner/契约权威归 design 与 tests.asset-design，不在此行复写；变更设计时同步 VRC 同步本清单。
<span style="color:#1f6feb"><em>**抽象示例**：见下表灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每个适用来源 ID 有 Case 或缺口；每个设计验证项（VRC）至少一个 Case 或在 §4 登记缺口；每个 Case ID 可追到（或计划有）case-design 文档。</em></span>

| 来源 ID / 固定版本 | 设计验证项 ID | Case ID | 分类（STD 家族） | 优先级 | 责任摘要（要测什么） | 设计状态 | 上级组合验证入口 |
|---|---|---|---|---|---|---|---|
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-API-002 | HEALTH-01 | normal | P0 | healthz 始终存活 | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003 | HEALTH-02 | normal | P0 | readyz 就绪=全部 tier 可用 | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003 | HEALTH-03 | recovery | P1 | readyz degraded | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003、VRC-UTIL-001 | HEALTH-04 | recovery | P0 | readyz not_ready（无 deployment） | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-MGMT-003、VRC-UTIL-001 | HEALTH-05 | recovery | P1 | readyz bootstrap 失败 | 已设计 | — |
| 系统设计 §8 健康/就绪接口（/healthz、/readyz） | VRC-API-002、VRC-MGMT-003 | HEALTH-06 | normal | P1 | 健康端点无需鉴权 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-002 | DP-MODELS-01 | normal | P0 | 列出全部可见 tier | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | DP-MODELS-02 | normal | P0 | 精确返回模型 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | DP-MODELS-03 | negative | P0 | 大小写敏感（小写） | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | DP-MODELS-04 | negative | P1 | 大小写敏感（全大写） | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | DP-MODELS-05 | negative | P1 | URL 编码尾空格不匹配 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-001 | DP-MODELS-06 | negative | P0 | 不存在模型 | 已设计 | — |
| 系统设计 §8 逻辑模型清单接口（/v1/models） | VRC-INF-002 | DP-MODELS-07 | boundary | P1 | capabilities 固定 12 键 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-01 | normal | P0 | 流式成功 + 事件序列 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-02 | negative | P0 | stream=false 被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-03 | normal | P1 | 推理输出结构（不含内容 oracle） | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-04 | normal | P1 | tools 透传 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-05 | negative | P0 | unknown model 路由失败 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-06 | normal | P0 | stream=true 唯一受理形态 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-07 | negative | P0 | store=true 被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-08 | negative | P0 | 缺 model | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-09 | negative | P0 | 禁字段 previous_response_id | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-10 | boundary | P1 | max_output_tokens 截断 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | DP-RESP-11 | recovery | P0 | 注入上游 502 → provider_failure | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-12 | negative | P2 | conversation_id 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-13 | negative | P2 | truncation 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-14 | negative | P2 | max_tokens 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-15 | negative | P2 | temperature 接受 / top_p 未知字段被拒 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-16 | recovery | P1 | 非法 JSON body | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-17 | recovery | P1 | embedding-only 等级发 Responses | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-18 | recovery | P2 | body 超 2 MB | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-004 | DP-RESP-19 | recovery | P1 | 全部候选不健康 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-004 | DP-RESP-20 | concurrency | P1 | 准入饱和 → 429 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-21 | recovery | P1 | 客户端中途断开 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | DP-RESP-22 | recovery | P1 | 注入上游 503 → provider_unavailable | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-003 | DP-RESP-23 | recovery | P1 | 上游非 5xx → provider_error | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-24 | recovery | P1 | provider 凭据缺失 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-INF-001 | DP-RESP-25 | recovery | P1 | 上游契约错误 | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | DP-RESP-26 | recovery | P1 | 流截断注入 stream_terminate | 已设计 | — |
| 系统设计 §8 Responses 接口（POST /v1/responses） | VRC-DIAG-004 | DP-RESP-27 | recovery | P1 | 畸形事件注入 malformed_event | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001、VRC-INF-002 | DP-EMB-01 | normal | P0 | 基本 embedding | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-02 | normal | P0 | base64 编码 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-002 | DP-EMB-03 | normal | P1 | 不变量（同输入 ×5） | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-04 | negative | P0 | unknown model | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-002 | DP-EMB-05 | boundary | P2 | batch 33 不强制上限 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-06 | negative | P1 | dimensions 与冻结空间不符 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-07 | negative | P2 | 非法 encoding_format | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-004 | DP-EMB-08 | concurrency | P1 | embeddings 准入饱和 429 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-09 | recovery | P1 | embeddings 上游契约错误 502 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-004 | DP-EMB-10 | recovery | P1 | embeddings 上游不可用 503 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-01 | normal | P0 | 时间窗查询 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-02 | normal | P1 | 请求后可见记录 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-03 | boundary | P1 | cursor 分页 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-04 | negative | P2 | 过期 cursor | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-05 | negative | P1 | 缺 from/to | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-06 | normal | P1 | 主体隔离：data 只见自身，admin 见全局 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-07 | boundary | P1 | 分页重放幂等 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-08 | recovery | P1 | store 不可用不返回空页 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage）；机制 §15 计量（T-MET-CRASH） | VRC-INF-004、VRC-MGMT-006 | DP-USAGE-09 | recovery | P0 | 账本崩溃/重启恢复（orphan unknown 不回填 0） | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-01 | normal | P0 | 列出 providers | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-02 | normal | P0 | 创建 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-03 | normal | P0 | 获取 provider 详情 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-04 | negative | P0 | 不存在 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ADM-PROV-05 | concurrency | P0 | 更新 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ADM-PROV-06 | concurrency | P0 | 更新缺 If-Match | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ADM-PROV-07 | concurrency | P1 | 过期 ETag | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-08 | normal | P0 | 删除 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ADM-PROV-09 | negative | P1 | 删除缺 If-Match | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-10 | negative | P1 | 删除被引用 provider | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-11 | negative | P1 | kind 枚举校验 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-12 | normal | P2 | secret_ref 格式 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ADM-PROV-13 | normal | P2 | usage 子对象更新 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-14 | security | P0 | provider 不泄露 secret | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-15 | negative | P1 | 创建 provider data token 403 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-002 | ADM-PROV-16 | negative | P1 | 更新 provider data token 403 | 已设计 | — |
| 系统设计 §8 Provider CRUD 接口（/v1/providers） | VRC-MGMT-001 | ADM-PROV-17 | negative | P1 | 删除 provider data token 403 | 已设计 | — |
| 系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models） | VRC-MGMT-001 | ADM-PROV-MODELS-01 | normal | P1 | provider 上游模型目录 | 已设计 | — |
| 系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models） | VRC-MGMT-001 | ADM-PROV-MODELS-02 | negative | P1 | 不存在 provider | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006 | ADM-PROV-USAGE-01 | normal | P1 | 读取 provider usage 快照 | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006、VRC-DIAG-004 | ADM-PROV-USAGE-02 | negative | P1 | 刷新缺确认 | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006、VRC-DIAG-004 | ADM-PROV-USAGE-03 | normal | P1 | 刷新带确认 | 已设计 | — |
| 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） | VRC-MGMT-006 | ADM-PROV-USAGE-04 | negative | P1 | usage 未知 provider | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-01 | normal | P0 | 列出 deployments | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-02 | normal | P0 | 创建 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-03 | normal | P0 | 获取 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-002 | ADM-DEPL-04 | concurrency | P1 | 更新 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-05 | normal | P0 | 删除 deployment | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-06 | negative | P1 | capabilities 缺字段 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-07 | negative | P1 | capabilities 未知字段 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-08 | negative | P1 | 引用不存在 provider | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-002 | ADM-DEPL-09 | negative | P1 | provider_id 不可 PATCH | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-10 | negative | P1 | 创建 deployment data token 403 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-002 | ADM-DEPL-11 | negative | P1 | 更新 deployment data token 403 | 已设计 | — |
| 系统设计 §8 Deployment CRUD 接口（/v1/deployments） | VRC-MGMT-001 | ADM-DEPL-12 | negative | P1 | 删除 deployment data token 403 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-01 | normal | P0 | 列出 service-levels | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-02 | negative | P1 | 创建非 fixed tier | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-02b | negative | P1 | 创建已存在 fixed tier | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-03 | normal | P0 | 获取 service-level | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-04 | concurrency | P1 | 更新 service-level | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-04b | negative | P1 | 更新非法字段 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-05 | negative | P0 | 删除 fixed tier | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-06 | negative | P2 | 成员能力不一致 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-07 | negative | P2 | 冻结向量空间冲突 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-08 | recovery | P2 | 内部错误信封（非数组输入） | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-09 | negative | P1 | 创建 service-level data token 403 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-10 | negative | P1 | 更新 service-level data token 403 | 已设计 | — |
| 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） | VRC-MGMT-002 | ADM-SL-11 | negative | P1 | 删除 service-level data token 403 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ADM-PROBE-01 | negative | P0 | 探测缺确认 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ADM-PROBE-02 | normal | P1 | 探测带确认 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ADM-PROBE-03 | negative | P1 | 探测未知 deployment | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-INF-004 | ADM-RUNTIME-01 | normal | P1 | 运行时快照 | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-INF-004 | ADM-RUNTIME-02 | security | P1 | 运行时快照负向（角色） | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-API-002 | ADM-RUNTIME-03 | security | P2 | 运行时快照缺凭据 401 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-01 | normal | P1 | 统计聚合 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-02 | normal | P2 | 分组 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-03 | negative | P1 | 缺时间窗 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-04 | negative | P1 | 统计接口 data token 403 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ADM-AUDIT-01 | security | P0 | 审计事件 + 脱敏 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-006 | ADM-AUDIT-02 | boundary | P1 | 审计分页 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ADM-AUDIT-03 | negative | P1 | 审计非法分页参数 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ADM-AUDIT-04 | negative | P1 | 审计接口 data token 403 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ADM-LOGS-01 | security | P0 | 脱敏日志 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ADM-LOGS-02 | negative | P1 | 缺时间窗 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ADM-LOGS-03 | negative | P1 | 日志接口 data token 403 | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ADM-USAGE-01 | normal | P1 | 管理面 usage | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ADM-USAGE-02 | boundary | P1 | 管理面分页 | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ADM-USAGE-03 | normal | P1 | 清空 usage（admin + 审计） | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | OBS-DIAG-01 | normal | P1 | 读取诊断开关 | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | OBS-DIAG-02 | normal | P1 | 更新诊断开关 | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | OBS-DIAG-03 | negative | P2 | 开关更新非法值 | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | OBS-SNAP-01 | normal | P1 | 快照页（脱敏） | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | OBS-SNAP-02 | recovery | P2 | 快照无效 cursor | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | OBS-SNAP-03 | recovery | P1 | 诊断快照 store 不可用 503 | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | OBS-STATS-01 | normal | P1 | 诊断统计窗口 | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | OBS-STATS-02 | negative | P1 | 统计缺 since/until | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | OBS-STATS-03 | recovery | P1 | 诊断统计 store 不可用 503 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | OBS-TRACE-01 | normal | P1 | trace 列表去重 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | OBS-TRACE-02 | recovery | P2 | trace 列表分页/游标 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | OBS-TRACE-03 | recovery | P1 | 诊断 trace store 不可用 503 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-01 | normal | P0 | 读取 deployment 注入配置 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-02 | normal | P0 | 写入故障注入 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-03 | negative | P1 | 注入未知 deployment | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-04 | negative | P1 | 非法注入项 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-05 | recovery | P1 | 写入故障注入 store 不可用 503 | 已设计 | — |
| 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） | VRC-DIAG-002 | OBS-REQTRACE-01 | normal | P1 | 请求全生命周期 trace | 已设计 | — |
| 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） | VRC-DIAG-002 | OBS-REQTRACE-02 | negative | P1 | 未知 request_id | 已设计 | — |
| 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） | VRC-API-002 | OBS-REQTRACE-03 | security | P1 | 请求追踪负向（角色） | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-001 | OBS-ALIAS-01 | normal | P1 | 别名 diagnostics（GET+PATCH） | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | OBS-ALIAS-02 | normal | P2 | 别名 diagnostics/snapshots | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | OBS-ALIAS-03 | normal | P2 | 别名 trace | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-004 | OBS-ALIAS-04 | normal | P2 | 别名 deployments diagnostics（GET+PATCH） | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | OBS-ALIAS-05 | normal | P2 | 别名 diagnostics/stats | 已设计 | — |
| 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） | VRC-DIAG-002 | OBS-ALIAS-06 | normal | P2 | 别名 diagnostics/traces | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-01 | security | P0 | Data 端点 LAN trust 无 token | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-02 | security | P0 | 错误 bearer | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-03 | security | P0 | Data token 访问 admin 面 | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-04 | security | P0 | Admin 端点 LAN trust 无 token | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-05 | security | P0 | 公共端点无需 token | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-06 | security | P2 | 空 bearer | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-MGMT-003 | AUTH-07 | security | P0 | 未配置鉴权 | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-08 | security | P1 | 别名命名空间需 admin | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-09 | security | P1 | 管理面未授权优先于资源存在性 | 已设计 | — |
| 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） | VRC-API-002 | AUTH-10 | security | P1 | 缺/非法凭据 401 | 已设计 | — |

**Case 总数：163（设计数）**（分类：normal 50 / boundary 7 / negative 57 / concurrency 7 / recovery 26 / security 16；环境 A 102 / B 61；Priority P0 46 / P1 93 / P2 24）。**设计数 = 已实现数 163**：全部 163 个设计 Case 均有自动化入口（163 个 `at_*.py` 文件；`--collect-only` 实际 collect=176 项，多出者为参数化/双臂测试——`-m api_a`＝105、`-m api_b`＝71）。逐 Case 的输入/执行/Oracle/判定/证据/清理见 `tests.system-case` 文档（`cases/<lowercased-case-id>.md`），本方案不展开。

**设计验证项覆盖**：本清单 `设计验证项 ID` 取自各 Case 的 `tests.system-case` 文档所声明的设计验证项（`DP-RESP-16`/`DP-RESP-23` 两 Case 的 case 文档未声明，按系统设计 §7.8 错误目录 `ERR-REQ-JSON`→`VRC-INF-001`、`ERR-PROVIDER-FAIL`→`VRC-INF-003` 反查补全；未新增任何 VRC ID）。设计文档（系统设计 §7/§8/§14、机制 §15、模块设计 §14、ISD §9.1）共声明 **33 个设计验证项**；本清单覆盖 **14 个**，**19 个无系统层 Case**（逐项裁决见 §4；其中 13 项为模块级验证项、行为由单元层承接＝Tailored-N/A，6 项 `VRC-UI-001..006` 因本项目无浏览器/JS 宿主定稿为 Tailored-N/A）。逐项覆盖数：`VRC-INF-001` 31、`VRC-MGMT-006` 21、`VRC-MGMT-001` 22、`VRC-MGMT-002` 22、`VRC-API-002` 13、`VRC-DIAG-002` 15、`VRC-DIAG-004` 15、`VRC-MGMT-003` 9、`VRC-INF-002` 5、`VRC-DIAG-001` 4、`VRC-INF-004` 7、`VRC-LOG-001` 3、`VRC-UTIL-001` 2、`VRC-INF-003` 1。

### 3.6 需求（`LT-*`）到 Case 的可追溯映射（§3 的 §3.6-等价节）

> 命名沿用已退役 `llmtier-api-test-specification` §3.6 的链式定义（`LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case 家族），**不新增顶层章节**（本节是 §3 的子节）。链的**唯一权威来源**是需求文档 [`llmtier-requirements.md`](../../10_requirements/llmtier-requirements.md) 的 `LT-*` 条目、系统设计、机制需求与 `CT-*` 静态契约；本节只登记映射，不复制定义。Case 家族按 Case ID 前缀分组，成员以 §3 清单为准（含本版新增 23 个 Case）。任一 case 文档的"目的/来源"字段可回指本表。

| Case 家族（按 §3 前缀） | 需求 `LT-*` | 机制需求 `R-*` | 设计验证 `VRC-*` | 机制 `T-*` | 契约 `CT-*` |
|---|---|---|---|---|---|
| `HEALTH-*` | LT-FUN-006、LT-OPS-001 | R-CFG-02、R-TRUST-04 | VRC-API-002、VRC-MGMT-003、VRC-UTIL-001 | T-TRUST-NOCFG、T-OBS | CT-OPS-001 |
| `DP-MODELS-*` | LT-FUN-002 | R-INF-04、R-INF-07 | VRC-INF-001/002 | T-TRUST-ENDPOINTS | CT-MODEL-001 |
| `DP-RESP-*` | LT-FUN-001/008、LT-INT-001/006、LT-PERF-001、LT-REL-001 | R-INF-01..06、R-TRUST-01、R-TRUST-02 | VRC-INF-001/003/004、VRC-DIAG-004 | T-STREAM、T-TOOLS、T-QUEUE、T-TIMEOUT、T-DISCONNECT、T-OBS-INJECT | CT-DP-001、CT-BOUNDARY-001、CT-ADM-001 |
| `DP-EMB-*` | LT-FUN-003、LT-OPEN-02 | R-INF-04/05/07 | VRC-INF-001/002/004 | T-QUEUE（准入）、T-STREAM（无） | CT-EMB-001 |
| `DP-USAGE-*` | LT-FUN-004、LT-INT-004/005/007、LT-REL-003 | R-MET-01..04 | VRC-MGMT-006、VRC-INF-004 | T-MET-FINAL、T-MET-PAGE、T-MET-RESET、T-MET-UNKNOWN、T-MET-CRASH（`DP-USAGE-09`） | CT-USAGE-001、CT-STORE-001 |
| `ADM-PROV-*` | LT-FUN-005、LT-SEC-001、LT-INT-008、LT-REL-004 | R-CFG-01、R-CFG-03 | VRC-MGMT-001/002 | T-CFG-CAS、T-CFG-SECRET、T-CFG-DELREF、T-CFG-BADREF、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ADM-PROV-MODELS-*` | LT-FUN-005 | R-CFG-01 | VRC-MGMT-001 | T-CFG-SECRET | CT-ADMIN-001 |
| `ADM-PROV-USAGE-*` | LT-FUN-005/006、LT-OPS-002 | R-CFG-01、R-OBS-01 | VRC-MGMT-006、VRC-DIAG-004 | T-CFG-SECRET | CT-ADMIN-001、CT-OPS-001 |
| `ADM-DEPL-*` | LT-FUN-005、LT-INT-008 | R-CFG-01 | VRC-MGMT-001/002 | T-CFG-CAS、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ADM-SL-*` | LT-FUN-005、LT-PERF-002 | R-CFG-01 | VRC-MGMT-002 | T-CFG-SPACE、T-CFG-CAS、T-TRUST-ENDPOINTS | CT-ADMIN-001 |
| `ADM-PROBE/RUNTIME/STATS/AUDIT/LOGS/USAGE-*` | LT-FUN-005/006、LT-OPS-002/006、LT-SEC-002/004、LT-INT-002 | R-OBS-01/02、R-MET-03、R-CFG-01、R-INF-03 | VRC-MGMT-003/006、VRC-LOG-001、VRC-DIAG-001、VRC-INF-004 | T-OBS、T-MET-RESET、T-MET-PAGE | CT-ADMIN-001、CT-LOG-001、CT-OPS-001、CT-USAGE-001 |
| `OBS-*` | LT-FUN-005、LT-OPS-006、LT-INT-002/007、LT-SEC-002 | R-OBS-01..06 | VRC-DIAG-001/002/004 | T-OBS-SWITCH、T-OBS-SNAP、T-OBS-STATS、T-OBS-TRACE、T-OBS-INJECT | CT-ADMIN-001、CT-LOG-001 |
| `AUTH-*` | LT-INT-001、LT-SEC-001 | R-TRUST-01..04 | VRC-API-002、VRC-MGMT-003 | T-TRUST-BEARER、T-TRUST-LAN、T-TRUST-SHARED、T-TRUST-NOCFG、T-TRUST-LEAK、T-TRUST-ENDPOINTS | CT-ADMIN-001 |

**需求覆盖结论（35 项 `LT-*`）**：上表以"家族级"重建追溯链，**26 项有 Case 家族承接**（`LT-FUN-001..006/008`、`LT-INT-001/002/004/005/006/007/008`、`LT-OPEN-02`、`LT-OPS-001/002/006`、`LT-PERF-001/002`、`LT-REL-001/003/004`、`LT-SEC-001/002/004`），**9 项不在本运行层分母**（逐项见下方「需求缺口裁决」，**全部定稿 Tailored-N/A，无具名 Gap**）：`LT-FUN-007`、`LT-INT-003`、`LT-REL-002`（静态 absence/边界，由 `CT-BOUNDARY-001`/`CT-SCOPE-001`、`tests/system/st_04_forbidden_scan.py` 与 `tests/contract/test_contract_semantics_v03.py` 承接，非本运行层分母）；`LT-OPS-003/004/005`、`LT-OPEN-03`（运维/实现 Gate 承接，权威＝运维手册与 release 文档）；`LT-PERF-003`（声明性约束，权威＝release §7）；`LT-SEC-003`（生产 TLS/SSO 部署面，权威＝`std-tailoring` `LT-TL-022`）。**家族级覆盖 ≠ 逐 Case 文档均引用该 `LT-*`**：本表是设计级映射权威，不要求每个 case 文档重复列出家族内全部 `LT-*`；case 文档按需引用其直接相关者。原评审以"逐 case 文档字面出现"计数（18/35）低估了这些家族级承接；本表按 STD 需求→Case 追溯语义重建。

## 4. 不适用与缺口裁决

<span style="color:#1f6feb"><em>**本节目的**：区分“不适用”与“尚未设计”。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：Tailored-N/A 必须引用设计章节事实；Gap 须有 Owner 与恢复条件；两者都不从分母静默消失。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每条裁决有事实或 Owner；无“顺手 N/A”。</em></span>

> **模块级验证项裁决依据（重要）**：下表中 19 项模块级验证项（`VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`、`VRC-UI-001..006`）是**模块设计 §14 的验证项**，系统层清单不承载其中内部行为者。**本项目未采用独立模块测试层**——不存在 `tests.module-test-scheme`（`tests.module-test-plan` 模板要求方案绑定单一软件模块，本项目有 M001–M008 共 8 个模块；建立合并模块方案需与 LT-TL-023 同级的用户授权，当前无此授权，故不虚构该层，不复制第二 authority）。各模块 §14 验证项的**行为级承接方**是 `llmtier-unit-test-scheme` §3（该方案 §1 明确被测模块内部为真实实现、仅替换进程外上游，即整模块组装层语义），**不是**任何"模块测试设计"；故本方案**不再声称"归模块测试设计承接"**，按事实登记：有真实行为宿主者标 `Tailored-N/A（下层承接）`；**唯一无宿主者 `VRC-UI-001..006` 已定稿为 `Tailored-N/A`（事实＝本项目无浏览器/JS 宿主，见下行），不再保留为 Gap**；`VRC-OBS-001..005` 的行为级有单元宿主（Tailored-N/A 下层承接），仅其视觉子项无宿主、同定稿 Tailored-N/A。本表不再有"具名 Gap 承接方不存在"的条目。

> **本表无未关闭 Gap（本版终审）**：所有适用性裁决均为 **Tailored-N/A**（含子系统级别、验收活动、生产环境、模型质量、容量/耐久、运维恢复）或**已关闭/已覆盖**（`ERR-*` envelope code＝单元宿主覆盖、缺凭据 401＝单元宿主覆盖、三项 OpenAPI 偏差＝无偏差/改声明对齐）。每条均引用真实 artifact 或 std-tailoring 权威；无"无 ETA 的具名缺口"。

| 来源 ID / 事实依据 | 裁决（Tailored-N/A / 已关闭 / 已覆盖） | Owner / 权威与恢复条件 |
|---|---|---|
| **子系统测试级别** | Tailored-N/A | 本项目**无 `design.subsystem` 设计文档**：LLMTier 是纯软件系统，软件系统设计（`llmtier-system-design`）直接展开为模块（M001/M003/M004/M005/M006/M007 等），不存在软件子系统对象。故不采用 `tests.subsystem-test-scheme`；系统层方案直接承接系统设计 §7/§8 与机制端到端的测试分母。若将来引入 `design.subsystem`，本裁决须重新评审并补建子系统方案。 |
| 验收活动 | Tailored-N/A（不在 tests 家族） | 客户/项目验收与 release 放行授权**不属于 tests 家族**（STD 模板选择规则：验收按项目 tailoring 承接）。本方案不承载验收判定；`Gate` 只给放行建议，不等于验收或上线授权。 |
| 真实生产环境（TLS 反向代理、生产 SSO/MFA、浏览器无 bearer、HttpOnly/CSRF） | **Tailored-N/A（定稿；非 Gap；不在 tests 家族）** | Owner：运维/安全。**权威**：STD 模板选择规则（验收/生产部署活动按项目 tailoring 承接，不在 tests 家族）＋ `std-tailoring.md` `LT-TL-022`（验收/运行时激活为 deferred）＋ `llmtier-release-and-operations.md` §10（目标 runbook）、§11（production acceptance 前置）。**事实**：production TLS/SSO/CSRF 是反向代理/部署面行为，本项目测试 harness 是 LAN 上 HTTP 黑盒，无 TLS/SSO 终止端；`runtime_activation=false`（OpenAPI `x-llmtier-runtime-activation=false`），激活证据属运维 Gate。故**不写空 Case**；`LT-SEC-003` 同此裁决。恢复条件＝生产部署面可用且 `runtime_activation` 决策启动后，由验收活动（`LT-TL-022`）承接。 |
| 上游模型答案质量与推理正确性 | **Tailored-N/A（定稿；非 Gap；不在测试分母）** | Owner：模型/推理。**权威**：`llmtier-requirements.md` `LT-PERF-003`/§10「静态 PASS 不证明实现上线」＋ `llmtier-system-design` §1 范围（本系统不拥有模型权重/推理正确性，上游 OMLX 为外部依赖）＋ `std-tailoring.md` `LT-TL-020`（内容评测不在 tests 家族）。**事实**：本方案只断言结构/事件序列/字段契约，不把模型内容当 Oracle（系统设计 §8）；内容评测需独立统计口径与评测集，属模型评测专项。故**不写空 Case**。恢复条件＝定义独立内容 Oracle 与统计口径后另立评测专项。 |
| 容量/耐久（FD 泄漏、30min 耐久、50 并发） | Tailored-N/A（本层不测；非缺口） | Owner：性能/运维。**事实依据**：本项目测试 harness 是**功能性 pytest 黑盒**（`tests/system/api_test_v03/*`＋`runner_a/b.sh`，`exec pytest`），无负载驱动、无 FD 采样器、无长稳计时运行器；系统设计未把 FD/30min/50 并发列为系统层组合保证（§1 已声明不证明）。故**不写空 Case、不保留"无 ETA"的 Gap**——本项按 tailoring 明确不在本方案分母内；原退役 `llmtier-test-plan` 的 ST-18/19/21 与 §2 `endurance` 裁剪一致。恢复条件（若需容量结论）：另立性能/运维专项（自有负载工具与计时运行器）执行，结果不合并进本方案分母。 |
| 进程 crash/restart 后的运维恢复、备份/恢复演练 | **Tailored-N/A（定稿；运维承接；非 Gap）** | Owner：运维。**权威**：`m5air-operations-manual.md` §12（停止/重启 ≤60s）、§14（冷备份/恢复流程）、§15（更新/回滚）；`llmtier-release-and-operations.md` §6/§10（升级/恢复目标 runbook）。**事实**：运维级恢复/备份演练是运维活动（`LT-OPS-003/004/005`），不是 HTTP 运行层行为；本层不做破坏性 DB 构造。**注**：账本在崩溃/重启后的**核心不变量**（orphan unknown 不回填 0，`T-MET-CRASH`）已由 `DP-USAGE-09` 覆盖；`LT-OPS-005` 的 QuerySnapshot TTL 由 `DP-USAGE-04`（过期 cursor）间接覆盖。恢复条件＝真实 systemd/备份密钥/restore rehearsal 交付后由运维专项执行（`LT-OPEN-03` implementation gate）。 |
| `ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`/`ERR-UTIL-TXN` 的 envelope code | Tailored-N/A（下层承接；非 Gap——4 项均有单元宿主） | Owner：M007/M004。**关闭事实（本版代码复核）**：4 项 envelope code 均由 `llmtier-unit-test-scheme` §3 的真实单元用例直接断言（被测模块内部真实、仅隔离临时库，`http_api.errors.ApiError` 的 `status`/`code` 逐一相等）：`bootstrap_required`＝`UT-MGMT-001::test_empty_store_without_settings_is_bootstrap_required`；`bootstrap_invalid`＝`UT-MGMT-001::test_missing_section_fails`/`test_env_secret_ref_unavailable_fails`/`test_file_secret_ref_missing_fails`；`schema_unknown`＝`UT-UTIL-002::test_legacy_store_without_schema_meta_rejected`；`schema_version_mismatch`＝`UT-UTIL-002::test_version_mismatch_rejected`；`schema_integrity_failed`＝`UT-UTIL-004::test_integrity_failure_is_503`；`store_path_unsafe`＝`UT-UTIL-001::test_symlink_path_rejected`；`E-UTIL-NESTED-TXN`＝`UT-UTIL-004::test_nested_transaction_is_409`。**本层不测的理由（事实）**：`/readyz` 503 body 为 `ReadinessView` 而非 `ErrorEnvelope`（无 `code`）；其余需破坏性构造（symlink DB、嵌套事务）从 HTTP 无法无破坏触发。`ERR-BOOT` 的表现层另由 HEALTH-04/05 覆盖。 |
| 非受信来源的真实"缺凭据" 401 | Tailored-N/A（下层承接；非 Gap——单元宿主存在） | Owner：代码 owner（`src/http_api/auth.py`）。**关闭事实**：A/B 受信网段无法构造非受信来源，但 `src/http_api/auth.py::authenticate`/`unauthenticated_principal` 可用合成非受信地址（如 `8.8.8.8`）直接单元验证：`unauthenticated_principal("8.8.8.8", Headers(), role)` 返回 `None`，随后 `authenticate(Headers(), role)` 抛 `ApiError(401, "authentication_required")`——由 `llmtier-unit-test-scheme` §3 `UT-API-008::test_non_trusted_address_without_credential_is_401` 覆盖。系统层 AUTH-10 仍以非法授权方案（`Basic`）触发同一 401 分支。本层无系统级构造，缺口按"单元级已覆盖"关闭。若引入显式 env 门控须重新评审。 |
| `VRC-INF-005`（观测 fail-open / 不二次校验，M003；模块设计 inference §14.5） | Tailored-N/A（下层承接） | Owner：M003。本层不测；行为承接＝`llmtier-unit-test-scheme` §3 `UT-INF-005`（观测抛错时推理结果不变）。**非 Gap**——宿主存在。 |
| `VRC-UTIL-002`（事务/初始化/拒绝，M007；模块设计 util §14.2、`ERR-PATH-UNSAFE`） | Tailored-N/A（下层承接） | Owner：M007。本层不测；承接＝`llmtier-unit-test-scheme` §3 `UT-UTIL-002`/`UT-UTIL-004`（回滚/幂等/损坏库/嵌套事务 409/并发启动）。`ERR-PATH-UNSAFE` 的 HTTP envelope code 由 `UT-UTIL-001::test_symlink_path_rejected` 单元覆盖（见上方 envelope code 行，已关闭）。 |
| `VRC-API-001/003/004`（M001 分发/错误、body/SSE、静态与健康；模块设计 http-api §14.1/§14.3/§14.5/§14.6） | Tailored-N/A（下层承接） | Owner：M001。本层不测；承接＝`llmtier-unit-test-scheme` §3 `UT-API-001/003/004/005/006/007/009/010/011/012/013`（分发/错误信封/body/SSE 单帧/静态穿越/fail-open 降级）。 |
| `VRC-MGMT-004/005`（M004 分页与清空、探测；模块设计 management §14.4/§14.5） | Tailored-N/A（下层承接） | Owner：M004。本层不测；承接＝`llmtier-unit-test-scheme` §3 `UT-MGMT-004/005/009/010`（cursor 过期/`reset_usage` 范围/探测不可达）。系统层 `DP-USAGE-*`/`ADM-USAGE-*`/`ADM-PROBE-*` 以表现层 Case 间接覆盖（登记于 `VRC-MGMT-006`/`VRC-DIAG-004`）。 |
| `VRC-DIAG-003`（M006 libdiag fail-open；模块设计 libdiag §14.3） | Tailored-N/A（下层承接） | Owner：M006。本层不测；承接＝`llmtier-unit-test-scheme` §3 `UT-DIAG-003`/`UT-DIAG-007`（写入/初始化失败不阻断、降级）。 |
| `VRC-OBS-001..005`（M005 observability：开关/查询脱敏/注入/关联标识/诊断页；模块设计 observability §14.1–§14.5） | Tailored-N/A（下层承接）＋**视觉子项 Tailored-N/A** | Owner：M005（视觉子项 Owner：M002 web-ui）。本层不测；行为承接＝`llmtier-unit-test-scheme` §3 `UT-OBS-001..007`。**视觉子项**（诊断页 tabs/Disabled 呈现）**定稿为 Tailored-N/A**：本项目 harness 无浏览器/JS 宿主（无 node/jsdom/playwright/selenium，已核实全仓零命中），静态渲染无法驱动，故不写空 Case、不保留 Gap；单元层同步**定稿 Tailored-N/A**（`llmtier-unit-test-scheme` §4，`std-tailoring` `LT-TL-024` 记录），恢复条件＝引入浏览器/E2E 宿主后重评。 |
| `VRC-UI-001..006`（M002 web-ui：加载/编辑鉴权/Pause/用量未知/探测确认/诊断页；模块设计 web-ui §14.1–§14.7） | Tailored-N/A（定稿；非 Gap） | Owner：M002 web-ui。**事实依据**：本项目 harness **无浏览器/E2E 宿主**——全仓无 node/jsdom/playwright/selenium（已核实零命中），系统层为 HTTP 黑盒且本层无 UI 端点 Case；静态渲染不可驱动，**不写空 Case**。故该 6 项行为级断言**定稿为 Tailored-N/A**（明确不在本方案分母内），**不再登记为"具名 Gap"**，也不"承接"到不存在的文档。下层现状：`llmtier-unit-test-scheme` §3 有 `UT-UI-001..010`（`test_webui_contract.py`）承接静态/契约子项；纯视觉子项同一事实在单元方案 §4 **定稿 Tailored-N/A**（Owner M002；`std-tailoring` `LT-TL-024` 记录）。恢复条件：引入浏览器/JS 宿主后由单元层升级为行为断言并重评本裁决。 |
| ~~`POST /v1/responses` 声明的 `422`（OpenAPI）~~ **已关闭（无偏差）** | **Closed — 无偏差，无需 Case** | Owner：M001 http-api/规格。**结案事实**：复核 `interfaces/openapi/llmtier.openapi.json` `/v1/responses` 的 responses 恰为 `200/400/401/404/429/502/503`，**不含 422**；`grep -rn "422" src/` 零命中、`grep -rn "422" docs/20_system_design` 零命中。实现与设计一致使用 `400 invalid_json`（`app.py:161-162` `_body()`；系统设计 §7.8 `ERR-REQ-JSON`），已由 `DP-RESP-16` 覆盖、schema 级违例由 `DP-RESP-08/12..15` 覆盖。原条目所称"OpenAPI 声明的 422"为过时陈述：OpenAPI 从未声明 422。**无偏差可消**，条目关闭。 |
| ~~`POST /v1/probes` 声明的 `502`（OpenAPI）~~ **已关闭（改声明对齐实现）** | **Closed — 按观测语义改契约声明** | Owner：M004 管理/M003 推理/规格。**裁决**：探测是**观测**，上游不可达/失败是观测结果而非接口错误——`OpenAIProvider.probe` 对**所有**上游异常 `except Exception: return False`（`providers/openai.py:144-145`），`AdminService.probe` 据此返回 `200 ProbeResult{status:"unhealthy"}` 并落库 health（`admin.py:119-122`）；模块设计 M004 §4.2「探测失败 → `unhealthy`」、health 枚举「`unhealthy`：探测失败」为设计意图权威，单元测试 `test_management_gaps.py::test_unreachable_probe_is_unhealthy_persisted` 锁定该行为。故**改声明对齐实现**：已从 OpenAPI `/v1/probes` 删除 `502 ProviderFailure`（并入 `404 NotFound`）；系统设计 §8、`llmtier-api-reference.md` §3.2 同步为"无 502"；`http-api-design.md`、机制 `inference-stream.md` §5 原即无 502。`ADM-PROBE-02/03` 已覆盖 200/404 表现。**偏差消除，条目关闭**。 |
| ~~Embeddings 的 `provider_failure`（`fault_502` 注入码）~~ **已关闭（不可达声明已移除）** | **Closed — 对齐已实现契约** | Owner：M003 推理/规格。**裁决**：`provider_failure` 仅在 `ResponsesService.create` 的注入分支产生（`responses.py:110`）；`EmbeddingsService.create` **不读** `enabled_injection`，无故障注入路径，该码在 Embeddings 不可达。设计不要求 Embeddings 注入（系统 §7.8 承接索引 `ERR-PROVIDER-INJECTED` 仅登记 `/v1/responses`；机制 `observability.md` 注入仅作用于推理流）。故移除"Embeddings `provider_failure`"声明，确认 Embeddings 错误码恰为可达集：`400`（`invalid_request`/`unsupported_model`/`unsupported_dimensions`/`invalid_json`/`request_too_large`）、`404 model_not_found`、`429 rate_limit_exceeded`、`502 provider_contract_error`、`503 provider_unavailable`/`provider_secret_unavailable`/`usage_store_unavailable`；OpenAPI `/v1/embeddings` 与系统 §7.8 一致。`DP-EMB-09`（502 契约错误）/`DP-EMB-10`（503 不可用）已覆盖可达集。**偏差消除，条目关闭**；若未来为 Embeddings 增加注入支持须重评。 |

> **三项具名缺口结案（本版终审）**：`POST /v1/responses` 的 `422`、`POST /v1/probes` 的 `502`、Embeddings 的 `provider_failure` 三项在本次按"对外契约/错误码 → 代码 vs 设计"归属规则逐项结案——**项 1 无偏差**（OpenAPI/源码/设计均无 422，全程 `400 invalid_json`）；**项 2、项 3 为过时/不可达声明**，按规格修订（改 OpenAPI/文档对齐实现与设计意图），不动代码。三项均已从 Gap 清单**关闭**，非重新登记；验证以 `DP-RESP-16`、`ADM-PROBE-02/03`、`DP-EMB-09/10` 承接。

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
| `LT-OPS-004`（恢复确认分层检查 process/config/model availability/Usage store，仅授权后 smoke） | **Tailored-N/A（定稿；运维承接；非 Gap）** | Owner：运维。**权威**：`llmtier-release-and-operations.md` §10 步骤 5–6（停止→保全→恢复备份→离线 integrity→只读启动→Registry/Usage/Audit 抽样→受授权 smoke）；`m5air-operations-manual.md` §8（启动验证）、§14.2（恢复后检查 Registry/Usage/Audit）。**事实**：分层恢复检查与授权 smoke 是运维流程；无副作用 health/readiness 读取由本层 `HEALTH-*` 运行层承接，真实 provider smoke 需 operator 授权（`LT-FUN-006`）。恢复条件＝运维分层恢复检查执行记录落地。 |
| `LT-OPS-005`（单节点 systemd 基线、优雅摘流 ≤60s、QuerySnapshot TTL 15min、Usage/Audit 保留 30/90 天、加密备份 7日+4周、RPO 24h/RTO 4h、release 前隔离 restore 演练） | **Tailored-N/A（定稿；运维承接；非 Gap；TTL 已间接触及）** | Owner：运维。**权威**：`llmtier-release-and-operations.md` §9（retention TTL、加密备份 7日+4周、RPO 24h/RTO 4h、release 前隔离 restore）、§10（systemd、摘流 ≤60s）；`m5air-operations-manual.md` §12/§14。**事实**：systemd/保留策略/加密备份/restore rehearsal 属运维专项，本层无对应 harness；QuerySnapshot TTL 由本层 `DP-USAGE-04`（过期 cursor→400）间接验证；Usage/Audit 保留期由 `UT-MGMT-009`（`reset_usage` 范围）与 `UT-LOG-002`（`page` 边界）在单元层部分承接。恢复条件＝真实 systemd/备份密钥/restore rehearsal 交付后由运维专项执行（`LT-OPEN-03`）。 |
| `LT-OPEN-03`（单节点 Linux + TLS 反代 + systemd + 加密备份 + runbook；design closed / implementation gate） | **Tailored-N/A（定稿；实现 Gate，非测试缺口）** | Owner：LLMTier。**权威**：`llmtier-requirements.md` §11（`LT-OPEN-03` 设计已关闭、待实施证据）＋ `llmtier-system-design` §16（`LT-OPEN-03` design closed / implementation gate）＋ `llmtier-release-and-operations.md` §10（"真实 systemd unit、代理/SSO 配置、备份密钥和 restore rehearsal 尚未交付，因此 activation 仍 BLOCKED"）。**事实**：这是**实现/部署 Gate**，不是测试设计缺口——设计已关闭，缺的是部署证据（真实单节点 Linux 基线 + TLS/systemd/加密备份）。本方案（测试方案）不承载部署证据；恢复条件＝runtime activation 前完成部署证据。 |

## 5. 文档联动与清单变更规则

<span style="color:#1f6feb"><em>**本节目的**：固定方案—用例—计划的联动规则，防三处漂移。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：新 Case 先入本清单再建 case-design 文档（文档 ID＝Case ID）；清单变更须同步计划构成表；写明方案冻结/版本规则。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：清单与 case-design 文档一一对应；计划只引用不复制。</em></span>

- **方案冻结与变更规则**：Case 清单随系统设计基线**冻结**；系统设计或机制变更导致分母变化时，本方案升版并同步 `tests.system-test-plan` 的构成表。Case ID 一经登记**不复用、不改名**；新增 Case 取同家族下一个未占用序号（含补丁后缀，如 `ADM-SL-02b`）；废弃 Case 标 `superseded`，不删除、不重编号。
- **与 case-design / 计划的同步规则**：**新 Case 先入本清单 §3，再建 case-design 文档**；case-design 文档路径固定为 `docs/70_verification/specifications/cases/<lowercased-case-id>.md`（例：`DP-RESP-01` → `cases/dp-resp-01.md`），文档 ID = Case ID；`tests.system-test-plan` 只引用本方案版本，不复制 Case 清单。本方案只登记 Case **设计状态**（Designed/Gap/Tailored-N/A），不承载实现状态（在 case-design 文档）与执行状态/Verdict（只在 Run 报告）。
- **本方案的退役与吸收映射**：本方案**唯一吸收并取代**旧 `assurance.test-specification` 家族的 `llmtier-api-test-specification`（140-Case 权威清单、定量覆盖模型、Traceability、环境与共同机制）与 `llmtier-contract-test-specification`（静态契约 `CT-*` 的 runtime 落地边界）。二者已从 `docs/70_verification/specifications/` 退役（git rm）；其原 Case ID 与数量（140）作为基线**保持不变**（不重命名、不重编号），逐 Case 细节现由 `tests.system-case` 文档承载；本版在该基线上按覆盖洞评审（`coverage_review`）**新增 23 个 Case**（`DP-EMB-08..10`、`ADM-*-15..`、`OBS-*-03..`、`DP-USAGE-09`、`DP-RESP-26/27` 等，见 §3），清单总数 140 → **163**。
- **需求到本方案的可追溯入口**：本方案各 Case 家族的追溯链 `LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case **已重建并落于 §3.6**（由退役 `llmtier-api-test-specification` §3.6 与需求文档重建；不再依赖已退役 source）。需求缺口（9 项 `LT-*`）见 §4「需求缺口裁决」；逐 Case 的 Run 侧追迹另由 case 文档与 Run manifest 的 `target_artifact` 锁定。

### 未决项与歧义记录（本方案自记录）

> 以下为实施本方案时发现的 STD 读数歧义；本方案按"采取 STD 读数并显式登记"处理，未静默猜测。列出以提请 STD 维护者裁决。

1. **Case ID 命名语法**：模板 §3 示例使用 `SYS-<对象>-<NNN>` 语法，且"必须写清楚"要求 Case ID 稳定唯一（`SYS-<对象>-<NNN>`）。本方案沿用 LLMTier 既有 Case ID 前缀（`HEALTH-*`/`DP-*`/`ADM-*`/`OBS-*`/`AUTH-*`，140 个基线 ID 加后续按覆盖洞新增的 23 个同族 ID），与模板语法不一致。**采取读数**：任务明确要求既有 Case ID 保持不变（140 基线不重命名）；Case ID 的"稳定且唯一"是本质要求，前缀族名形式由项目既有惯例决定。**歧义**：模板是否强制 `SYS-` 前缀，或仅为示例，待 STD 裁决。
2. **"未决项章节"**：任务要求"在方案的未决项章节记录歧义"，但 `tests.system-test-scheme` 模板**没有**未决项章节（正文仅 §1–§5，另有附录 A）。**采取读数**：遵守"匹配模板精确章节集、不得自创章节"，将未决项作为 §5 内的具名小节记录，而非新增顶层章节。
3. **`来源 ID` 粒度**：模板要求"一个来源 ID 至少一条记录"。原规格以 route×method×role×error-code 为覆盖分母，未给"来源 ID"独立编号。**采取读数**：按系统设计 §8 接口/机制分组作为来源 ID（如"系统设计 §8 Responses 接口"），一个来源对应多条 Case；不新造记录编号。
4. **`design_level` 取值**：`new-design` 对 `tests.system-test-scheme` 未在层级映射中登记，生成默认 `cross-level`；STD 指南称系统方案"对应 design.software-system（系统设计阶段）"。**采取读数**：metadata 置 `design_level=system`、`domain=[software]`（与系统层语义一致）；`validate-design` 不对此强制，故为语义读数而非工具强制。
5. **（已关闭）逐 Case 设计文档的入站链接（跨任务移交）**：原记录为"140 份 `tests.system-case` 文档仍指向已退役的 `../llmtier-api-test-specification.md`，重写前 `validate-design docs` 会报告 `link.missing`"。**关闭事实**：并行工作项已完成 case 文档重写——当时全部 141 份 case 文档（140 Case + README）**均不再**引用任何退役规格（0 处），且全部以真实路径引用本方案（`llmtier-system-test-scheme.md`）；`validate-design docs` 不再报告该类 `link.missing`。本条歧义已消解，保留以存档（其后按覆盖洞新增的 23 份 case 文档同样不引用退役规格）。

## 附录 A. 本层设计验证项 VRC 汇集（对照用）

<span style="color:#1f6feb"><em>**本节目的**：把设计文档声明的本层验证项 VRC 汇集于此，供逐项对照 §3 清单的覆盖。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：VRC 清单以设计文档（design §12/§14）为唯一权威，本附录只登记 ID 与要验证什么，不复制判据/Oracle 定义；设计变更时本附录同步；每个 VRC 必须在 §3 清单有至少一个 Case，否则登记缺口。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：本附录 VRC 集合与设计文档一致；每个 VRC 在 §3 清单有 Case 或缺口。</em></span>

**本层 VRC 集合（33 项）**：`VRC-API-001`、`VRC-API-002`、`VRC-API-003`、`VRC-API-004`、`VRC-INF-001`、`VRC-INF-002`、`VRC-INF-003`、`VRC-INF-004`、`VRC-INF-005`、`VRC-MGMT-001`、`VRC-MGMT-002`、`VRC-MGMT-003`、`VRC-MGMT-004`、`VRC-MGMT-005`、`VRC-MGMT-006`、`VRC-DIAG-001`、`VRC-DIAG-002`、`VRC-DIAG-003`、`VRC-DIAG-004`、`VRC-LOG-001`、`VRC-OBS-001..005`、`VRC-UI-001..006`、`VRC-UTIL-001`、`VRC-UTIL-002`。来源＝各 Case `tests.system-case` 文档所声明者（`DP-RESP-16`/`DP-RESP-23` 按系统设计 §7.8 错误目录反查补全）。

| 设计验证项 ID | 要验证什么（名称/责任） | 设计来源 | §3 Case 覆盖 |
|---|---|---|---|
| `VRC-API-002` | HTTP 入口/鉴权/序列化与健康表现 | 系统设计 §12 | HEALTH-01..06、AUTH-01..10、ADM-RUNTIME-02/03、OBS-REQTRACE-03 |
| `VRC-MGMT-003` | 就绪/审计/未配置鉴权语义 | 系统设计 §12 | HEALTH-02..05、ADM-AUDIT-01/03/04、AUTH-07 |
| `VRC-MGMT-006` | 用量/统计/分页口径 | 系统设计 §12 | DP-USAGE-01..09、ADM-PROV-USAGE-*、ADM-STATS-01..04、ADM-USAGE-*、ADM-AUDIT-02 |
| `VRC-MGMT-001` | Provider/Deployment 管理语义 | 系统设计 §12 | ADM-PROV-01..15/17、ADM-PROV-MODELS-01/02、ADM-DEPL-01/03/05/06/07/08/10/12 |
| `VRC-MGMT-002` | 更新/并发/ETag 与 Service Level 语义 | 系统设计 §12 | ADM-PROV-05..07/09/13/16、ADM-DEPL-04/09/11、ADM-SL-01..11 |
| `VRC-INF-001` | 推理/模型/嵌入路由与请求契约 | 系统设计 §12 | DP-MODELS-01..07、DP-RESP-01..25、DP-EMB-01..09 |
| `VRC-INF-002` | 推理输出/能力集结构契约 | 系统设计 §12 | DP-MODELS-01/07、DP-EMB-03/05 |
| `VRC-INF-003` | 上游非 5xx → provider_error | 系统设计 §12 | DP-RESP-23 |
| `VRC-INF-004` | 准入饱和/候选健康/运行时快照 | 系统设计 §12 | DP-RESP-19/20、DP-EMB-08/10、DP-USAGE-09、ADM-RUNTIME-01 |
| `VRC-DIAG-001` | 诊断开关读写 | 系统设计 §12 | OBS-DIAG-01..03、OBS-ALIAS-01 |
| `VRC-DIAG-002` | 诊断快照/统计/trace/请求追踪 | 系统设计 §12 | OBS-SNAP-01..03、OBS-STATS-01..03、OBS-TRACE-01..03、OBS-REQTRACE-01/02、OBS-ALIAS-02..06 |
| `VRC-DIAG-004` | 故障注入配置与探测 | 系统设计 §12 | DP-RESP-11/22/26/27、ADM-PROV-USAGE-02/03、ADM-PROBE-01..03、OBS-DEPL-01..05、OBS-ALIAS-04 |
| `VRC-LOG-001` | 日志/审计脱敏 | 系统设计 §12 | ADM-LOGS-01..03 |
| `VRC-UTIL-001` | 存储引导/就绪引导表现 | 系统设计 §12 | HEALTH-04/05 |
| `VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005` | 模块级验证项（无系统层 Case；行为由单元层 `llmtier-unit-test-scheme` §3 承接） | 模块设计 §14、ISD §9.1 | §4 裁决：Tailored-N/A（下层承接），逐项列 UT Case |
| `VRC-UI-001..006` | M002 web-ui 行为级验证项（无系统层 Case；本项目无浏览器/JS 宿主） | 模块设计 web-ui §14、ISD §9.1 | §4 裁决：**Tailored-N/A（定稿；非 Gap）**，同 `llmtier-unit-test-scheme` §4 裁决（`std-tailoring` `LT-TL-024`） |



<!-- 交付自查：每个适用来源 ID 是否都有 Case 或具名缺口；清单里的每个 Case ID 是否都有（或计划有）对应 case-design 文档；方案里是否混入了输入构造或 Oracle 细节？ -->
