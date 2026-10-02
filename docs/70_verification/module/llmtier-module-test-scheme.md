<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Module Test Scheme

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-module-test-scheme` |
| Document Version | `0.1.0-draft.7` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-test-scheme` |
| Template Version | `0.6.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/llmtier-module-test-scheme.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本方案绑定软件模块集合：本方案覆盖 8 个软件模块 `M001-M008`（见 §1）；`design_object_id` 为本项目元数据可选字段，本方案 metadata 未写入该字段（合并方案跨 8 模块，单一 `design_object_id` 无法承载），模块归属改由 §3「来源 ID / 固定版本」列与 Case ID 前缀承担；模块/ISD 基线在 §1.5 固定；实现状态与执行结果不进本方案。
> 本文档对设计验证项（VRC）的引用规则：只引用 ID 与状态，不复制定义/判据/Owner；判据与契约权威归 design 与 tests.asset-design，本文档若细化执行断言需在变更时回溯设计修订并记录。**VRC 在本层只作追溯列/附 A，不作分母**（见 §3）。
> **裁剪说明（tailored）**：模板默认“本方案绑定单一软件模块”。本项目按用户授权将 8 个模块的模块层 Case 清单合并为一份项目级方案（`M001-M008` 一次登记），逐模块归属由 §3 的「来源 ID / 固定版本」列与 Case ID 前缀承担；该合并只关清单登记位置，不改变 Case 与模块设计分支/接口的追溯。裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md) `LT-TL-025`。

### 模板定位：方案、用例与计划的边界

- **权威分工**：模块层测试的 Case 清单（ID、分类、优先级、责任摘要、设计状态）以本方案为唯一登记处；单 Case 展开归 `tests.module-case`（一 Case 一文档）；活动组织归 `tests.module-test-plan`。
- **只有摘要**：本方案每条 Case 只写责任摘要（要测什么），不写输入构造、Oracle 或步骤。
- **下层 PASS 不关闭本层**；本层 PASS 不关闭上层组合目标。

### 状态语义：用例状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 用例状态 | `Designed` / `Gap`（具名缺口）/ `Tailored-N/A` | 本方案 §3 清单 | 未设计写成已设计；N/A 无设计事实依据 |

任一 Case 在本方案中只报设计状态；实现与执行状态可沿 Case ID 追到 case-design 文档与 Run 报告。

## 1. 目标、范围与被测对象

- 被测对象、设计基线与父对象：LLMTier 8 个软件模块——M001 `http-api`（`src/http_api/`）、M002 `web-ui`（`src/web_ui/`）、M003 `inference`（`src/inference/`）、M004 `management`（`src/management/`）、M005 `observability`（`src/observability/`）、M006 `libdiag`（`src/libdiag/`）、M007 `util`（`src/util/`）、M008 `log`（`src/log/`）；父对象为软件系统设计 `llmtier-system-design`；模块/ISD 基线见 §1.5。**M005 `src/observability/` 无独立实现文件**（仅空 `__init__.py`），其模块行为落在 M001 `app.py` 的诊断路由与 M006 `diagnostics.py` 查询面（见 M005 设计 §3/§4；本方案 §3 的 M005 行据此归属）。
- **本层定位＝灰盒（gray-box），主要手段＝公开入口 + 边界替身**（对齐 STD [test-standard.md](https://github.com/corezilla/STD/blob/eaca6dcb9ca990bfb9b68ae1c08dfb5d9d4b5da9/docs/test-standard.md) §3）：模块层经**公开入口**驱动（HTTP 端点 / 服务方法 / `Store` 公开方法——这是黑盒刺激），但被测模块**内部单元真实**，且**允许并鼓励断言模块内部分支、内部状态与内部调用序**（白盒观测）。**边界替身**只在模块边界以外注入（上游 provider 用进程内 `FakeAdapter`；真实网络端口仅绑 loopback 测试实例 `127.0.0.1:0`）；**不测**跨模块协议与边界外真实依赖（归系统层 `ST-*`）。这与单元层的区别不在“测不测内部”，而在：
  - **单元层**逐函数/逐类验证单函数分支（mock 协作者），命令入口是函数调用；
  - **模块层**验证**组装后**才成立的保证——同一公开刺激下，内部真实单元之间的**分支走向、状态迁移与有序接线**是否与设计一致，以及**UT 各自 PASS 但组装后可能不成立**的分支/组合/接线点（见 §3 与 §5 去重规则）。
- **灰盒边界（可断言 seam vs 不耦合的实现细节）**：**可断言的内部 seam**＝模块内公开类型/方法（如 `Router.admit` 上下文、`UsageRecorder` 账本行、`Registry` 版本号、`DiagnosticsService` 开关列、`Store` 连接 PRAGMA）与**模块内序列**（先鉴权后分发、先 `admit` 后 dispatch、审计与业务同事务、路由→服务→存储）；**不耦合的实现细节**＝私有函数名、变量名、SQL 文本、日志措辞、内部数据结构的偶发形状——这些不作为断言对象。断言优先“模块公开返回/wire 信封/落库行 + 关键内部 seam 的状态/调用序”。
- **内部真实、仅边界替身**：模块内部全部真实（真实 `Store` + 隔离临时库、真实 `Registry`/`Router`/`UsageRecorder`/`AuditLog`/`OperationalLog`/`DiagnosticsService`、真实 `ThreadingHTTPServer` handler 栈、真实 `webui/` 静态产物），**禁止**对被测模块内部单元或内部字段打桩；仅模块**边界以外**的协作者使用替身（上游 provider 用进程内 `FakeAdapter`，真实网络端口仅绑 loopback 测试实例 `127.0.0.1:0`）。
- **状态型初态必须经公开入口构造**：凡构造模块初态（造数据、造开关、造用量、造审计、造诊断样本、造注入、造配置）**必须调用被测模块公开入口**（HTTP 端点 / 服务方法 / `Store` 公开方法）；**禁止**测试直写表、直改内部字段或实例属性来建立初态（见 §1.5 规则 1）。
- 不证明的组合保证及承接入口：跨模块系统级流程（启动/systemd、反向代理、Piko 联调）、wire 互操作与 OpenAPI 端到端一致性、真实上游 provider 协议、浏览器 E2E；承接＝系统测试方案/计划（`llmtier-system-test-scheme`/`-plan`）与契约层。**下层（单元）PASS 不关闭本层**，**本层 PASS 不关闭上层**。
- 被测入口集合（每个 Case 的具体入口见对应 module-case §2）：M001 `app.py` `Handler` 对外 HTTP 端点 + `errors.py`/`auth.py`/`sse.py`/`health.py`；M002 `webui/index.html` + `webui/app.js` 对外 DOM/API 契约；M003 `ResponsesService.create`/`EmbeddingsService.create` + `Router.admit` + `UsageRecorder.*`；M004 `Registry.*`/`AdminService.*`/`AccountUsage.refresh`；M005 诊断端点（经 M001 `app.py` 路由）；M006 `DiagnosticsService.*`；M007 `Store.*`；M008 `OperationalLog.record/page`。

## 1.5 测试方法与测试设计技术

- **模块/ISD 基线**：M001 `http-api` v0.1.0-draft.2 / ISD `http-api-isd`；M002 `web-ui` v0.1.0-draft.2 / `web-ui-isd`；M003 `inference` v0.1.0-draft.1 / `inference-isd`；M004 `management` v0.1.0-draft.3 / `management-isd`；M005 `observability` v0.1.0-draft.6 / `observability-isd`；M006 `libdiag` v0.1.0-draft.6 / `libdiag-isd`；M007 `util` v0.1.0-draft.2 / `util-isd`；M008 `log` v0.1.0-draft.1 / `log-isd`。设计要求见各模块设计 §14 与 ISD §9.1。
- **模块层专属规则（强制）**：
  1. **状态只经公开入口**——凡构造模块初态必须调用被测模块公开入口（HTTP 端点 / 服务方法 / `Store` 公开方法）；**禁止**测试直接写表、直改内部字段或实例属性来建立初态。
  2. **内部真实、边界替身**——模块内部协作者一律真实实例；只有模块边界以外（真实上游 provider、真实网络对端）可替换为替身，且替身交互契约以 `tests.asset-design` 为唯一 authority。
  3. **组装保证优先**——一个模块层 Case 必须断言**组装后**才成立的保证（分支走向、状态迁移、调用链顺序、跨单元失败传播、模块间接口契约），不得退化为单元层已覆盖的单函数行为复测（UT 去重见 §5）。
  4. **分支/组合/迁移必覆盖**——§3 列出的每个模块内**判定分支**、每条**组合行**与**状态迁移**都必须映射到 ≥1 个 Case；未覆盖者须在 §4 具名或标 `Tailored-N/A`（依据设计事实），不得静默消失。
- **入场标准**：模块设计 §14 与 ISD §9.1 到位；本方案 §3 分母（接口行为 + 分支 + 组合/迁移 + 组装边界）冻结、无未登记缺口；对应 module-case 文档已建且其测试代码 `Implemented`；边界替身契约在 `tests.asset-design` 就位且自检 Verified；ENV（§1.7）就绪。
- **离场标准**：§3 四层分母每层每条至少一个 Case 已判定；全部 Case Verdict 齐全；缺口有具名 Owner 与恢复条件（§4）；模块设计或 ISD 变更触发受影响 Case 重跑。
- **自动化策略**：`PYTHONPATH=src python3 -m pytest tests/module/cases -q` 进 CI，整批运行；单 Case 用其文档 §7 的 `-k`/文件路径入口选择；失败不阻断后续 Case（除环境性 BLOCKED）；flaky 不掩盖根因（INVALID 单独登记复现状态）。

### 模块层专门测试技术（选型与设计）

模块层在等价类/边界/错误猜测之上，**必须**使用以下四类以覆盖“组装后才成立”的保证；每类给出分母并在 §3 逐条映射到 Case：

1. **分支 / 条件覆盖（branch/condition coverage）**：把模块内每一处**判定分支**列为一条，**每个分支至少一条 Case**，给出分支分母并要求全覆盖。模块内判定分支（清单见 §3.2）：M001 鉴权三态（401/403/503）、`_auth_either` 优先级、SSE terminal 三态（completed/aborted-by-client/aborted-by-error）、路由命中/未命中、`_body` 413/非法 JSON/非法 Content-Length、`_static` 穿越/未命中、`_run` 500/503 出口；M003 校验顺序四出口、准入四出口（404/429 队列满/503 全不健康/429 超时）、注入四态、admitted 真/假副作用分支；M004 bootstrap 五出口、CRUD 412/409-conflict/409-in-use/404、分页 cursor 四态、refresh 四态；M006 注入六类 × 校验出口、fail-open 三分支、stream_wrapper 三态；M007 migrate 四拒绝出口、事务嵌套 409；M008 脱敏命中/未命中 × `page` 400/夹取。
2. **组合（判定表 / 配对 pairwise）**：对**相互独立**的判定做组合，用**判定表**列出行，用 **pairwise** 削减全组合规模；给组合矩阵并说明选组合的理由。组合行清单见 §3.3：M001 鉴权结果 × 端点类别、SSE body 形态 × 终止界定、分页 cursor 状态 × 越界；M003 注入类型 × 准入阶段、能力档 × 请求形态；M004 资源类别 × 错误码、账号用量 provider × 凭据 × 确认；M006 注入类型 × config 合法性、游标状态 × 查询面。
3. **状态转换覆盖（state-transition coverage）**：模块内状态机每条**迁移**至少一条 Case，给迁移表。迁移清单见 §3.4：M003 账本 `unknown→final`、Router 槽位持有→释放、队列 push→pop/超时；M004 bootstrap 空→就绪/失败回滚、资源版本 vN→vN+1；M005/M006 开关 off↔on（关闭零写入）；M007 库 空→初始化→迁移→关闭/回滚；M008 日志追加顺序。
4. **调用序 / 接线断言（ordering & wiring）**：跨内部单元/模块接口断言**有序调用与次数**——先 `_auth` 后 `_dispatch`、先 `Router.admit` 后 dispatch、审计与业务**同事务**、路由→服务→存储路径、诊断 trace stage 有序、幂等（重复启动/bootstrap no-op、重复 revoke）。
5. **等价类 / 边界 / 错误猜测 / 故障注入 / 并发**：**保留但重定位为灰盒**——注入与观测均经公开入口与内部 seam，断言组装后的分支与状态，而非单函数返回值。

| Case 家族 | 测试设计技术 | 环境类型引用 | 自动化与判定规则 |
|---|---|---|---|
| normal | 组装后真实调用 + 等价类划分 + 分支覆盖 | ENV-1 组装隔离库；M002 用 ENV-2 loopback HTTP | CI 跑全集；断言模块公开返回/wire 信封/落库行**与内部 seam 状态**严格相等 |
| | · 注入：固定 request、固定 tier/deployment、固定 fixture（`AppFixture.seed` 经公开入口）；命名分支的命中路径 | | · 主路径一次判定 PASS/FAIL；分支命中方可判定 |
| boundary | 边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界 | ENV-1 组装隔离库；ENV-2 | 单 Case `-k`；边界在「接受」与「拒绝」间二选一，覆盖邻近一步 |
| | · 注入：body 2 MB、`limit` 上限、message 512、`max_output_tokens` 上下界、cursor 过期 | | · 超界→既定错误码，无第三态 |
| negative | 错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合 | ENV-1 组装隔离库；ENV-2 | 每错误分支独立断言错误码/类型 + 组装路径；一次性判定 |
| | · 注入：未知 model、缺字段、非布尔开关、删除被引用、非法 cursor、越权端点、pairwise 组合行 | | · 失败不掩盖 |
| concurrency | 线程对偶 + 受控时序（`threading`/`ThreadingHTTPServer`）+ 调用序断言 | ENV-1 + ENV-2 | 固定确定性交错；断言占用/释放与 FIFO 序；失败记录交错样本 |
| | · 注入：并发 PATCH（ETag/412）、同等级 FIFO、并发启动两实例 | | · 失败须留并发样本 |
| recovery | 故障注入 + 异常路径恢复（`LLMTIER_SLOW_ADAPTER_DELAY`/写失败/断开）+ 状态回滚断言 | ENV-1 组装隔离库；ENV-3 上游 fake | 异常路径后断言回滚/无半写/unknown 不补零/推理不变/账本状态 |
| | · 注入：边界替身返回上游 5xx/超时/断连/配额耗尽/坏数据/畸形流、库写失败、客户端断开、迁移中途失败、诊断写入失败 | | · fail-open 与回滚逐项断言 |
| security | 鉴权/脱敏/注入边界冒烟（Bearer/LAN 信任、`[REDACTED]`、目录穿越）+ 分支×端点配对 | ENV-1 + ENV-2 | 上游/系统层已覆盖，本层仅冒烟 + 组装分支 |
| | · 注入：错误/缺失 Bearer、data 访问 admin、日志含 Authorization/Secret、`../` 路径 | | · 断言状态码与脱敏文本 |
| performance | 不在本层 | 性能预算归系统层 | 不用负载/容量测试（本层不负责系统预算） |
| endurance | 不在本层 | 耐久/长稳归系统层 | 不用长跑（本层不负责） |

### 注入类方法（错误/故障注入 + 数据注入）

> **本节目的**：把模块层**注入类方法**（means）固定下来——注入是**跨家族应用的构造/刺激手段**（不新增 Case 家族、不单独设 Case），其落点映射到 §3 四层分母的既有行（family 加/recovery/negative/security + 分支/组合/迁移分母）。
> **主要手段＝边界替身（mock/fake）返回错误数据/行为**：模块层的错误注入**以边界替身为主**——由 `FakeAdapter`（进程内 fake）**返回坏数据或产生错误行为**（bad data / quota exhausted / timeout / disconnect / malformed stream），断言模块对该错误的**映射与处理**（分支走向、错误码、状态回滚）。**产品 diagnostics 注入（`fault_502`/`fault_503`/`delay`/`rate_limit`/`stream_terminate`/`malformed_event`）是可选补充**：仅当产品注入能力可用时才作为额外手段，**不是基线**；产品注入未命中（或能力不可用）**不使基线 Case 失效**——基线由边界替身保证。
> **完成条件**：本节每个「mock 返回类型」与数据注入类型均映射到 ≥1 个 §3 行（见「方法 → Case 落点」表）；**用边界替身返回错误时，判定＝模块对该错误的映射**（命中即以替身确实返回了配置错误为准）；**用产品注入时未命中即判 `INVALID`**（不得以“重试即恢复”掩盖根因）。

#### 错误 / 故障注入（按「边界替身返回什么」组织；产品注入为可选补充）

| mock 返回（主手段）| 边界替身返回的错误数据/行为 | 产品注入（可选补充）| 落点（§3 分母行 → Case） |
|---|---|---|---|
| **5xx（上游错误响应）** | `FakeAdapter`/`FakeResponse` 返回 500/502/503 或抛对应 `ApiError` | `fault_502`/`fault_503` | MT-INF-003（recovery）、MT-INF-008（注入四态 recovery） |
| **超时** | `FakeAdapter` 挂起 > 连接/流空闲超时（或本地 stub 不返回） | `delay` | MT-INF-003（recovery）、MT-INF-008（recovery） |
| **断连** | `FakeAdapter` 抛 `URLError`/`OSError`/`HTTPException`（连接中断） | — | MT-INF-003（recovery）、MT-INF-011（fail-open recovery） |
| **配额/额度耗尽（quota exhausted）** | mock 返回上游 **4xx（429/402/403）配额耗尽**错误体 | `rate_limit`（近似 429，仅产品注入可用时） | **MT-INF-012（recovery）** |
| **坏数据（契约违规：非 SS 帧·坏向量·非法 base64）** | mock 返回非 SSE 体 / 非法 base64 / 非有限向量 / 非法维数 | — | MT-INF-010（boundary）、MT-INF-002（boundary） |
| **畸形流（非法 SSE 事件/多 terminal/坏帧）** | mock 返回不合法 SSE 块或多 terminal / 非 JSON 帧 | `malformed_event`/`stream_terminate` | MT-DIAG-005（boundary）、MT-INF-003（recovery） |

- **存储面 / 传输面 / 准入面（非上游替身返回值）**：存储面（库写失败/表损坏/迁移中途失败）与传输面（客户端中途断开/超大流）不经上游替身，直接在真实 `Store`/ENV-2 真实 socket 上触发；准入面（队列饱和/全不健康/等待超时）经 `Router` 公开 `admit` 上下文或（可选）`rate_limit`+`delay` 产品注入制造。落点：MT-INF-009/MT-DIAG-007/MT-OBS-004/MT-UTIL-004/MT-UTIL-005（存储面 recovery）、MT-API-008/MT-API-007（传输面 recovery/boundary）、MT-INF-007/MT-INF-004/K4（准入面 concurrency/组合）。
- **判定规则（强制）**：**用边界替身注入**——替身按配置返回了错误即视为「命中」，判定＝模块对该错误的**映射/处理**（错误码、分支走向、回滚、`unknown` 不补零）；**用产品注入**——**注入命中（命中计数 > 0）方可判定**，注入计数为 0、并发未交错、故障未实际触发 → 该 Case 记 `INVALID`（不记 PASS）；**不得用“重试即恢复”掩盖根因**——须断言注入发生后的分支走向、状态回滚/无半写、`unknown` 不补零与调用序，而非仅“再次调用成功”。

#### 数据注入（data injection，按数据类型与用途）

> **初态/边界数据经公开入口构造（+ 可选 mock）**：初态数据与边界数据**必须经被测模块公开入口**构造（HTTP 端点 / 服务方法 / `Store` 公开方法；`AppFixture.seed`），**边界替身（mock）只作可选补充**去近似边界来源（如本地 `FakeResponse` 返回边界响应体）——**禁止**测试直写表/直改内部字段。

| 数据类型 / 用途 | 注入内容 | 手段（公开入口 ① / 边界替身 ②） | 落点（§3 分母行 → Case） |
|---|---|---|---|
| **① 初态数据** | 固定 tier/deployment/账本/snapshot/injection 行 | ① **经公开入口播种**（HTTP 端点 / 服务方法 / `Store` 公开方法；`AppFixture.seed`）——**禁止直接写表** | 一切需初态的 Case 的**公开入口前置**（§1.5 规则 1）；代表行 MT-MGMT-001/006、MT-INF-003/004、MT-DIAG-004、MT-OBS-002 |
| **② 边界数据** | 2 MB body、`limit` 上限、512 字符、极值/空/未知 | ① 公开请求参数/正文；边界由模块公开入口构造 | MT-API-007（413 boundary）、MT-MGMT-009（cursor/limit boundary）、MT-LOG-001/003（512/limit 夹取 boundary）、K3/K5 |
| **③ 诊断数据注入** | deployment 级注入配置 | ① `PATCH /v1/deployments/{id}/diagnostics`（诊断注入 API，≥1 项） | MT-DIAG-002（注入配置 negative）、MT-DIAG-003/004（注入校验/撤销 negative）、MT-OBS-004（注入分支 recovery）、K4/K8 |
| **④ 冻结向量** | SSE 字节帧、32-hex `traceparent`、base64 向量、UI 资产字符串 | ① 固定 request/header；② 本地 `FakeAdapter`/`FakeResponse` 只代返回值 | MT-API-008（SSE 帧 recovery）、MT-API-010（traceparent 分支 normal）、MT-INF-002/010（base64 向量 boundary）、MT-UI-001/002（UI 资产字符串契约）、K2/K10 |

- **判定规则（强制）**：数据注入的注入值/观测**严格相等**（wire 信封、落库行、内部 seam 状态逐字段比对）；**未知值不补零**（`unknown` / `Unknown` / NULL 落库，绝不以 0 代替）；初态注入**必须经公开入口**（`Store` 公开方法或 HTTP/服务方法），**禁止**测试直写表/直改内部字段。

#### 1.5.1 异常 / 错误注入矩阵（全量封闭：每个对外 error code、上游 4xx/5xx/配额/坏数据/凭据、传输/时间病态）

> **本矩阵目的**：把「异常 / 错误」按**来源**穷举为三组，并把每一行**唯一地**映射到「mock 如何注入 → 被测模块应映射为（code/status，per CODE in `src/`）→ MT case」。**Oracle ＝ `src/` 实际实现**（`src/http_api/errors.py` 的信封 + 各模块 `ApiError(...)` 调用点），**系统设计 §7.8 错误目录为对照**；若二者不一致，以 `src/` 为准并在 §4 登记 design-vs-code 缺口。
> **封闭判据**：本矩阵 = (a) 对外 error code 全集 ∪ (b) 上游异常类别 ∪ (c) 传输/时间病态。**每一行必须映射到 ≥1 个 `MT-*` case 或一个具名 Gap**（既有 case 命中或本变更新增 case 均可）；**0 静默缺失**。§3.7 增设「异常/错误注入矩阵 → Case 核对块」与本节同口径。

**（a）每个对外 error code（Oracle ＝ `src/`；逐一登记，不接受“某类已覆盖”的合并）**

| # | `code`（Oracle `src/`） | 应映射 status（`src/`） | mock/注入如何触发 | 映射 MT case |
|---|---|---|---|---|
| a1 | `invalid_request` | 400 | 缺字段/非法 Content-Length/非法布尔/`max_output_tokens` 越界/`provider_id` 变更/缺 `from`-`to` | MT-API-007 / MT-INF-005 / MT-MGMT-007 |
| a2 | `unsupported_request` | 400 | `stream!=true`/`store!=false`/带 tools 但能力不支持 | MT-INF-005 / MT-INF-006 |
| a3 | `unsupported_field` | 400 | 禁字段（`prompt_cache_key` 等）/未知字段 | MT-INF-005 |
| a4 | `unsupported_model` | 400 | 等级 `capabilities.responses/embeddings=false` | MT-INF-006 |
| a5 | `invalid_json` | 400 | body 非 JSON / JSON 非对象 | MT-API-007 |
| a6 | `request_too_large` | 413 | Content-Length > 2 MB | MT-API-007 |
| a7 | `unsupported_dimensions` | 400 | `dimensions` 不在冻结能力集 | MT-INF-010 |
| a8 | `authentication_required` | 401 | 受保护端点无 Bearer | MT-API-006 |
| a9 | `permission_denied` | 403 | data 凭据访问 admin 端点 / 跨 principal cursor | MT-API-006 / MT-MGMT-009 |
| a10 | `auth_not_configured` | 503 | 鉴权配置缺失且访问受保护端点 | MT-API-006 |
| a11 | `model_not_found` | 404 | 请求 tier 不存在 | MT-INF-007 |
| a12 | `not_found` | 404 | 未知路由 / 未知资源 ID / 静态未命中 | MT-API-004 / MT-MGMT-007 |
| a13 | `resource_conflict` | 409 | 唯一名重复（provider/deployment/tier） | MT-MGMT-007 |
| a14 | `capability_conflict` | 409 | 成员能力集不一致 / Inference Tier 无 responses | MT-MGMT-008 |
| a15 | `embedding_space_conflict` | 409 | `Embedding-v1` 非 embedding-only / 空间或限额不符冻结契约 | MT-MGMT-008 |
| a16 | `fixed_service_level` | 409 | 删除固定 tier（固定 service level） | **MT-MGMT-011（新增）** |
| a17 | `resource_in_use` | 409 | 删除被引用的 provider/deployment | MT-MGMT-007 |
| a18 | `version_conflict` | 412 | `If-Match` ETag 过期 | MT-MGMT-007 |
| a19 | `cursor_expired` | 400 | 非法/过期/跨 principal cursor | MT-MGMT-009 / MT-DIAG-006 |
| a20 | `rate_limit_exceeded` | 429 | 队列满（`Retry-After:30`）/排队超时（`Retry-After:1`）/注入 `rate_limit` | MT-INF-007 / MT-INF-008 / MT-INF-018 |
| a21 | `provider_unavailable` | 503 | 上游 5xx / 建连·首字节·流空闲超时 / 抛连异常 | MT-INF-003 / MT-INF-008 / MT-INF-013 / MT-INF-014 |
| a22 | `provider_error` | 上游码（4xx/5xx） | 上游 HTTP 非成功（`exc.code`），`408/429` retryable | MT-INF-012 |
| a23 | `provider_failure` | 502 | 诊断注入 `fault_502` | MT-INF-008 |
| a24 | `provider_secret_unavailable` | 503 | `secret_ref` 为 `env:` 无值 / `file:` 不可读 / 非法引用 | **MT-INF-019（新增）** |
| a25 | `provider_contract_error` | 502 | 非 SSE / 多 terminal / 无合法 terminal / terminal 与 status 矛盾 / 非法 base64·向量 / 截断流 / 畸形帧 | MT-INF-010 / MT-DIAG-005 / MT-INF-016 / MT-INF-017 |
| a26 | `model_unavailable` | 503 | 全部候选不健康/禁用 | MT-INF-007 |
| a27 | `usage_store_unavailable` | 503 | SQLite 读/写异常（经 `_store_read`/`_run`） | MT-API-005 / MT-OBS-003（诊断查询面复用同 code，见 §4 O-OBS-STORECODE-1） |
| a28 | `internal_error` | 500 | 未捕获异常 | MT-API-005 |
| a29 | `bootstrap_required` | 503 | 空库无 settings | MT-MGMT-001 |
| a30 | `bootstrap_invalid` | 503 | settings 缺节 / `env:` 空 / `file:` 不存在 / 事务失败 | MT-MGMT-001 / MT-MGMT-006 |
| a31 | `schema_version_mismatch` | 503 | 库 schema 版本与代码不匹配 | MT-UTIL-004 |
| a32 | `schema_unknown` | 503 | 有表但无 `schema_meta` | MT-UTIL-004 |
| a33 | `schema_integrity_failed` | 503 | `PRAGMA integrity_check` 失败 | MT-UTIL-004 |
| a34 | `store_path_unsafe` | 503 | DB 路径为 symlink | MT-UTIL-003 |
| a35 | `E-UTIL-NESTED-TXN` | 409 | 同一连接重复开启事务 | MT-UTIL-005 |
| a36 | `invalid_injection` | 400 | 注入类型/字段/范围非法 | MT-DIAG-003 |
| a37 | `confirmation_required` | 400 | 探测/账号用量刷新缺 `confirm_external_call` | MT-MGMT-004 / MT-MGMT-010 |

**（a）计数：37 个对外 code**（Oracle `src/`）；**35 个已有 case 命中，2 个新增 case 补口（a16 `fixed_service_level` → MT-MGMT-011；a24 `provider_secret_unavailable` → MT-INF-019）**，**0 未映射**。

**（b）上游异常类别（边界替身返回；产品注入为可选补充）**

| # | 上游异常 | mock 如何注入 | 被测模块应映射为（code/status，per `src/`） | 映射 MT case |
|---|---|---|---|---|
| b1 | 上游 4xx（非配额） | `FakeResponse`/`FakeAdapter` 返回 400/404/422 | 沿用上游码 + `code=provider_error`，`retryable=false` | MT-INF-012 |
| b2 | 上游 5xx | `FakeAdapter` 返回 500/502/503 | `503 provider_unavailable`（`retryable=true`） | MT-INF-003 / MT-INF-008 |
| b3 | 配额/额度耗尽（429/402/403） | mock 返回 429/402/403 配额错误体 | 沿用上游码 + `code=provider_error`；429→`retryable=true`，402/403→`false` | MT-INF-012 |
| b4 | 非 JSON 响应 | mock 返回非 JSON body | `502 provider_contract_error`（解析失败） | MT-INF-017 |
| b5 | 坏数据·非 SS 帧 | mock 返回 `Content-Type` 非 `text/event-stream` | `502 provider_contract_error` | MT-DIAG-005 / MT-INF-016 |
| b6 | 坏数据·坏向量/非法维数 | mock 返回非有限值/维度不符向量 | `502 provider_contract_error` + 拒绝 | MT-INF-010 |
| b7 | 坏数据·非法 base64 | mock 返回不可解码 base64 | `502 provider_contract_error` | MT-INF-010 |
| b8 | 凭据缺失（`env:`/`file:`/非法引用） | `secret_ref` 指向空 `env:` / 不可读 `file:` / 未知 scheme | `503 provider_secret_unavailable` | MT-INF-019 |

**（b）计数：8 类**；**全部映射到 ≥1 case（b4/b8 由新增 MT-INF-017/019 补口）**，0 未映射。

**（c）传输 / 时间病态（真实 socket / 真实 `Store` / `Router` 公开 `admit`）**

| # | 传输/时间病态 | mock/环境如何注入 | 被测模块应映射为（code/status/终态，per `src/`） | 映射 MT case |
|---|---|---|---|---|
| c1 | **stall/hang**（上游建连成功但永不响应） | ENV-2 真实 socket 上游 accept 后不回字节；`connect_timeout_ms`/`stream_idle_timeout_ms` 置小 | `503 provider_unavailable`（`retryable=true`），账本 `unknown` 收敛、Router 许可释放 | **MT-INF-013（新增）** |
| c2 | **slow-response timeout**（慢速 trickle 超过流空闲超时） | 上游分片慢发，片间隔 > `stream_idle_timeout_ms` | `503 provider_unavailable`；无半写账本、许可释放 | **MT-INF-014（新增）** |
| c3 | **超长/超大 response** | 上游返回超大 body / 极长 SSE 单帧或超多事件 | 模块在自身边界内完整归一（不越界崩溃）；超 2 MB **下游响应**由系统层预算承接 | **MT-INF-015（新增）** |
| c4 | **broken pipe / client disconnect mid-stream** | ENV-2 真实客户端读首帧后 `close()`（SSE 已开始） | SSE terminal `aborted(client disconnected)`；无 500、无 fd 泄漏、账本不变 | **MT-API-012（新增）** |
| c5 | **connection reset (RST)** | ENV-2 客户端 `SO_LINGER 0` 后 `close()` 触发 RST | 同 c4：`aborted`，进程不崩溃、许可/fd 释放 | **MT-API-013（新增）** |
| c6 | **truncated stream / early EOF**（上游在 terminal 前关流） | mock 流在最后一个 terminal 事件前 `EOF` | `502 provider_contract_error`（无合法 terminal） | **MT-INF-016（新增）** |
| c7 | **malformed frame**（非 JSON `data:` 行 / 坏 SSE 块） | mock 返回 `data: {not json}` 或坏块 | `502 provider_contract_error` | **MT-INF-017（新增）** |
| c8 | **concurrency timeout + permit leak** | `Router.admit` 队列等待超 `30 s`（受控时钟/小预算） | `429 rate_limit_exceeded` + `Retry-After`；`_inflight` 归零、无许可泄漏 | **MT-INF-018（新增）** |

**（c）计数：8 类**；**全部映射到 ≥1 新增 case（c1–c8 → MT-INF-013…018 / MT-API-012/013）**，0 未映射。
> **真实 socket 说明**：c1/c2/c3/c6/c7 以**进程内 fake / 真实 provider 实例（loopback 临时端口）**为刺激源；c4/c5 属**客户端侧病态**，必须在 ENV-2 `ThreadingHTTPServer` 的**真实 socket** 上用真实客户端中途断开/RST（不能用进程内对象模拟，否则不触发 `BrokenPipeError`/`ConnectionResetError`）。

**（a)/(b)/(c) 汇总计数：37 + 8 + 8 = 53 条异常/错误项**；新增 **10 个 `MT-*` case**（MT-MGMT-011、MT-INF-013…019、MT-API-012…013）承接其中 20 条（a16/a24、b4/b8、c1–c8），其余 33 条由既有 case 承接。**0 静默缺失。**

#### 方法 → Case 落点说明

- 本节的**注入类方法**是**跨家族应用的构造与刺激手段**，不新增 Case 家族、不单独设 Case：按上面的「落点」列映射到 §3 的既有行——**family 加/recovery/negative/security** 表行（§1.5 家族表）+ **分支**（§3.2）/ **组合**（§3.3，K1–K10）/ **迁移**（§3.4，T1–T14）分母。
- **主/补充手段口径**：错误注入**以边界替身返回错误数据/行为为主手段**（5xx/超时/断连/配额耗尽/坏数据/畸形流六类），**产品 diagnostics 注入为可选补充**；同一落点可由主手段独立成立，产品注入可用时叠加验证。
- 覆盖核对：上两表每个「mock 返回类型」/注入面/数据类型均映射到 ≥1 个 §3 行；§3.7 新增「注入面/数据类型 → Case」核对块，与分支/组合/迁移核对同口径，**0 未映射**。

### 测试设计技术选型表（按 Case 家族）

| Case 家族 | 选用的设计技术 | 选用理由 | 不选用的反模式 |
|---|---|---|---|
| normal | 组装后真实调用 + 等价类划分 + 分支覆盖 | 覆盖合法输入空间与主路径分支，验证组装主路径 | 不用全部输入矩阵（规模爆炸） |
| boundary | 边界值（上限/零/空/刚好满/长度）+ 条件边界 | 边界是缺陷高发区，验证边界与邻近一步 | 不用随机/模糊测试（不可复现） |
| negative | 错误猜测 + 反例驱动 + 判定表组合 | 异常路径以设计已识别反例为准，组合用 pairwise | 不用模糊异常注入（无 oracle/无归因） |
| concurrency | 线程对偶 + 确定性交错 + 调用序断言 | 状态机驱动，固定时序控制，验证占用/释放 | 不用随机并发（不可复现 + flaky） |
| recovery | 故障注入 + 异常路径回滚 + 状态迁移断言 | 资源归还与回滚基线需在失败路径覆盖 | 不用"重试"模拟恢复（掩盖根因） |
| security | 鉴权/脱敏/注入冒烟 + 契约 + 分支×端点配对 | 上游/系统层已覆盖，本层仅冒烟 + 组装分支 | 不用模糊安全测试（不可复现 + 上游责任） |
| performance | 不在本层 | 性能预算归系统层 | 不用负载/容量测试（本层不负责系统预算） |
| endurance | 不在本层 | 耐久/长稳归系统层 | 不用长跑（本层不负责） |

## 1.6 替身使用策略与边界

- **决策准则**：按所有权/可控性/真实性分类——模块内部协作者（`Store`、`Registry`、`Router`、`UsageRecorder`、`AuditLog`、`OperationalLog`、`DiagnosticsService`、`sse`、`auth`、`health`）**全部真实**；只有模块边界以外、不属于被测模块且不可控的对象（真实上游 provider、真实网络对端）才用替身。
- **替身形态**：`FakeAdapter` 为进程内 fake（只代返回值/异常/终态，定义于 `tests/common/fakes.py`）；`FakeResponse` 为各测试模块**本地**定义的 HTTP 响应 stub（用于 account-usage HTTP 与 OpenAI SSE 响应），非共享资产成员；不用 mock 框架打桩被测自身。
- **替身保真度与契约**：替身契约与自检归 `tests.asset-design`（一资产一文档），本方案与 Case 只引用其 ID 不复制行为。**资产实例已建立**：`llmtier-unit-fakes`（`docs/70_verification/unit/assets/llmtier-unit-fakes.md`，覆盖 `FakeAdapter`/`AppFixture`，候选 ID `FAKE-LLMTIER-ADAPTER`）。模块层**复用**该资产（同一进程内 fake 与组装夹具），不另立重复资产；`FakeResponse` 在该资产 §2/§3 已声明为各模块本地 stub、非本资产成员。§3 各 Case 只引用该文档 ID。
- **交互断言 vs 返回值断言**：优先断言模块公开返回值、wire 信封、落库行；**模块层允许并鼓励**断言**模块内公开 seam 的状态与模块间接口的调用序/次数**（如先 `_auth` 后 `_dispatch`、先 `Router.admit` 后 dispatch、审计与业务同事务、路由→服务→存储），但**不耦合**私有函数名、变量名、SQL 文本、日志措辞等实现细节。
- **反模式（逐项排除）**：不 mock 被测拥有的接口；不 mock 值对象/纯数据（dict/JSON 直接构造）；不为凑覆盖率而 mock；不过度断言内部实现细节；不直改被测内部字段建立初态（见 §1.5 规则 1）。

| 协作者类型 | 替身形态 | 替身契约文档（tests.asset-design） | 决策理由 |
|---|---|---|---|
| 上游 provider adapter（模块边界外） | 进程内 fake（`FakeAdapter`） | `llmtier-unit-fakes`（`docs/70_verification/unit/assets/llmtier-unit-fakes.md`） | 真实 provider 不可控；fake 只代返回值/异常/终态 |
| provider HTTP 响应（account-usage / OpenAI SSE） | 本地 stub（各测试模块自定义 `FakeResponse`） | `llmtier-unit-fakes` §2/§3（声明 `FakeResponse` 为各模块本地 stub、非本资产成员） | 代 HTTP 响应体；非 `probe(models)` |
| SQLite 存储与全部模块内部协作者 | 真实实现（不替身） | 不适用（真实依赖） | 被模块组装的一部分，用真实实现 + 密隔离 |
| HTTP 监听端口 | 真实 `ThreadingHTTPServer`（`127.0.0.1:0`） | 不适用（真实网络） | 端口是真实路径，仅绑 loopback 临时端口 |
| Web UI 静态产物 | 真实文件读取（`Path.read_text`） | 不适用（真实产物） | UI 契约对真实 `index.html`/`app.js` 断言 |

## 1.7 测试环境类型（方案定义）

| 环境类型 | 行为/真伪 | 契约文档 | 在本层用例中的角色 |
|---|---|---|---|
| ENV-1 组装隔离库 | 真实：`tempfile.TemporaryDirectory` + `Application`（`Store`+`Registry`+全部内部服务真实组装）；每 Case 新建、`tearDown` 销毁 | — | 绝大多数模块 Case 的默认环境（`tests/common/fakes.py::AppFixture`） |
| | · 契约：真实 SQLite 落库；`settings.json` 经公开引导入口写入；不复用跨 Case 状态 | | · 用法：`setUp` 建 `AppFixture`、`tearDown` `close()` |
| ENV-2 loopback 组装 HTTP 实例 | 真实：`ThreadingHTTPServer((127.0.0.1, 0), handler_factory(app))`，完整 handler 栈 | — | 模块对外 HTTP/wire 契约 Case（路由、鉴权、SSE、静态、诊断、别名） |
| | · 契约：真实 socket、临时端口、真实组装栈；不代被测 `app.py` 逻辑 | | · 用法：`setUpClass` 起服务、`tearDownClass` shutdown |
| ENV-3 provider 进程内 fake | fake：`FakeAdapter` 只代返回值/异常/终态 | `llmtier-unit-fakes` | 上游交互/失败注入 Case |
| | · 契约：`complete`/`embed`/`probe` 返回可配置结果；不证明真实 provider 协议 | | · 用法：`ResponsesService(..., adapter=FakeAdapter(...))` |
| ENV-4 确定性注入 | 真实：经公开入口配置 `LLMTIER_SLOW_ADAPTER_DELAY` 或诊断注入（`set_injections`）产生确定故障/延迟 | `llmtier-unit-fakes`（组装夹具） | 失败传播/恢复 Case 的确定性故障源 |

**总体说明**：Python 3.14（`python3 -m pytest`），`PYTHONPATH=src`；组装夹具来源为 `tests/common/fakes.py`（`AppFixture`/`FakeAdapter`）；替身资产契约见 `llmtier-unit-fakes`（`docs/70_verification/unit/assets/`，`Implemented`/`Unverified`）；CI 入口为 `PYTHONPATH=src python3 -m pytest tests/module/cases -q`（或按 `-k` 选单 Case）；并行隔离按临时库实例 + loopback 随机端口；缺 Python/依赖记 Blocked，不静默换环境。

## 2. 测试分类体系

| 分类（STD 家族词表） | 本阶段适用性 | 裁剪依据 |
|---|---|---|
| normal | 适用 | 组装后主路径（模块设计 §14 正常场景） |
| boundary | 适用 | 容量/长度/分页/时间窗边界（模块设计 §14 边界场景） |
| negative | 适用 | 非法字段/凭据/引用/类型/顺序（模块设计 §14 失败场景） |
| concurrency | 适用 | 并发 PATCH、同等级 FIFO、并发启动（模块设计 §8/§14 事实） |
| recovery | 适用 | fail-open、写入失败、迁移回滚、断开（模块设计 §14 事实） |
| security | 适用（冒烟） | 鉴权/脱敏/目录穿越属模块可测点；深层安全归系统层 |
| performance | 不在本层 | 性能预算归系统测试方案 |
| endurance | 不在本层 | 耐久/长稳归系统层 |

## 3. 覆盖分母与 Case 清单

> 来源 ID 与设计验证项（VRC）的边界：本表登记 ID+责任摘要；判据/Oracle/Owner/契约权威归 design 与 tests.asset-design，不在此行复写；变更设计时同步 VRC 同步本清单。
> **分母不再是“一行一 VRC”**：VRC 在本层**只作追溯列与附 A**（见 §3.5 与附录 A），**不作分母**。本层分母为**四层**，逐层计数并在 §3.6 汇总：
> - **① 对外接口端到端行为**（模块设计 §9 对外接口的组装后行为）——§3.1；
> - **② 内部分支**（每个判定分支 1 Case）——§3.2；
> - **③ 组合 / 状态转换**（判定表/迁移表的行）——§3.3 / §3.4；
> - **④ 组装边界替身注入**（边界替身注入并断言命中计数）——§3.1/§3.2 中的边界 Case。
> 分母来源为被测源码的判定分支、判定表与状态迁移（可核验于 `src/<module>/`），非复制 VRC 判据。**来源 ID 读法**：来源 ID 指向被测模块/模块组装本体——「模块设计 §14 验证项 / 组装入口（分支/组合/迁移）」，固定版本随模块行首标注。**版本以 §1.5「模块/ISD 基线」为准**；下表行末版本标签为清单登记时点的模块设计版本标签。
> **用例归属（本项目合并方案的补充列）**：M001→`MT-API-*`；M002→`MT-UI-*`；M003→`MT-INF-*`；M004→`MT-MGMT-*`；M005→`MT-OBS-*`；M006→`MT-DIAG-*`；M007→`MT-UTIL-*`；M008→`MT-LOG-*`（token 与单元方案一致，便于反查映射）。
> **模块层责任**：每条 Case 的责任摘要限定为**组装后**才成立的保证（分支走向/状态迁移/调用序），单元层已覆盖且组装不改判的单函数分支不在本层重复登记（UT 去重见 §5）。

### 3.1 层①对外接口端到端行为（接口行为分母）

> 分母＝模块设计 §9 对外接口在**组装后**的端到端行为，每条至少 1 Case。本层是“黑盒刺激 + 灰盒观测”的基线。

| 来源 ID / 固定版本 | 追溯 VRC | Case ID | 分类 | 优先级 | 责任摘要（要测什么） | 设计状态 | 上级组合验证入口 |
|---|---|---|---|---|---|---|---|
| M001 http-api §9 · `Handler._dispatch` 路由分发（组装） v0.1.0-draft.2 | VRC-API-001 | MT-API-001 | normal | P0 | 组装后路由分发端到端：请求经 handler 栈命中端点、统一错误信封（`X-Request-ID`、`error.type`）与健康/就绪视图一致 | Designed | 系统测试 |
| M001 http-api §9 · 契约别名 `/tier/admin/v1/*`（组装） v0.1.0-draft.2 | VRC-API-001 | MT-API-002 | normal | P1 | 组装后别名与 `/v1/*` 端到端 parity（同一资源视图/ETag），路由→服务→存储路径一致 | Designed | 系统测试 |
| M001 http-api §9 · 静态与健康就绪（组装） v0.1.0-draft.2 | VRC-API-004 | MT-API-003 | security | P1 | 组装后静态交付：真实 `webui/` 资源、`/ui/`→`index.html`、空库 `/readyz`→503、`/healthz` 可达 | Designed | 系统测试 |
| M002 web-ui §9 · 页面装载（组装静态产物） v0.1.0-draft.2 | VRC-UI-001 | MT-UI-001 | normal | P1 | 组装后 5 页装载与 tier/成员状态语义映射（Unknown≠Idle、Disabled 优先、空态）、`readyz` 映射、单一数据源 | Designed | 系统测试 |
| M002 web-ui §9 · 编辑/暂停/探测/用量/诊断契约（组装） v0.1.0-draft.2 | VRC-UI-002/003/004/005/006 | MT-UI-002 | normal | P0 | 组装后 UI API 契约：编辑 412/409、Pause 确认边界、探测确认、用量 Unknown 呈现、诊断 4 tabs 契约与 `app.js` 接线一致 | Designed | 系统测试 |
| M003 inference §9 · `ResponsesService.create`（组装） v0.1.0-draft.1 | VRC-INF-001 | MT-INF-001 | normal | P0 | 组装后推理契约：校验→路由→适配→终态全链，事件子集对照 OpenAPI、恰好一个 terminal | Designed | 契约层 / 系统测试 |
| M003 inference §9 · `EmbeddingsService.create`（组装） v0.1.0-draft.1 | VRC-INF-002 | MT-INF-002 | boundary | P0 | 组装后向量化：正常/base64、非有限值、非法维数、usage→`prompt_tokens`，`Embedding-v1` 约束 | Designed | 契约层 / 系统测试 |
| M003 inference §9 · `UsageRecorder` 账本（组装） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-003 | recovery | P0 | 组装后失败与用量：上游 5xx/超时、usage 缺失→unknown 不补零、账本终态单调推进 | Designed | M-METER / 系统测试 |
| M003 inference §9 · `Router.admit`/`models`（组装） v0.1.0-draft.1 | VRC-INF-004 | MT-INF-004 | concurrency | P0 | 组装后准入与目录：占满队列 429、全不健康 503、同等级 FIFO、availability 三态、许可释放 | Designed | M001 / 系统测试 |
| M004 management §9 · `Registry.bootstrap_settings`（组装） v0.1.0-draft.3 | VRC-MGMT-001 | MT-MGMT-001 | normal | P0 | 组装后引导：合法 settings、重复启动 no-op、空库无 settings→503 `bootstrap_required`、缺节/`env:` 空/`file:` 不存在→503 `bootstrap_invalid` 回滚 + not_ready | Designed | 启动 / M001 |
| M004 management §9 · `Registry` CRUD（组装） v0.1.0-draft.3 | VRC-MGMT-002 | MT-MGMT-002 | negative | P0 | 组装后 CRUD 不变量：ETag stale 412、删除被引用、能力冲突、`Embedding-v1` 冻结、审计同事务 | Designed | M003 / 契约层 |
| M004 management §9 · `Admin.page`/`reset_usage`（组装） v0.1.0-draft.3 | VRC-MGMT-004 | MT-MGMT-003 | boundary | P0 | 组装后分页与清空：首屏后更正旧页冻结、cursor 过期/跨 principal→400/403、范围清空计数一致 | Designed | M-METER / 系统测试 |
| M004 management §9 · `Admin.probe`（组装） v0.1.0-draft.3 | VRC-MGMT-005 | MT-MGMT-004 | normal | P1 | 组装后探测：未确认 400、正常探测、不可达落 `unhealthy`、`may_have_incurred_cost` | Designed | M003 适配器 |
| M004 management §9 · `AccountUsage.refresh`（组装） v0.1.0-draft.3 | VRC-MGMT-006 | MT-MGMT-005 | negative | P1 | 组装后账号用量：GET 不触网、未确认 POST、凭据缺失、provider 报错→`unavailable`+`error` 快照持久 | Designed | M002 Providers 页 |
| M005 observability §9 · 诊断端点（组装） v0.1.0-draft.6 | VRC-OBS-001..005 | MT-OBS-001 | normal | P1 | 组装后诊断端到端：经 M001 路由 → M006 `DiagnosticsService`，开关/快照/统计/trace/时间窗全链生效 | Designed | M002 / M006 |
| M006 libdiag §9 · `DiagnosticsService` 记录与查询（组装） v0.1.0-draft.6 | VRC-DIAG-002 | MT-DIAG-001 | boundary | P1 | 组装后记录与查询：trace/快照/统计字段、URL 去 query、summary 截断、百分位、7 天清理 | Designed | M003 / M005 |
| M006 libdiag §9 · 注入配置（组装） v0.1.0-draft.6 | VRC-DIAG-004 | MT-DIAG-002 | negative | P0 | 组装后注入：六类注入、非法类型 400、命中确定、优先级、traces 时间窗分页 | Designed | M003 / M001 |
| M007 util §9 · `Store` 连接/PRAGMA/回收（组装） v0.1.0-draft.2 | VRC-UTIL-001 | MT-UTIL-001 | boundary | P0 | 组装后连接：`foreign_keys=1`/`wal`、每线程一连接、fd 基线稳定、close 异常、world-writable、symlink 拒绝 | Designed | M004 / M-METER / M-OBS |
| M007 util §9 · `transaction`/`migrate`（组装） v0.1.0-draft.2 | VRC-UTIL-002 | MT-UTIL-002 | recovery | P0 | 组装后事务与迁移：回滚无半写、幂等 `migrate`、损坏库/版本不匹配拒绝、嵌套事务 409、并发启动 | Designed | M004 / M-METER / M-OBS |
| M008 log §9 · `OperationalLog.record/page`（组装） v0.1.0-draft.1 | VRC-LOG-001 | MT-LOG-001 | security | P0 | 组装后脱敏与查询：Bearer/api_key/token 落库 `[REDACTED]`、长度 ≤512、倒序、过滤、`limit` 夹到 200、缺 `since`/`until`→400 | Designed | M004 / M002 |

**层①计数：20 条接口行为**（M001 3 / M002 2 / M003 4 / M004 5 / M005 1 / M006 2 / M007 2 / M008 1）。

### 3.2 层②内部分支（每分支 1 Case）

> 分母＝被测源码的判定分支（可核验于 `src/<module>/`）。**每个分支至少 1 Case**；同模块内分支可合并为一条 Case（多分支断言），但每个分支必须在 §3.7 分支分母表的“映射 Case”列被点名。

| 来源 ID（分支） / 固定版本 | 追溯 VRC | Case ID | 分类 | 优先级 | 责任摘要（要测什么） | 设计状态 |
|---|---|---|---|---|---|---|
| M001 `_dispatch` 路由命中/未命中 + 未知路由 404（组装） v0.1.0-draft.2 | VRC-API-001 | MT-API-004 | negative | P0 | 未命中端点→404 `not_found`（错误信封一致）；命中分支与未命中分支各断言 | Designed |
| M001 `_run` 错误出口：ApiError/sqlite3.Error/未知异常（组装） v0.1.0-draft.2 | VRC-API-001 | MT-API-005 | negative | P0 | 三出口分别断言：ApiError→既定码；`sqlite3.Error`→503 `usage_store_unavailable`；未知异常→500 `internal_error`（均落日志） | Designed |
| M001 `_auth` 三态 401/403/503 + `_auth_either` 优先级（组装） v0.1.0-draft.2 | VRC-API-002 | MT-API-006 | security | P0 | 缺失配置→503 `auth_not_configured`；无 Bearer→401；错误凭据→403；`_auth_either` admin-first 且 401 与 403 不泄露存在性 | Designed |
| M001 `_body` 分支：非法 Content-Length/413/非法 JSON/非对象（组装） v0.1.0-draft.2 | VRC-API-003 | MT-API-007 | boundary | P0 | 四出口分别断言 400 `invalid_request` / 413 `request_too_large` / 400 `invalid_json` ×2 | Designed |
| M001 SSE terminal 三态：completed/client-abort/error-abort（组装） v0.1.0-draft.2 | VRC-API-003 | MT-API-008 | recovery | P0 | 正常流→`completed` trace；客户端断开→`aborted(client disconnected)`；流异常→`aborted(stream_error)` 且落日志；created 首、terminal 唯一、`[DONE]` | Designed |
| M001 `_static` 分支：穿越 404/未命中 404/`/ui/`→index（组装） v0.1.0-draft.2 | VRC-API-004 | MT-API-009 | security | P1 | `../` 穿越→404；缺失文件→404；`/ui/`→`index.html`；三态分别断言 | Designed |
| M001 `_correlation` 分支：header/traceparent 命中/未命中/缺省（组装） v0.1.0-draft.2 | VRC-OBS-004 | MT-API-010 | normal | P1 | `X-Correlation-ID` 回显；`traceparent` 合法→提取 32-hex；非法→原样；皆缺→缺省 | Designed |
| M002 `dispatchUiError` 分支：401/403、409、412、429、503/default（组装契约） v0.1.0-draft.2 | VRC-UI-002 | MT-UI-003 | negative | P0 | 五分支：401/403 呈现；409 引用保留输入；412 stale 保留输入；429 `Retry-After`；503/default stale | Designed |
| M002 状态映射分支：`backendState`/`tierState` 的 Disabled/Unknown/Empty/Running/Idle（组装契约） v0.1.0-draft.2 | VRC-UI-001 | MT-UI-004 | normal | P1 | provider-disabled→Disabled 优先；availability 缺失→Unknown≠Idle；空 tier→Empty；healthy+running→Running/Idle | Designed |
| M002 `usageSummary` 分支：not_refreshed/unlimited/Unavailable/percent-null（组装契约） v0.1.0-draft.2 | VRC-UI-004 | MT-UI-005 | boundary | P1 | 四态渲染；Unknown≠0；版本替换去重；503 显式化不显示空表 | Designed |
| M002 `reportLoadFailure` 分支：已列举状态抑制 vs 未知状态 stale（组装契约） v0.1.0-draft.2 | VRC-UI-002 | MT-UI-006 | negative | P1 | 非列举状态（网络/500）经 `reportLoadFailure` 保留上一屏并标 stale；与 `dispatchUiError` 分工 | Designed |
| M003 校验顺序四出口：缺字段/unsupported_request/禁字段/未知字段（组装） v0.1.0-draft.1 | VRC-INF-001 | MT-INF-005 | negative | P0 | 按顺序分别断言 `invalid_request`/`unsupported_request`/`unsupported_field`(禁)/`unsupported_field`(未知)，`param` 指向违规字段 | Designed |
| M003 能力分支：responses=false / tools 无能力 / max_output_tokens 越界（组装） v0.1.0-draft.1 | VRC-INF-001 | MT-INF-006 | negative | P0 | `unsupported_model` / `unsupported_request`(tools) / `invalid_request`(max 范围/布尔) 三分支 | Designed |
| M003 准入四出口：404/429 队列满/503 全不健康/429 超时（组装） v0.1.0-draft.1 | VRC-INF-004 | MT-INF-007 | concurrency | P0 | 无候选→404；队列≥32→429 `Retry-After 30`；全不健康→503 `model_unavailable`；等待超时→429 `Retry-After 1` | Designed |
| M003 注入四态：fault_502/fault_503/rate_limit/delay/none（组装） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-008 | recovery | P0 | 502→`provider_failure`；503→`provider_unavailable`；rate_limit→429+`Retry-After`；delay→延迟；none→正常；均标 `piko_injected` | Designed |
| M003 admitted 真/假副作用分支（组装） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-009 | recovery | P0 | admitted=True 失败→`usage.finish(source=injected/none)`；admitted=False→无 usage 副作用（E-INF-ADMIT） | Designed |
| M003 `EmbeddingsService.create` 分支：base64/非有限值/非法维数/空（组装） v0.1.0-draft.1 | VRC-INF-002 | MT-INF-010 | boundary | P0 | 各分支分别断言：非法 base64→502 `provider_contract_error`；非有限值/非法维数/空向量拒绝；usage→`prompt_tokens` | Designed |
| M003 fail-open 分支：诊断写入失败/断开时推理不变（组装） v0.1.0-draft.1 | VRC-INF-005 | MT-INF-011 | recovery | P1 | 诊断抛错/断开时推理结果不变、不二次鉴权 | Designed |
| M003 上游非 5xx 错误分支：配额/额度耗尽（429/402/403）→ 沿用上游码 + `provider_error`（组装） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-012 | recovery | P1 | 边界替身（`FakeAdapter`/本地 `FakeResponse`）返回上游 **配额/额度耗尽** 4xx 错误体；断言模块按 `openai.py` 映射为**沿用上游码 + `code=provider_error`**（429→`retryable=true`，402/403→`retryable=false`），义务收敛 unknown 不补零，不跨等级 fallback | Designed |
| M004 bootstrap 五出口：no-op/required/invalid/`env:` 空/`file:` 缺失 + 回滚（组装） v0.1.0-draft.3 | VRC-MGMT-001 | MT-MGMT-006 | recovery | P0 | 五分支 + 中途失败回滚空库 + `ensure_fixed_tiers` 幂等 | Designed |
| M004 CRUD 错误分支：412/409-conflict/409-in-use/404/400 provider_id（组装） v0.1.0-draft.3 | VRC-MGMT-002 | MT-MGMT-007 | negative | P0 | ETag stale 412；UNIQUE 409 `resource_conflict`；删除被引用 409 `resource_in_use`；未知 404；deployment provider_id 变更 400 | Designed |
| M004 能力校验分支：capability_conflict/Embedding-v1 冻结/unknown deployment（组装） v0.1.0-draft.3 | VRC-MGMT-002 | MT-MGMT-008 | negative | P0 | 绑定能力不一致→409 `capability_conflict`；Embedding-v1 冻结空间/上限→409 `embedding_space_conflict`；未知 deployment→400 | Designed |
| M004 分页 cursor 四态：none/expired/cross-principal/filter-mismatch（组装） v0.1.0-draft.3 | VRC-MGMT-004 | MT-MGMT-009 | boundary | P0 | 无 cursor 首页；过期→400 `cursor_expired`；跨 principal→403；过滤不符→400；旧页冻结 | Designed |
| M004 account refresh 四态：no-network/confirm/credentials/provider-error（组装） v0.1.0-draft.3 | VRC-MGMT-006 | MT-MGMT-010 | negative | P1 | GET 不触网；未确认→400；凭据缺失→`unavailable`；provider 报错→`unavailable`+`error` 持久 | Designed |
| M005 开关分支：默认关/开/部分更新保留/关闭零写入（组装） v0.1.0-draft.6 | VRC-OBS-001 | MT-OBS-002 | normal | P1 | 经 M001 端点切换快照/统计开关，关闭时零写入，部分更新保留另一开关 | Designed |
| M005 查询分支：快照/统计字段 + 去 query + 存储不可读 503（组装） v0.1.0-draft.6 | VRC-OBS-002 | MT-OBS-003 | boundary | P1 | 字段完整、URL 去 query（`?token=` 不落库）、存储不可读→503 不伪装空页 | Designed |
| M005 注入分支：合法/非法 400/未知 deployment 404 + 观测写失败推理不变（组装） v0.1.0-draft.6 | VRC-OBS-003 | MT-OBS-004 | recovery | P1 | 合法注入命中；非法类型 400；未知 deployment 404；观测库写失败推理不变（fail-open） | Designed |
| M006 注入校验分支：未知类型/enabled 非布尔/config 非对象/缺字段/越界/error_body 空或超长（组装） v0.1.0-draft.6 | VRC-DIAG-004 | MT-DIAG-003 | negative | P0 | 六类判定分支分别断言 400 `invalid_injection`；error_body >512 截断；`malformed_event_type` 非法 400 | Designed |
| M006 `set_injections` 分支：非 list 400/未知 deployment 404/空 items revoke（组装） v0.1.0-draft.6 | VRC-DIAG-004 | MT-DIAG-004 | negative | P0 | 非 list→400；未知 deployment→404；`items:[]` 撤销全部注入（DELETE） | Designed |
| M006 `stream_wrapper` 三态：透传/早停/畸形帧（组装） v0.1.0-draft.6 | VRC-DIAG-004 | MT-DIAG-005 | boundary | P1 | 无注入→透传；`stream_terminate`→到点 return；`malformed_event`→到点发畸形帧并 return | Designed |
| M006 游标分支：traces/snapshots 非法 cursor→400（组装） v0.1.0-draft.6 | VRC-DIAG-002 | MT-DIAG-006 | boundary | P1 | 非法 cursor→400 `cursor_expired`；`next_cursor`/`has_more` 稳定；时间窗越界为空 | Designed |
| M006 fail-open 分支：record_trace/record_latency/capture_snapshot 写失败、cleanup 失败、init 失败（组装） v0.1.0-draft.6 | VRC-DIAG-003 | MT-DIAG-007 | recovery | P1 | 各写入失败不阻断推理；cleanup 失败返回 0；`_UnavailableDiagnostics` 降级 | Designed |
| M007 连接分支：symlink 503/world-writable/fd 基线/close 异常（组装） v0.1.0-draft.2 | VRC-UTIL-001 | MT-UTIL-003 | boundary | P0 | symlink→503 `store_path_unsafe`；world-writable 警告；多请求 fd 基线不泄漏；close 异常上抛 | Designed |
| M007 migrate 四拒绝出口：schema_unknown/版本不匹配/完整性失败 + 幂等（组装） v0.1.0-draft.2 | VRC-UTIL-002 | MT-UTIL-004 | recovery | P0 | 无 schema_meta 但有表→503 `schema_unknown`；版本不匹配→503；完整性失败→503 `schema_integrity_failed`；重复 `migrate` 幂等 | Designed |
| M007 事务分支：嵌套 409 + 迁移中途失败回滚（组装） v0.1.0-draft.2 | VRC-UTIL-002 | MT-UTIL-005 | recovery | P1 | 嵌套事务→409 `E-UTIL-NESTED-TXN`；迁移中途失败回滚为可启动空库 | Designed |
| M008 脱敏分支：五种敏感模式命中 + 未命中（组装） v0.1.0-draft.1 | VRC-LOG-001 | MT-LOG-002 | security | P0 | Bearer/api_key/token/authorization/secret 命中→`[REDACTED]`；普通文本不误伤；长度 ≤512 | Designed |
| M008 `page` 分支：缺 since/until→400 + limit 夹取 + 过滤（组装） v0.1.0-draft.1 | VRC-LOG-001 | MT-LOG-003 | negative | P1 | 缺参→400；`limit` 夹到 [1,200]；level/module/request_id 过滤；DESC 顺序 | Designed |
| M004 固定 tier 删除分支：固定 service level→409 `fixed_service_level`（组装） v0.1.0-draft.3 | VRC-MGMT-002 | MT-MGMT-011 | negative | P1 | 删除固定 tier（固定 service level）→409 `fixed_service_level`，资源不变；对照 `src/management/registry.py:379`（§1.5.1 a16） | Designed |
| M001 客户端中途断开分支：broken pipe / client disconnect mid-stream（组装，ENV-2 真实 socket） v0.1.0-draft.2 | VRC-API-003 | MT-API-012 | recovery | P0 | SSE 已开始后客户端 `close()`→`aborted(client disconnected)`；无 500、无 fd 泄漏、账本不变（§1.5.1 c4） | Designed |
| M001 连接重置分支：connection reset (RST) mid-stream（组装，ENV-2 真实 socket） v0.1.0-draft.2 | VRC-API-003 | MT-API-013 | recovery | P1 | 客户端 `SO_LINGER 0` 关闭触发 RST→`aborted`；进程不崩溃、许可/fd 释放（§1.5.1 c5） | Designed |
| M003 stall/hang 分支：上游建连成功但永不响应→超时（组装，ENV-3） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-013 | recovery | P0 | 上游 `accept` 后不回字节，`connect_timeout`/`stream_idle_timeout` 命中→503 `provider_unavailable`（retryable）；账本 `unknown` 收敛、Router 许可释放（§1.5.1 c1） | Designed |
| M003 slow-response 分支：慢速 trickle 超过流空闲超时（组装，ENV-3） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-014 | recovery | P1 | 上游分片慢发、片间隔 > `stream_idle_timeout_ms`→503 `provider_unavailable`；无半写账本、许可释放（§1.5.1 c2） | Designed |
| M003 超大 response 分支：超长/超大上游响应体归一（组装，ENV-3） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-015 | boundary | P1 | 超大 body / 极长 SSE 单帧 / 超多事件在模块边界内完整归一、不越界崩溃；超 2 MB 下游响应归系统层（§1.5.1 c3） | Designed |
| M003 截断流分支：terminal 前 early EOF→契约错误（组装，ENV-3） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-016 | recovery | P0 | 上游在最后一个 terminal 事件前 `EOF`→502 `provider_contract_error`（无合法 terminal）；账本收敛（§1.5.1 c6） | Designed |
| M003 畸形帧分支：非 JSON `data:` 行 / 坏 SSE 块（组装，ENV-3） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-017 | negative | P0 | `data: {not json}` 或坏块→502 `provider_contract_error`；不伪装成功（§1.5.1 c7） | Designed |
| M003 并发超时 + 许可泄漏分支：队列等待超时后许可归零（组装，ENV-1） v0.1.0-draft.1 | VRC-INF-004 | MT-INF-018 | concurrency | P1 | `Router.admit` 等待超 `30 s`→429 `rate_limit_exceeded`+`Retry-After`；`_inflight` 归零、无许可泄漏（§1.5.1 c8） | Designed |
| M003 provider 凭据解析分支：`env:` 无值 / `file:` 不可读 / 非法引用→凭据缺失（组装，ENV-3） v0.1.0-draft.1 | VRC-INF-003 | MT-INF-019 | negative | P1 | `secret_ref` 为 `env:` 空值 / `file:` 不可读 / 非法 scheme→503 `provider_secret_unavailable`；不 dispatch、无义务（§1.5.1 a24/b8） | Designed |
| M001 鉴权结果 × 端点类别组合（K1，组装） v0.1.0-draft.2 | VRC-API-002 | MT-API-011 | security | P0 | pairwise 组合行：(data-ok, data 端点) / (admin-ok, admin 端点) / (data-cred, admin 端点)→403 / (无凭据, 非受信)→401 / (未配置, 任一端点)→503，断言组装路径上拒绝先于业务 | Designed |

**层②计数：47 条分支**（M001 9 / M002 4 / M003 15 / M004 6 / M005 3 / M006 5 / M007 3 / M008 2），较 `0.1.0-draft.5` 增 **10 条**（M001 +2 传输病态、M003 +7 上游/时间病态、M004 +1 固定 tier；见 §1.5.1（a)-(c)）。§3.2 表内另含 **1 条组合落地 Case**（`MT-API-011`，对应 §3.3 K1），其独自分母计入层③，不重复计入层②。

### 3.3 层③组合（判定表 / 配对 pairwise 的行）

> 分母＝相互独立判定的组合行（判定表/配对矩阵），每行至少 1 Case。**不做全组合**，用 pairwise 削减；给出选组合的理由。

| 组合 ID | 组合矩阵（行＝选中组合） | 独立性依据 / 选行理由 | 映射 Case | 追溯 VRC | 设计状态 |
|---|---|---|---|---|---|
| K1 鉴权结果 × 端点类别 | (data-ok, data 端点) / (admin-ok, admin 端点) / (data-cred, admin 端点)→403 / (无凭据, 非受信)→401 / (未配置, 任一端点)→503 | 鉴权判定独立于端点类别；全组合 5×3，pairwise 保留交叉拒绝行 | MT-API-006 / MT-API-011 | VRC-API-002 | Designed |
| K2 SSE body 形态 × 终止界定 | (message 帧, completed) / (reasoning 帧, completed) / (function_call 帧, completed) / (任一流, client-abort) / (任一流, error-abort) | body 形态与终止原因独立；选择能触发 terminal 三态的代表行 | MT-API-008 | VRC-API-003 | Designed |
| K3 分页 cursor 状态 × 越界 | (无 cursor, 首页) / (有效 cursor, 下一页) / (过期 cursor, 400) / (有效 cursor, 超出总分页, 空页) | cursor 状态与越界独立；覆盖正常/错误/边界三分 | MT-MGMT-009 | VRC-MGMT-004 | Designed |
| K4 注入类型 × 准入阶段 | (fault_502, pre-call) / (fault_503, pre-call) / (rate_limit, pre-call) / (delay, pre-call) / (stream_terminate, stream) / (malformed_event, stream) | 注入类型与生效阶段独立（`_PRE_CALL` vs `_STREAM`）；每类型每阶段一行 | MT-INF-008 / MT-DIAG-005 | VRC-INF-003 / VRC-DIAG-004 | Designed |
| K5 能力档 × 请求形态 | (responses=false, 基本) / (responses=true + tools=false, 带 tools) / (responses=true + max=null, 带 max) / (responses=true + max=int, 带 max 越界) | 能力档与请求字段独立；覆盖能力拒绝与数值边界 | MT-INF-006 | VRC-INF-001 | Designed |
| K6 资源类别 × 错误码 | (provider, 412) / (deployment, 412) / (service_level, 409-conflict) / (provider, 409-in-use) / (deployment, 409-in-use) / (任一类, 404) | 错误码判定跨资源类别一致，选交叉代表行 | MT-MGMT-007 | VRC-MGMT-002 | Designed |
| K7 账号用量 provider × 凭据 × 确认 | (local, 无凭据, 已确认) / (minimax, 有凭据, 未确认)→400 / (minimax, 无凭据, 已确认)→unavailable / (volc, 有凭据, provider 报错)→unavailable | provider 分支、凭据存在、确认三分量独立；pairwise 覆盖 | MT-MGMT-010 | VRC-MGMT-006 | Designed |
| K8 注入类型 × config 合法性 | (六类, 合法) / (任一类, enabled 非布尔) / (任一类, 缺字段) / (delay, 越界) / (malformed_event, 非法 event type) / (fault_502, error_body 空) | 类型与校验出口独立；校验出口不随类型变，选交叉代表行 | MT-DIAG-003 | VRC-DIAG-004 | Designed |
| K9 游标状态 × 查询面 | (traces, 非法) / (traces, 时间窗越界) / (snapshots, 非法) / (snapshots, 分页 next) | 游标判定在 traces/snapshots 两查询面复用 | MT-DIAG-006 | VRC-DIAG-002 | Designed |
| K10 敏感模式 × 位置 | (Bearer, 行首) / (token=, 行中) / (api_key, 行尾) / (authorization, 键值) / (普通文本, 不误伤) | 正则命中与位置独立；覆盖命中和未命中 | MT-LOG-002 | VRC-LOG-001 | Designed |

**层③计数：10 条组合行（跨 8 模块，共 10 组）**。

### 3.4 层④状态转换（迁移表的行）

> 分母＝模块内状态机的迁移行，每条迁移至少 1 Case。给迁移表（当前态 → 事件 → 次态 / 可观测）。

| 迁移 ID | 状态机 | 迁移（当前态 → 事件 → 次态） | 可观测/断言 | 映射 Case | 追溯 VRC | 设计状态 |
|---|---|---|---|---|---|---|
| T1 账本 | UsageRecorder | unknown → authorize_dispatch → 未定/unknown | 新版本行 `measurement_status=unknown`、`is_final=0` | MT-INF-003 / MT-INF-009 | VRC-INF-003 | Designed |
| T2 账本 | UsageRecorder | 未定 → finish(measured) → final | `is_final=1`、`source=provider`、tokens 落库 | MT-INF-003 | VRC-INF-003 | Designed |
| T3 账本 | UsageRecorder | 未定 → finish(None) → final(unknown) | `is_final=1`、`source=unavailable`、tokens 为 NULL 不补零 | MT-INF-003 | VRC-INF-003 | Designed |
| T4 路由槽位 | Router | held → 上下文退出 → released | `_inflight` 减 1、provider in-flight 减 1、notify | MT-INF-004 | VRC-INF-004 | Designed |
| T5 路由队列 | Router | pushed → pop(dispatched) / timeout(429) | 队列长度归零；FIFO 序；超时错误 | MT-INF-007 | VRC-INF-004 | Designed |
| T6 bootstrap | Registry | 空库 → 合法 settings → ready | 表就绪、无 `bootstrap_error`、`/readyz` 200 | MT-MGMT-001 | VRC-MGMT-001 | Designed |
| T7 bootstrap | Registry | 空库 → 非法 settings → 回滚空库 + not_ready | 事务回滚无半写、`bootstrap_error` 置位、`/readyz` 503 | MT-MGMT-006 | VRC-MGMT-001 | Designed |
| T8 资源版本 | Registry | vN → update → vN+1（ETag 变化） | 返回新 ETag；旧 ETag PATCH→412 | MT-MGMT-007 | VRC-MGMT-002 | Designed |
| T9 开关 | DiagnosticSettings | off → on → off | 关闭态写入零行；开启态行产生 | MT-OBS-002 / MT-DIAG-001 | VRC-OBS-001 / VRC-DIAG-001 | Designed |
| T10 注入 | InjectionDiagnostics | 无 → `set_injections(启用)` → 命中 | `enabled_injection` 返回首个命中（优先级序） | MT-DIAG-004 | VRC-DIAG-004 | Designed |
| T11 注入 | InjectionDiagnostics | 启用 → `set_injections([])` → 撤销 | 行删除；`enabled_injection` 返回 None | MT-DIAG-004 | VRC-DIAG-004 | Designed |
| T12 存储 | Store | 空 → `_initialize` → 已迁移 → `close` | schema_meta 就绪；close 释放 fd | MT-UTIL-002 | VRC-UTIL-002 | Designed |
| T13 存储 | Store | 迁移中 → 失败 → 回滚 | 回滚为空库且可重新启动 | MT-UTIL-005 | VRC-UTIL-002 | Designed |
| T14 日志 | OperationalLog | append → 查询 DESC | 追加顺序在 `page` 中倒序稳定 | MT-LOG-003 | VRC-LOG-001 | Designed |

**层④计数：14 条状态迁移**（M003 5 / M004 3 / M005+M006 3 / M007 2 / M008 1）。

### 3.5 VRC 追溯（不作分母）

> 本层 VRC 对照见附录 A；VRC 在 §3.1–§3.4 只作**追溯列**。33 个模块设计 §14 验证项全部在 §3 有追溯（见附录 A）。
> **注意**：33/33 为**设计验证项追溯覆盖**；行为覆盖由四层分母（层①20 + 层②47 + 层③10 + 层④14）共同确证。M002 `VRC-UI-001..006` 的模块层 Case 为**静态产物/契约**层面的组装验证；其**真实 JS 行为级**由系统层真实浏览器 `ST-UI-001..010` 承接（见 `llmtier-system-test-scheme` §4）。

### 3.6 分母计数汇总

| 层 | 分母（条/行） | 说明 |
|---|---|---|
| ① 对外接口端到端行为 | 20 | §3.1（模块设计 §9 接口行为） |
| ② 内部分支 | 47 | §3.2（每个判定分支 1 Case） |
| ③ 组合（判定表/配对） | 10 | §3.3（组合行） |
| ④ 状态转换（迁移表） | 14 | §3.4（迁移行） |
| **合计分母** | **91** | 四层相加 |
| **模块 Case 总数** | **68** | 见下 |

**Case 总数：68**（分类：negative 18 / boundary 13 / normal 11 / recovery 17 / security 6 / concurrency 3；Priority P0 39 / P1 29）。全部归属 8 模块（`M001-M008`），无工具 Case。较 `0.1.0-draft.5` 增 **10 个 Case**（`MT-MGMT-011`、`MT-API-012/013`、`MT-INF-013…019`），全部来自 §1.5.1 异常/错误注入矩阵的 a16/a24、b4/b8、c1–c8。

> **分母→Case 说明（多分支/多行合并为 1 Case）**：四层分母 91 条并非 91 个 Case——按 §1.5 “分支/组合/迁移必覆盖”原则，**同模块内相互接近的分支/组合行/迁移可合并入 1 个 Case**，但每一行都必须在 §3.2/§3.3/§3.4 的“映射 Case”列或 §3.7 分支分母表被点名。反向核对：91 条分母每条都映射到 ≥1 个 `MT-*` Case（见 §3.7）。
> **注入类方法不增分母**：§1.5「注入类方法」的「mock 返回」六类、存储/传输/准入面与数据注入 4 类是**跨家族应用的构造/刺激手段**，其落点映射到四层分母的既有行（见 §3.7 注入面/数据类型核对块）；**§1.5.1「异常/错误注入矩阵」** 是同一手段口径的**全量封闭清单**（37 code + 8 上游类 + 8 传输/时间病态），其落点同样映射到既有/新增分支行——其中 a16/a24、b4/b8、c1–c8 由 **10 个新增分支 Case** 承接（计入层②），其余由既有 Case 承接；矩阵本身不另设 Case、不重复计分母。
> **module-case 文档映射**：本清单 68 个 Case，对应 68 份 `tests.module-case` 文档（`docs/70_verification/module/cases/MT-<OBJ>-<NNN>.md`），**本步尚未建立**（下一交付步建立，建立后完成 68/68）；本表设计状态均为 `Designed`。

### 3.7 分支 / 组合 / 迁移分母→Case 映射核对表（全覆盖核对）

> 本表逐条列出 §3.2/§3.3/§3.4 的全部分支/组合/迁移分母，并给出映射 Case；**任何一条未映射即缺口**（须在 §4 具名或 `Tailored-N/A`）。

| 分母层 | 分母 ID（模块） | 映射 Case |
|---|---|---|
| 分支 | M001-未命中404 / M001-命中 | MT-API-004 |
| 分支 | M001-ApiError/sqlite/未知异常 | MT-API-005 |
| 分支 | M001-401/403/503 / `_auth_either` 优先级 | MT-API-006 |
| 分支 | M001-Content-Length/413/JSON/非对象 | MT-API-007 |
| 分支 | M001-SSE completed/client-abort/error-abort | MT-API-008 |
| 分支 | M001-穿越/未命中/`/ui/` | MT-API-009 |
| 分支 | M001-correlation header/traceparent/缺省 | MT-API-010 |
| 分支 | M002-dispatchUiError 五分支 | MT-UI-003 |
| 分支 | M002-backendState/tierState 五态 | MT-UI-004 |
| 分支 | M002-usageSummary 四态 | MT-UI-005 |
| 分支 | M002-reportLoadFailure 抑制/未知 | MT-UI-006 |
| 分支 | M003-校验四出口 | MT-INF-005 |
| 分支 | M003-能力三分支 | MT-INF-006 |
| 分支 | M003-准入四出口 | MT-INF-007 |
| 分支 | M003-注入四态 | MT-INF-008 |
| 分支 | M003-admitted 真/假副作用 | MT-INF-009 |
| 分支 | M003-embeddings 四分支 | MT-INF-010 |
| 分支 | M003-fail-open | MT-INF-011 |
| 分支 | M003-上游非 5xx 错误（配额/额度耗尽 429/402/403） | MT-INF-012 |
| 分支 | M004-bootstrap 五出口 | MT-MGMT-006 |
| 分支 | M004-CRUD 五错误分支 | MT-MGMT-007 |
| 分支 | M004-能力校验三分支 | MT-MGMT-008 |
| 分支 | M004-cursor 四态 | MT-MGMT-009 |
| 分支 | M004-refresh 四态 | MT-MGMT-010 |
| 分支 | M005-开关四分支 | MT-OBS-002 |
| 分支 | M005-查询三分支 | MT-OBS-003 |
| 分支 | M005-注入三分支 | MT-OBS-004 |
| 分支 | M006-注入校验六分支 | MT-DIAG-003 |
| 分支 | M006-set_injections 三分支 | MT-DIAG-004 |
| 分支 | M006-stream_wrapper 三态 | MT-DIAG-005 |
| 分支 | M006-游标分支 | MT-DIAG-006 |
| 分支 | M006-fail-open 分支 | MT-DIAG-007 |
| 分支 | M007-连接四分支 | MT-UTIL-003 |
| 分支 | M007-migrate 四拒绝出口 | MT-UTIL-004 |
| 分支 | M007-嵌套 409/迁移回滚 | MT-UTIL-005 |
| 分支 | M008-脱敏五模式 | MT-LOG-002 |
| 分支 | M008-page 三分支 | MT-LOG-003 |
| 分支 | M004-固定 tier 删除 `fixed_service_level`（§1.5.1 a16） | MT-MGMT-011 |
| 分支 | M001-客户端中途断开 broken pipe（§1.5.1 c4） | MT-API-012 |
| 分支 | M001-连接重置 RST mid-stream（§1.5.1 c5） | MT-API-013 |
| 分支 | M003-stall/hang 超时（§1.5.1 c1） | MT-INF-013 |
| 分支 | M003-slow-response 流空闲超时（§1.5.1 c2） | MT-INF-014 |
| 分支 | M003-超大 response 归一（§1.5.1 c3） | MT-INF-015 |
| 分支 | M003-截断流/early EOF（§1.5.1 c6） | MT-INF-016 |
| 分支 | M003-畸形帧（§1.5.1 c7） | MT-INF-017 |
| 分支 | M003-并发超时 + 许可泄漏（§1.5.1 c8） | MT-INF-018 |
| 分支 | M003-provider 凭据解析 `provider_secret_unavailable`（§1.5.1 a24/b8） | MT-INF-019 |
| 组合 | K1 鉴权×端点 | MT-API-006 / MT-API-011 |
| 组合 | K2 SSE body×终止 | MT-API-008 |
| 组合 | K3 cursor×越界 | MT-MGMT-009 |
| 组合 | K4 注入类型×阶段 | MT-INF-008 / MT-DIAG-005 |
| 组合 | K5 能力档×请求形态 | MT-INF-006 |
| 组合 | K6 资源类别×错误码 | MT-MGMT-007 |
| 组合 | K7 provider×凭据×确认 | MT-MGMT-010 |
| 组合 | K8 注入类型×config 合法性 | MT-DIAG-003 |
| 组合 | K9 游标状态×查询面 | MT-DIAG-006 |
| 组合 | K10 敏感模式×位置 | MT-LOG-002 |
| 迁移 | T1/T2/T3 账本 | MT-INF-003 / MT-INF-009 |
| 迁移 | T4 路由槽位释放 | MT-INF-004 |
| 迁移 | T5 路由队列 | MT-INF-007 |
| 迁移 | T6/T7 bootstrap | MT-MGMT-001 / MT-MGMT-006 |
| 迁移 | T8 资源版本 | MT-MGMT-007 |
| 迁移 | T9 开关 off↔on | MT-OBS-002 / MT-DIAG-001 |
| 迁移 | T10/T11 注入启用/撤销 | MT-DIAG-004 |
| 迁移 | T12/T13 存储初始化/回滚 | MT-UTIL-002 / MT-UTIL-005 |
| 迁移 | T14 日志顺序 | MT-LOG-003 |

**核对结论**：层②47 条分支、层③10 条组合行、层④14 条迁移行**全部映射到 ≥1 Case**（0 未映射）。

**注入面 / 数据类型 → Case 核对块**（§1.5「注入类方法」的落点核对；不新增分母、不新增 Case，注入是跨家族手段）：

| 注入分类 | 注入面 / 数据类型 | 映射 Case |
|---|---|---|
| 故障注入（主：边界替身返回错误） | mock 返回 **5xx**（上游错误响应） | MT-INF-003 / MT-INF-008 |
| 故障注入（主：边界替身返回错误） | mock 挂起 **超时** | MT-INF-003 / MT-INF-008 |
| 故障注入（主：边界替身返回错误） | mock 抛错 **断连** | MT-INF-003 / MT-INF-011 |
| 故障注入（主：边界替身返回错误） | mock 返回 **配额/额度耗尽（quota exhausted，4xx 429/402/403）** | **MT-INF-012** |
| 故障注入（主：边界替身返回错误） | mock 返回 **坏数据（契约违规：非 SS 帧·坏向量·非法 base64）** | MT-INF-010 / MT-INF-002 |
| 故障注入（主：边界替身返回错误） | mock 返回 **畸形流（非法 SSE/多 terminal/坏帧）** | MT-DIAG-005 / MT-INF-003 |
| 故障注入 | 存储面：库写失败 / 表损坏 / 迁移中途失败 | MT-INF-009 / MT-DIAG-007 / MT-OBS-004 / MT-UTIL-004 / MT-UTIL-005 |
| 故障注入 | 传输面：客户端中途断开 / 超大流 / 畸形事件 | MT-API-008 / MT-API-007 / MT-DIAG-005 |
| 故障注入 | 准入面：队列饱和 429 / 全不健康 503 / 等待超时 | MT-INF-007 / MT-INF-004 |
| 数据注入 | 初态数据（经公开入口播种，禁止直写表） | 各 Case 公开入口前置；代表 MT-MGMT-001/006 / MT-INF-003/004 / MT-DIAG-004 / MT-OBS-002 |
| 数据注入 | 边界数据（2 MB / `limit` 上限 / 512 / 极值·空·未知） | MT-API-007 / MT-MGMT-009 / MT-LOG-001 / MT-LOG-003 |
| 数据注入 | 诊断数据注入（`PATCH /v1/deployments/{id}/diagnostics`） | MT-DIAG-002 / MT-DIAG-003 / MT-DIAG-004 / MT-OBS-004 |
| 数据注入 | 冻结向量（SSE 字节帧 / 32-hex traceparent / base64 / UI 资产字符串） | MT-API-008 / MT-API-010 / MT-INF-002 / MT-INF-010 / MT-UI-001 / MT-UI-002 |

**注入面核对结论**：上述「mock 返回」6 类 + 存储/传输/准入 3 面 + 数据注入 4 类**全部映射到 ≥1 Case**（0 未映射）；边界替身按配置返回错误即命中（判定＝模块对该错误的映射），产品注入未命中即 `INVALID`（见 §5）。

**异常 / 错误注入矩阵 → Case 核对块**（§1.5.1（a)/(b)/(c) 的全量封闭核对；Oracle ＝ `src/`）：

| 矩阵组 | 条目 | 映射 Case / 具名 Gap |
|---|---|---|
| (a) 对外 error code | a1–a37 全部 37 个 `code` | 见 §1.5.1（a）逐行；a16→MT-MGMT-011、a24→MT-INF-019，其余 35 个命中既有 Case |
| (b) 上游异常类别 | b1 上游 4xx / b2 上游 5xx / b3 配额耗尽 / b4 非 JSON / b5 非 SS 帧 / b6 坏向量 / b7 非法 base64 / b8 凭据缺失 | MT-INF-012 / MT-INF-003·008 / MT-INF-012 / **MT-INF-017** / MT-DIAG-005·**MT-INF-016** / MT-INF-010 / MT-INF-010 / **MT-INF-019** |
| (c) 传输/时间病态 | c1 stall/hang / c2 slow-response / c3 超长超大 / c4 broken pipe / c5 RST / c6 截断流 / c7 畸形帧 / c8 并发超时+许可泄漏 | **MT-INF-013** / **MT-INF-014** / **MT-INF-015** / **MT-API-012** / **MT-API-013** / **MT-INF-016** / **MT-INF-017** / **MT-INF-018** |

**异常/错误矩阵核对结论**：(a) 37 个对外 `code` + (b) 8 类上游异常 + (c) 8 类传输/时间病态 = **53 条全部映射到 ≥1 Case 或具名 Gap（0 静默缺失）**；其中 10 个新增分支 Case（`MT-MGMT-011`、`MT-API-012/013`、`MT-INF-013…019`）承接 20 条（a16/a24、b4/b8、c1–c8）。

**design-vs-code 缺口（Oracle 对照）**：`src/` 实现与系统设计 §7.8 目录一致，未发现 `code` 值分歧；**但 §7.8 未决项（`interfaces/error-codes/` 机器目录未建）** 使 `code` 的机器权威仍为 `openapi` response schema——本矩阵以 `src/` 为 Oracle 登记，若后续建立 `interfaces/error-codes/` 须回溯本矩阵与 §1.5.1。**Named Gap（模块层不可测）**：c3「超 2 MB 下游响应预算」为系统层资源预算（归 `llmtier-system-test-scheme`），本层只断言模块内归一不崩溃——具名见 §4。

## 4. 不适用与缺口裁决

> **本表口径**：Tailored-N/A 必须引用设计章节事实；Gap 须有 Owner 与恢复条件；两者都不从分母静默消失。本层四层分母全部登记 Case；下列为**本层不承接的组合保证**（非分母条目）与**design-vs-code 缺口/观察项**（本轮 68 Case 实测发现，Oracle ＝ `src/`）。
> **缺口分类**：`G-*` ＝需回溯设计修订的实质缺口；`O-*` ＝实现现状与规格措辞不一致但不阻断本层判定的观察项。两者都不改变 §3 四层分母与 68 Case 清单，只约束 Oracle 取值与断言深度。

| 来源 ID / 事实依据 | 裁决（Tailored-N/A / Gap） | Owner / 恢复条件 |
|---|---|---|
| 跨模块系统级流程、systemd/反向代理、Piko 联调 | Tailored-N/A（本层不测；各模块设计 §14「父级组合验证交接」已列承接方） | 归系统测试方案（`llmtier-system-test-scheme`） |
| 真实上游 provider 协议与 wire 互操作、浏览器 E2E | Tailored-N/A（本层不测；系统方案已承接） | 归契约层与 `llmtier-system-test-scheme` |
| M002 `VRC-UI-001..006` 的**行为级**（真实 JS 执行） | Tailored-N/A（本层仅静态产物/契约组装；行为级归系统层） | Owner：M002 web-ui。**事实**：`MT-UI-*` 为组装契约层验证；行为级由系统层真实浏览器 `ST-UI-001..010`（headless Chrome over CDP）承接，原 `RISK-UI-EXEC-1` 已关闭（见 `llmtier-system-test-scheme` §4）。 |
| performance / endurance 分类 | Tailored-N/A（本层不纳入；见 §2 裁剪依据） | 归系统测试方案 |
| §1.5.1 a25 / b4 / c7：非 JSON `data:` 帧、非 JSON embeddings 响应体 → 预期 `502 provider_contract_error` | **design-vs-code 缺口 G-INF-NONJSON-MAPPING-1**（Oracle ＝ `src/`，实测为准） | Owner：M003 inference ＋ 系统设计 §7.8。**事实**：`OpenAIProvider.complete/_request` 把 `json.JSONDecodeError` 归入传输异常类 → 实测映射 `503 provider_unavailable`（retryable），而非矩阵预期的 `502 provider_contract_error`（对比：非 SSE Content-Type、多 terminal、terminal/status 矛盾、无合法 terminal 确为 502）。`MT-INF-017` 按 `src/` 断言并在此登记偏差。**恢复条件**：设计侧确认权威映射（503 或改实现为 502）后回溯修订 §1.5.1（a25/b4/c7）与本行；若建立 `interfaces/error-codes/` 目录，以其为准。 |
| `VRC-OBS-004` trace stage 因果序（"诊断 trace stage 有序"） | **design-vs-code 缺口 G-OBS-STAGE-ORDER-1** | Owner：M006 libdiag。**事实**：`libdiag/common.now()` 为毫秒精度，`TraceDiagnostics._trace_view` 按 `(stage_timestamp, id)` 排序而 `id` 为随机 `tev_<uuid4>`；快请求各 stage 落在同一毫秒时返回乱序（实测 40 次中 18 次乱）。`MT-OBS-001` 因此只断言 stage 集合与非递减时戳，不断言位置序。**恢复条件**：增加每请求单调序号列或改 `ORDER BY rowid` 后，回溯修订 `VRC-OBS-004` 并把位置序断言补入 `MT-OBS-001`。 |
| M002 `app.js` 的 `LOGIN_URL='/login'`（ ISD §5.1 401 跳转） | **design-vs-code 缺口 G-UI-LOGIN-ROUTE-1** | Owner：M002 web-ui ＋ M001 http-api。**事实**：`_static` 只放行 `/`、`/ui`、`/ui/*`，M001 无 `/login` 路由 → loopback 实测 `GET /login` 为 404 `not_found`。`MT-UI-003` 的 401 分支只做静态契约断言与服务端锚点。**恢复条件**：M001 提供 `/login`（或 ISD 改指真实登录入口）后，补 `/login` 端到端断言。 |
| M001 `_store_read` 统一映射存储读失败为 `usage_store_unavailable`（`app.py:144`），被诊断查询面复用 | **观察项 O-OBS-STORECODE-1**（非阻断，映射行为与契约一致） | Owner：M001。**事实**：§1.5.1 a27 原只映射 `MT-API-005`；实测 `MT-OBS-003` 是同一 `code` 的第二个映射点（诊断快照/统计/traces 查询面）。**恢复条件**：若错误目录按面细分 `code`，回溯修订 a27 与本行；否则把 a27 的映射 Case 补记 `MT-OBS-003`。 |
| M002 `backendState` 的 4 个 health 分支（`running`/`probing`/`exhausted`/`unreachable`）与 `health.py` 允许的 `degraded` | **观察项 O-UI-HEALTHDOMAIN-1** | Owner：M002 web-ui。**事实**：产品对 `deployments.health` 的全部写点只有 migration 默认 `'unknown'` 与 `apply_probe_result`（`healthy`/`unhealthy`）；`probing`/`exhausted`/`unreachable`/`running` 在 `src/` 内无写点，`degraded` 合法但 UI 无分支（落 Unknown）。`MT-UI-004` 对无写点取值只做静态契约断言。**恢复条件**：health 域扩展（如探测中态写入）后在 `MT-UI-004` 补行为级断言。 |
| M002 `usageSummary` 的 `ok` 分支（逐 window/percent 渲染） | **观察项 O-UI-USAGEOK-1** | Owner：M002 ＋ M004。**事实**：`ok` 只由真实 MiniMax/Volcengine 响应产生，M004 的 provider HTTP 面无边界替身资产可注入；本层只静态断言渲染分支。**恢复条件**：为 account-usage 面建 `tests.asset-design` 替身后补行为级断言。 |
| M003 `stream_idle_timeout_ms` 生效性 | 已修（`src/inference/providers/openai.py::_stream_read_timeout`） | **事实**：Python 3.14 `SocketIO` 无 `settimeout`，原实现静默 no-op → 读阶段回落到 `connect_timeout`（默认 30s），`stream_idle_timeout` 形同虚设。已补 `_sock.settimeout` 兜底；`MT-INF-014` 据此在 0.4s 内命中流空闲超时。**恢复条件**：无（已随本轮 fix 落地，见提交记录）。 |
| §1.5.1（c3）超 2 MB **下游响应**资源预算（超大流的下游预算，非模块内归一） | Gap（G-TRANSPORT-BUDGET-1） | Owner：LLMTier（系统层）。**事实**：模块层仅断言「模块内归一不崩溃」（MT-INF-015）；下游 2 MB/带宽预算属系统层资源预算，归 `llmtier-system-test-scheme`；恢复条件：系统层预算用例建立并引用本行。 |
| §1.5.1（c4/c5）真实 **跨主机** 网络 RST/半开连接（非 loopback） | Tailored-N/A（本层仅 loopback ENV-2 真实 socket） | Owner：LLMTier。**事实**：模块层用 loopback `127.0.0.1:0` 真实 socket 触发 `BrokenPipeError`/`ConnectionResetError`（MT-API-012/013 已覆盖进程内可复现断连）；跨主机链路病态归系统/运维层。 |

## 5. 文档联动与清单变更规则

- 方案冻结与变更规则：清单随各模块设计/ISD 基线冻结；新增 Case 先在本清单登记再建 `tests.module-case` 文档；分支/组合/迁移变更时同步 §3.2–§3.4 与 §3.7；Case ID 一经登记不复用、不改名。
- **与单元层（UT）去重规则（强制）**：
  1. **UT 已证的单函数分支不在 MT 重复**——单元层已覆盖且组装不改判的**单函数分支**，模块层不重复登记；模块层引用其 Case ID 而不复写断言（比对 `llmtier-unit-test-scheme` §3）。
  2. **MT 只测“UT 各自 PASS 但组装后可能不成立”的点**——即**分支在组装路径上的走向**、**组合交叉**、**跨单元状态迁移**与**调用序/接线**（先 auth 后 dispatch、先 admit 后 dispatch、审计同事务、路由→服务→存储）。这是模块层存在的理由。
  3. **判定方法**：若某断言可由单一函数在 mock 环境下等价复现，则归 UT；只有当断言依赖**真实内部协作者组合**（真实 `Store`/`Registry`/`Router`/`UsageRecorder`/`DiagnosticsService` 同栈）才归 MT。§3.2/§3.3/§3.4 的分母均为**跨单元组装面**，已在选行时据此过滤。
- **注入类方法规则（强制，见 §1.5）**：
  1. **注入命中否则 INVALID**——凡使用故障/延迟/流截断/畸形事件等注入的 Case，**必须**断言注入命中（命中计数 > 0）；注入计数为 0、并发未交错或故障未实际触发 → 该 Case 记 `INVALID`（**不记 PASS**）；**不得用“重试即恢复”掩盖根因**（须断言注入后的分支走向/回滚/无半写/`unknown` 不补零）。
  2. **数据注入经公开入口 + 未知不补零**——数据注入（初态/边界/诊断/冻结向量）**必须经公开入口**驱动（HTTP 端点 / 服务方法 / `Store` 公开方法），**禁止**测试直写表或直改内部字段建立初态；注入值与观测**严格相等**，未知/缺失值以 `unknown`/`Unknown`/NULL 表达，**绝不补零**。
  3. **异常/错误注入矩阵封闭（强制，见 §1.5.1）**——(a) 每个对外 `code`、(b) 上游异常类别、(c) 传输/时间病态**必须各自映射到 ≥1 Case 或具名 Gap**，以 `src/` 为 Oracle；新增/变更 `ApiError(...)` 调用点即触发矩阵回归。**真实 socket 病态（c4/c5）必须用 ENV-2 真实客户端中途断开/RST**，不得以进程内对象模拟替代。
- 与 case-design / 计划的同步规则：Case 文档 ID＝Case ID；`tests.module-test-plan` 构成表引用本方案版本；本方案合并 8 模块，逐模块切片由 Case ID 前缀承担。**case 文档的测试方法声明（强制契约条款）**：每份 `tests.module-case` 文档 §1 **必须**含一条 `- **测试方法（§1.5 方法表行）**：<technique(s)>` 列表项（**不新增章节**），指名本方案 §1.5 家族表的**确切技术行**；技术须由该 Case 的**实际分类 + 步骤/断言**推导，跨两类时并列；该条**必须**同时点名 STD test-standard §3 规定的模块**主要手段**（**公开入口** + **边界替身**：声明经哪个公开入口驱动、边界外协作者用何替身，或声明「无边界替身、全真实」）；若该 Case 覆盖分支/组合/迁移，须另在 §1 声明其覆盖的**分支 ID / 组合 ID / 迁移 ID**（取自 §3.7）；缺失或不诚实声明即视为 Case 不完备。
- 新增 Case 示例：`0.1.0-draft.6` 已按 §1.5.1 新增 `MT-MGMT-011`（固定 tier 删除 `fixed_service_level`）、`MT-API-012/013`（真实 socket broken pipe / RST）、`MT-INF-013…019`（stall/hang、slow-response、超大 response、截断流、畸形帧、并发超时+许可泄漏、凭据缺失）——先入本清单再建 `tests.module-case` 文档；模块计划引用本方案 `0.1.0-draft.6`。

## 附录 A. 本层设计验证项 VRC 汇集（对照用）

| 设计验证项 ID | 要验证什么（名称/责任） | 设计来源 | §3 Case 覆盖（追溯，非分母） |
|---|---|---|---|
| VRC-API-001 | 分发/错误/资源 | `http-api-design` §14.1 / `http-api-isd` §9.1.1 | MT-API-001/002/004/005 |
| VRC-API-002 | 鉴权 | `http-api-design` §14.2 / `http-api-isd` §9.1.2 | MT-API-006/011 |
| VRC-API-003 | body 与 SSE | `http-api-design` §14.3/§14.4 / `http-api-isd` §9.1.3 | MT-API-007/008/012/013 |
| VRC-API-004 | 静态与健康 | `http-api-design` §14.5/§14.6 / `http-api-isd` §9.1.4 | MT-API-003/009 |
| VRC-UI-001 | 加载与状态 | `web-ui-design` §14.1 / `web-ui-isd` §9.1.1 | MT-UI-001/004 |
| VRC-UI-002 | 编辑/鉴权 | `web-ui-design` §14.2 / `web-ui-isd` §9.1.2 | MT-UI-002/003/006 |
| VRC-UI-003 | Pause 边界 | `web-ui-design` §14.3 / `web-ui-isd` §9.1.3 | MT-UI-002 |
| VRC-UI-004 | 用量未知不填零 | `web-ui-design` §14.5 / `web-ui-isd` §9.1.4 | MT-UI-002/005 |
| VRC-UI-005 | 探测付费确认 | `web-ui-design` §14.4 / `web-ui-isd` §9.1.5 | MT-UI-002 |
| VRC-UI-006 | 诊断页 | `web-ui-design` §14.7 / `web-ui-isd` §9.1.6 | MT-UI-002 |
| VRC-INF-001 | 推理与流式契约 | `inference-design` §14.1 / `inference-isd` §9.1.1 | MT-INF-001/005/006 |
| VRC-INF-002 | 向量化契约 | `inference-design` §14.2 / `inference-isd` §9.1.2 | MT-INF-002/010 |
| VRC-INF-003 | 失败与用量 | `inference-design` §14.3 / `inference-isd` §9.1.3 | MT-INF-003/008/009/012/013/014/015/016/017/019 |
| VRC-INF-004 | 准入与目录 | `inference-design` §14.4 / `inference-isd` §9.1.4 | MT-INF-004/007/018 |
| VRC-INF-005 | 观测 fail-open | `inference-design` §14.5 / `inference-isd` §9.1.5 | MT-INF-011 |
| VRC-MGMT-001 | 引导与 Secret 引用 | `management-design` §14.1 / `management-isd` §9.1.1 | MT-MGMT-001/006 |
| VRC-MGMT-002 | CRUD 与不变量 | `management-design` §14.2 / `management-isd` §9.1.2 | MT-MGMT-002/007/008/011 |
| VRC-MGMT-003 | 审计与日志 | `management-design` §14.3 / `management-isd` §9.1.3 | MT-MGMT-002（审计同事务） |
| VRC-MGMT-004 | 分页与清空 | `management-design` §14.4 / `management-isd` §9.1.4 | MT-MGMT-003/009 |
| VRC-MGMT-005 | 探测 | `management-design` §14.5 / `management-isd` §9.1.5 | MT-MGMT-004 |
| VRC-MGMT-006 | 账号用量 | `management-design` §14.6 / `management-isd` §9.1.6 | MT-MGMT-005/010 |
| VRC-OBS-001 | 开关 | `observability-design` §14.1 / `observability-isd` §9.1.1 | MT-OBS-001/002 |
| VRC-OBS-002 | 快照/统计查询与脱敏 | `observability-design` §14.2 / `observability-isd` §9.1.2 | MT-OBS-001/003 |
| VRC-OBS-003 | 注入与 fail-open | `observability-design` §14.3 / `observability-isd` §9.1.3 | MT-OBS-004 |
| VRC-OBS-004 | trace 与关联标识 | `observability-design` §14.4 / `observability-isd` §9.1.4 | MT-API-010 / MT-OBS-001 |
| VRC-OBS-005 | trace 时间窗 | `observability-design` §14.5 / `observability-isd` §9.1.5 | MT-OBS-001 |
| VRC-DIAG-001 | 开关 | `libdiag-design` §14.1 / `libdiag-isd` §9.1.1 | MT-DIAG-001 |
| VRC-DIAG-002 | 记录与查询 | `libdiag-design` §14.2 / `libdiag-isd` §9.1.2 | MT-DIAG-001/006 |
| VRC-DIAG-003 | fail-open | `libdiag-design` §14.3 / `libdiag-isd` §9.1.3 | MT-DIAG-007 |
| VRC-DIAG-004 | 注入与 traces | `libdiag-design` §14.4 / `libdiag-isd` §9.1.4 | MT-DIAG-002/003/004/005 |
| VRC-UTIL-001 | 连接与回收 | `util-design` §14.1 / `util-isd` §9.1.1 | MT-UTIL-001/003 |
| VRC-UTIL-002 | 事务与迁移 | `util-design` §14.2 / `util-isd` §9.1.2 | MT-UTIL-002/004/005 |
| VRC-LOG-001 | 脱敏与查询 | `log-design` §14.1 / `log-isd` §9.1.1 | MT-LOG-001/002/003 |
