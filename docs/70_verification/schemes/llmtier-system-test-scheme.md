<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Scheme

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-scheme` |
| Document Version | `0.1.0-draft.4` |
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
| performance | 单 Case 基线采样 + 观察断言（准入上限/超时/`Retry-After`） | 本层只保留时序/预算类可观察断言，非容量结论 | 不用负载/容量压测（本层不负责系统预算，见 §4 Gap） |
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

**总体说明**：A/B 不共享 SQLite/端口/进程且不并行（A 类 PASS 不关闭 B 类，反之亦然）；A 类写用例 teardown 后复位，B 类整班销毁；缺关键环境时整批降级为 Blocked 并登记缺口，不静默换工具链。

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
| negative | 适用 | 45 个 Case：校验/鉴权/资源冲突/上游错误/存储不可用等拒绝路径（含 400/401/403/404/409/412/413/429/503）。 |
| concurrency | 适用 | 6 个 Case：准入饱和 429+`Retry-After`、`If-Match`/412 串行化并发编辑、注入变更与在途流（`DP-RESP-20`、`ADM-PROV-05/06/07`、`ADM-DEPL-04`、`ADM-SL-04`）。 |
| recovery | 适用 | 17 个 Case：故障注入（`fault_502`/`fault_503`/`stream_terminate`/`malformed_event`）、上游/存储失败、客户端断开、`/readyz` degraded/not_ready、schema 引导不可用。 |
| security | 适用 | 15 个 Case：认证/授权/角色隔离、LAN trust、无鉴权配置、secret 不泄露、审计与日志脱敏、别名命名空间鉴权。 |
| performance | 裁剪 | 纯软件、无 FPGA/硬件时序；本阶段只保留**时序/预算类可观察断言**（准入队列上限、超时路径、`Retry-After`），**不发布 SLO/容量结论**。功耗/容量压测（FD 泄漏、30min 耐久、50 并发）不在本方案分母内；原 `llmtier-test-plan`（已退役）的 ST-18/19/21 容量项现按 §4 Gap 由运维/性能专项承接（tailoring）。 |
| endurance | 裁剪 | 长稳/耐久另立专项，不在本方案分母内（tailoring）；见 §4 容量/耐久 Gap。 |

> 上表与 §3 清单交叉核对：normal 50 + boundary 7 + negative 45 + concurrency 6 + recovery 17 + security 15 = **140**。未列入的任何 STD 家族分类在本阶段**不适用**（见 §4 裁决）。



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
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001、VRC-INF-002 | DP-EMB-01 | normal | P0 | 基本 embedding | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-02 | normal | P0 | base64 编码 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-002 | DP-EMB-03 | normal | P1 | 不变量（同输入 ×5） | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-04 | negative | P0 | unknown model | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-002 | DP-EMB-05 | boundary | P2 | batch 33 不强制上限 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-06 | negative | P1 | dimensions 与冻结空间不符 | 已设计 | — |
| 系统设计 §8 Embeddings 接口（POST /v1/embeddings） | VRC-INF-001 | DP-EMB-07 | negative | P2 | 非法 encoding_format | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-01 | normal | P0 | 时间窗查询 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-02 | normal | P1 | 请求后可见记录 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-03 | boundary | P1 | cursor 分页 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-04 | negative | P2 | 过期 cursor | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-05 | negative | P1 | 缺 from/to | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-06 | normal | P1 | 主体隔离：data 只见自身，admin 见全局 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-07 | boundary | P1 | 分页重放幂等 | 已设计 | — |
| 系统设计 §8 Usage 查询接口（GET /v1/usage） | VRC-MGMT-006 | DP-USAGE-08 | recovery | P1 | store 不可用不返回空页 | 已设计 | — |
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
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ADM-PROBE-01 | negative | P0 | 探测缺确认 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ADM-PROBE-02 | normal | P1 | 探测带确认 | 已设计 | — |
| 系统设计 §8 探测接口（POST /v1/probes） | VRC-DIAG-004 | ADM-PROBE-03 | negative | P1 | 探测未知 deployment | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-INF-004 | ADM-RUNTIME-01 | normal | P1 | 运行时快照 | 已设计 | — |
| 系统设计 §8 运行态接口（GET /v1/runtime） | VRC-INF-004 | ADM-RUNTIME-02 | security | P1 | 运行时快照负向（角色） | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-01 | normal | P1 | 统计聚合 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-02 | normal | P2 | 分组 | 已设计 | — |
| 系统设计 §8 统计接口（GET /v1/stats） | VRC-MGMT-006 | ADM-STATS-03 | negative | P1 | 缺时间窗 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ADM-AUDIT-01 | security | P0 | 审计事件 + 脱敏 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-006 | ADM-AUDIT-02 | boundary | P1 | 审计分页 | 已设计 | — |
| 系统设计 §8 审计接口（GET /v1/audit） | VRC-MGMT-003 | ADM-AUDIT-03 | negative | P1 | 审计非法分页参数 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ADM-LOGS-01 | security | P0 | 脱敏日志 | 已设计 | — |
| 系统设计 §8 日志接口（GET /v1/logs） | VRC-LOG-001 | ADM-LOGS-02 | negative | P1 | 缺时间窗 | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ADM-USAGE-01 | normal | P1 | 管理面 usage | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ADM-USAGE-02 | boundary | P1 | 管理面分页 | 已设计 | — |
| 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） | VRC-MGMT-006 | ADM-USAGE-03 | normal | P1 | 清空 usage（admin + 审计） | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | OBS-DIAG-01 | normal | P1 | 读取诊断开关 | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | OBS-DIAG-02 | normal | P1 | 更新诊断开关 | 已设计 | — |
| 系统设计 §8 诊断开关接口（/v1/diagnostics） | VRC-DIAG-001 | OBS-DIAG-03 | negative | P2 | 开关更新非法值 | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | OBS-SNAP-01 | normal | P1 | 快照页（脱敏） | 已设计 | — |
| 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） | VRC-DIAG-002 | OBS-SNAP-02 | recovery | P2 | 快照无效 cursor | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | OBS-STATS-01 | normal | P1 | 诊断统计窗口 | 已设计 | — |
| 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） | VRC-DIAG-002 | OBS-STATS-02 | negative | P1 | 统计缺 since/until | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | OBS-TRACE-01 | normal | P1 | trace 列表去重 | 已设计 | — |
| 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） | VRC-DIAG-002 | OBS-TRACE-02 | recovery | P2 | trace 列表分页/游标 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-01 | normal | P0 | 读取 deployment 注入配置 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-02 | normal | P0 | 写入故障注入 | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-03 | negative | P1 | 注入未知 deployment | 已设计 | — |
| 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） | VRC-DIAG-004 | OBS-DEPL-04 | negative | P1 | 非法注入项 | 已设计 | — |
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

**Case 总数：140**（分类：normal 50 / boundary 7 / negative 45 / concurrency 6 / recovery 17 / security 15；环境 A 89 / B 51；Priority P0 45 / P1 72 / P2 23）。本表是**唯一权威 Case 清单**：一行一个 Case；逐 Case 的输入/执行/Oracle/判定/证据/清理见 `tests.system-case` 文档（`cases/<lowercased-case-id>.md`），本方案不展开。

**设计验证项覆盖**：本清单 `设计验证项 ID` 取自各 Case 的 `tests.system-case` 文档所声明的设计验证项（`DP-RESP-16`/`DP-RESP-23` 两 Case 的 case 文档未声明，按系统设计 §7.8 错误目录 `ERR-REQ-JSON`→`VRC-INF-001`、`ERR-PROVIDER-FAIL`→`VRC-INF-003` 反查补全；未新增任何 VRC ID）。设计文档（系统设计 §7/§8/§14、机制 §15、模块设计 §14、ISD §9.1）共声明 **33 个设计验证项**；本清单覆盖 **14 个**，**19 个无 Case**（清单见 §4 缺口裁决）。逐项覆盖数：`VRC-INF-001` 30、`VRC-MGMT-006` 19、`VRC-MGMT-001` 18、`VRC-MGMT-002` 17、`VRC-API-002` 12、`VRC-DIAG-002` 12、`VRC-DIAG-004` 12、`VRC-MGMT-003` 8、`VRC-INF-002` 5、`VRC-DIAG-001` 4、`VRC-INF-004` 4、`VRC-LOG-001` 2、`VRC-UTIL-001` 2、`VRC-INF-003` 1。



## 4. 不适用与缺口裁决

<span style="color:#1f6feb"><em>**本节目的**：区分“不适用”与“尚未设计”。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：Tailored-N/A 必须引用设计章节事实；Gap 须有 Owner 与恢复条件；两者都不从分母静默消失。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每条裁决有事实或 Owner；无“顺手 N/A”。</em></span>

| 来源 ID / 事实依据 | 裁决（Tailored-N/A 或 Gap） | Owner / 恢复条件 |
|---|---|---|
| **子系统测试级别** | Tailored-N/A | 本项目**无 `design.subsystem` 设计文档**：LLMTier 是纯软件系统，软件系统设计（`llmtier-system-design`）直接展开为模块（M001/M003/M004/M005/M006/M007 等），不存在软件子系统对象。故不采用 `tests.subsystem-test-scheme`；系统层方案直接承接系统设计 §7/§8 与机制端到端的测试分母。若将来引入 `design.subsystem`，本裁决须重新评审并补建子系统方案。 |
| 验收活动 | Tailored-N/A（不在 tests 家族） | 客户/项目验收与 release 放行授权**不属于 tests 家族**（STD 模板选择规则：验收按项目 tailoring 承接）。本方案不承载验收判定；`Gate` 只给放行建议，不等于验收或上线授权。 |
| 真实生产环境（TLS 反向代理、生产 SSO/MFA、浏览器无 bearer、HttpOnly/CSRF） | Gap | Owner：运维/安全。恢复条件：生产部署面可用并有授权后补测；当前由安全评估与运维手册承接，非系统测试分母。 |
| 上游模型答案质量与推理正确性 | Gap | Owner：模型/推理。恢复条件：定义独立内容 Oracle 与统计口径后另立评测；本方案只断言结构/事件序列/字段契约，不把模型内容当 Oracle。 |
| 容量/耐久（FD 泄漏、30min 耐久、50 并发） | Gap | Owner：性能/运维。恢复条件：另立性能/运维专项执行容量测试（原退役 `llmtier-test-plan` 的 ST-18/19/21 内容）；结果不合并进本方案分母。 |
| 进程 crash/restart 后的运维恢复、备份/恢复演练 | Gap | Owner：运维。恢复条件：运维手册 `m5air-operations-manual.md` §14/§15 承接。 |
| `ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`/`ERR-UTIL-TXN` 的 envelope code | Gap（具名缺口，4 项） | Owner：M007/规格。恢复条件：`/readyz` 503 body 为 `ReadinessView` 而非 `ErrorEnvelope`（无 `code`）；其余需破坏性构造（symlink DB、嵌套事务）从 HTTP 无法无破坏触发。`ERR-BOOT` 的表现层由 HEALTH-04/05 覆盖，envelope code 保留具名缺口。 |
| 非受信来源的真实"缺凭据" 401 | Gap | Owner：代码 owner（`src/http_api/auth.py`）。恢复条件：当前实现对 loopback/RFC1918 无 `Authorization` 头**无条件**授予共享角色，无法从 A/B 受信网段制造真实缺凭据 401；AUTH-10 改以非法授权方案触发。若引入显式 env 门控须重新评审。 |
| 设计验证项 `VRC-INF-005`（观测 fail-open / 不二次校验，M003；系统设计 §7.4） | Gap（无 Case） | Owner：M003 推理/规格。恢复条件：需系统层可观察的 fail-open 断言；当前系统 Case 只锁事件序列/terminal 契约（`VRC-INF-002`），未覆盖"观测失败不阻断、不二次校验"语义，归 M003 模块测试设计承接。 |
| 设计验证项 `VRC-UTIL-002`（事务/初始化/拒绝，M004；系统设计 §7.7、`ERR-PATH-UNSAFE`） | Gap（无 Case） | Owner：M004 存储/规格。恢复条件：事务回滚、schema 不匹配/损坏、路径不安全等需破坏性构造（symlink DB、嵌套事务），非 HTTP 可达；HEALTH-04/05 仅覆盖 schema 引导表现层，事务/拒绝语义归 M004 模块测试设计承接。 |
| 设计验证项 `VRC-API-001/003/004`（M001 分发/错误、body/SSE、静态与健康） | Gap（模块级，无 Case） | Owner：M001 http-api。恢复条件：模块级验证项（分发路由/错误信封/body 解析/SSE 单帧/静态交付）；系统层 Case 以端点契约（`VRC-INF-001`/`VRC-API-002`）间接覆盖其表现，未逐项登记，归 M001 模块测试设计承接。 |
| 设计验证项 `VRC-MGMT-004/005`（M005 分页与清空、探测） | Gap（模块级，无 Case） | Owner：M005 管理。恢复条件：`query_snapshots` 分页/清空、`/v1/probes` 探测语义；系统层 Case（`DP-USAGE-*`/`ADM-USAGE-*`/`ADM-PROBE-*`）归入 `VRC-MGMT-006`/`VRC-DIAG-004`，未逐项登记，归 M005 模块测试设计承接。 |
| 设计验证项 `VRC-DIAG-003`（M007 libdiag fail-open） | Gap（模块级，无 Case） | Owner：M007 诊断。恢复条件：诊断记录失败不阻断业务（fail-open）；系统层未构造该失败路径，归 M007 模块测试设计承接。 |
| 设计验证项 `VRC-OBS-001..005`（M006 observability：开关/查询脱敏/注入/关联标识/诊断页） | Gap（模块级，无 Case） | Owner：M006 观测。恢复条件：审计/日志/诊断观测语义；系统层 `OBS-*` Case 登记为 `VRC-DIAG-*`/`VRC-MGMT-*`，未按 M006 验证项逐项登记，归 M006 模块测试设计承接。 |
| 设计验证项 `VRC-UI-001..006`（M002 web-ui：加载/编辑鉴权/Pause/用量未知/探测确认/诊断页） | Gap（模块级，无 Case） | Owner：M002 web-ui。恢复条件：浏览器端静态资源与交互契约不在系统测试分母（无 HTTP 端点 Case）；web-ui 模块设计已声明其验证方法，待模块测试设计承接。 |



## 5. 文档联动与清单变更规则

<span style="color:#1f6feb"><em>**本节目的**：固定方案—用例—计划的联动规则，防三处漂移。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：新 Case 先入本清单再建 case-design 文档（文档 ID＝Case ID）；清单变更须同步计划构成表；写明方案冻结/版本规则。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：清单与 case-design 文档一一对应；计划只引用不复制。</em></span>

- **方案冻结与变更规则**：Case 清单随系统设计基线**冻结**；系统设计或机制变更导致分母变化时，本方案升版并同步 `tests.system-test-plan` 的构成表。Case ID 一经登记**不复用、不改名**；新增 Case 取同家族下一个未占用序号（含补丁后缀，如 `ADM-SL-02b`）；废弃 Case 标 `superseded`，不删除、不重编号。
- **与 case-design / 计划的同步规则**：**新 Case 先入本清单 §3，再建 case-design 文档**；case-design 文档路径固定为 `docs/70_verification/specifications/cases/<lowercased-case-id>.md`（例：`DP-RESP-01` → `cases/dp-resp-01.md`），文档 ID = Case ID；`tests.system-test-plan` 只引用本方案版本，不复制 Case 清单。本方案只登记 Case **设计状态**（Designed/Gap/Tailored-N/A），不承载实现状态（在 case-design 文档）与执行状态/Verdict（只在 Run 报告）。
- **本方案的退役与吸收映射**：本方案**唯一吸收并取代**旧 `assurance.test-specification` 家族的 `llmtier-api-test-specification`（140-Case 权威清单、定量覆盖模型、Traceability、环境与共同机制）与 `llmtier-contract-test-specification`（静态契约 `CT-*` 的 runtime 落地边界）。二者已从 `docs/70_verification/specifications/` 退役（git rm）；其 Case ID 与数量（140）**保持不变**，逐 Case 细节现由 `tests.system-case` 文档承载。
- **需求到本方案的可追溯入口**：本方案各 Case 家族的可追溯链维持 `LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case（原规格 §3.6 的映射表已随 source 文档退役；追迹数据由逐 Case 设计文档与 Run manifest 的 `target_artifact` 共同锁定）。

### 未决项与歧义记录（本方案自记录）

> 以下为实施本方案时发现的 STD 读数歧义；本方案按"采取 STD 读数并显式登记"处理，未静默猜测。列出以提请 STD 维护者裁决。

1. **Case ID 命名语法**：模板 §3 示例使用 `SYS-<对象>-<NNN>` 语法，且"必须写清楚"要求 Case ID 稳定唯一（`SYS-<对象>-<NNN>`）。本方案沿用 LLMTier 既有 140 个 Case ID（`HEALTH-*`/`DP-*`/`ADM-*`/`OBS-*`/`AUTH-*`），与模板语法不一致。**采取读数**：任务明确要求 Case ID 保持不变（140）；Case ID 的"稳定且唯一"是本质要求，前缀族名形式由项目既有惯例决定。**歧义**：模板是否强制 `SYS-` 前缀，或仅为示例，待 STD 裁决。
2. **"未决项章节"**：任务要求"在方案的未决项章节记录歧义"，但 `tests.system-test-scheme` 模板**没有**未决项章节（正文仅 §1–§5，另有附录 A）。**采取读数**：遵守"匹配模板精确章节集、不得自创章节"，将未决项作为 §5 内的具名小节记录，而非新增顶层章节。
3. **`来源 ID` 粒度**：模板要求"一个来源 ID 至少一条记录"。原规格以 route×method×role×error-code 为覆盖分母，未给"来源 ID"独立编号。**采取读数**：按系统设计 §8 接口/机制分组作为来源 ID（如"系统设计 §8 Responses 接口"），一个来源对应多条 Case；不新造记录编号。
4. **`design_level` 取值**：`new-design` 对 `tests.system-test-scheme` 未在层级映射中登记，生成默认 `cross-level`；STD 指南称系统方案"对应 design.software-system（系统设计阶段）"。**采取读数**：metadata 置 `design_level=system`、`domain=[software]`（与系统层语义一致）；`validate-design` 不对此强制，故为语义读数而非工具强制。
5. **（已关闭）逐 Case 设计文档的入站链接（跨任务移交）**：原记录为"140 份 `tests.system-case` 文档仍指向已退役的 `../llmtier-api-test-specification.md`，重写前 `validate-design docs` 会报告 `link.missing`"。**关闭事实**：并行工作项已完成 case 文档重写——全部 141 份 case 文档（140 Case + README）**均不再**引用任何退役规格（0 处），且全部以真实路径引用本方案（`llmtier-system-test-scheme.md`）；`validate-design docs` 不再报告该类 `link.missing`。本条歧义已消解，保留以存档。

## 附录 A. 本层设计验证项 VRC 汇集（对照用）

<span style="color:#1f6feb"><em>**本节目的**：把设计文档声明的本层验证项 VRC 汇集于此，供逐项对照 §3 清单的覆盖。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：VRC 清单以设计文档（design §12/§14）为唯一权威，本附录只登记 ID 与要验证什么，不复制判据/Oracle 定义；设计变更时本附录同步；每个 VRC 必须在 §3 清单有至少一个 Case，否则登记缺口。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：本附录 VRC 集合与设计文档一致；每个 VRC 在 §3 清单有 Case 或缺口。</em></span>

**本层 VRC 集合（33 项）**：`VRC-API-001`、`VRC-API-002`、`VRC-API-003`、`VRC-API-004`、`VRC-INF-001`、`VRC-INF-002`、`VRC-INF-003`、`VRC-INF-004`、`VRC-INF-005`、`VRC-MGMT-001`、`VRC-MGMT-002`、`VRC-MGMT-003`、`VRC-MGMT-004`、`VRC-MGMT-005`、`VRC-MGMT-006`、`VRC-DIAG-001`、`VRC-DIAG-002`、`VRC-DIAG-003`、`VRC-DIAG-004`、`VRC-LOG-001`、`VRC-OBS-001..005`、`VRC-UI-001..006`、`VRC-UTIL-001`、`VRC-UTIL-002`。来源＝各 Case `tests.system-case` 文档所声明者（`DP-RESP-16`/`DP-RESP-23` 按系统设计 §7.8 错误目录反查补全）。

| 设计验证项 ID | 要验证什么（名称/责任） | 设计来源 | §3 Case 覆盖 |
|---|---|---|---|
| `VRC-API-002` | HTTP 入口/鉴权/序列化与健康表现 | 系统设计 §12 | HEALTH-01..06、AUTH-01..10、ADM-RUNTIME-02、OBS-REQTRACE-03 |
| `VRC-MGMT-003` | 就绪/审计/未配置鉴权语义 | 系统设计 §12 | HEALTH-02..05、ADM-AUDIT-01/03、AUTH-07 |
| `VRC-MGMT-006` | 用量/统计/分页口径 | 系统设计 §12 | DP-USAGE-01..08、ADM-PROV-USAGE-*、ADM-STATS-*、ADM-USAGE-*、ADM-AUDIT-02 |
| `VRC-MGMT-001` | Provider/Deployment 管理语义 | 系统设计 §12 | ADM-PROV-01..14、ADM-PROV-MODELS-01/02、ADM-DEPL-01/03/05/06/07/08 |
| `VRC-MGMT-002` | 更新/并发/ETag 与 Service Level 语义 | 系统设计 §12 | ADM-PROV-05..07/09/13、ADM-DEPL-04/09、ADM-SL-01..08 |
| `VRC-INF-001` | 推理/模型/嵌入路由与请求契约 | 系统设计 §12 | DP-MODELS-01..07、DP-RESP-01..25、DP-EMB-* |
| `VRC-INF-002` | 推理输出/能力集结构契约 | 系统设计 §12 | DP-MODELS-01/07、DP-EMB-03/05 |
| `VRC-INF-003` | 上游非 5xx → provider_error | 系统设计 §12 | DP-RESP-23 |
| `VRC-INF-004` | 准入饱和/候选健康/运行时快照 | 系统设计 §12 | DP-RESP-19/20、ADM-RUNTIME-01 |
| `VRC-DIAG-001` | 诊断开关读写 | 系统设计 §12 | OBS-DIAG-01..03、OBS-ALIAS-01 |
| `VRC-DIAG-002` | 诊断快照/统计/trace/请求追踪 | 系统设计 §12 | OBS-SNAP-*、OBS-STATS-*、OBS-TRACE-*、OBS-REQTRACE-01/02、OBS-ALIAS-02..06 |
| `VRC-DIAG-004` | 故障注入配置与探测 | 系统设计 §12 | DP-RESP-11/22、ADM-PROV-USAGE-02/03、ADM-PROBE-01..03、OBS-DEPL-01..04、OBS-ALIAS-04 |
| `VRC-LOG-001` | 日志/审计脱敏 | 系统设计 §12 | ADM-LOGS-01/02 |
| `VRC-UTIL-001` | 存储引导/就绪引导表现 | 系统设计 §12 | HEALTH-04/05 |
| `VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`、`VRC-UI-001..006` | 模块级/表现层验证项（无系统层 Case） | 系统设计 §12/§14、机制 §15、模块设计 §14、ISD §9.1 | 见 §4 缺口裁决（Gap） |



<!-- 交付自查：每个适用来源 ID 是否都有 Case 或具名缺口；清单里的每个 Case ID 是否都有（或计划有）对应 case-design 文档；方案里是否混入了输入构造或 Oracle 细节？ -->
