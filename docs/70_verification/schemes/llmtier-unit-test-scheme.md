<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Unit Test Scheme

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-unit-test-scheme` |
| Document Version | `0.1.0-draft.8` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.unit-test-scheme` |
| Template Version | `0.6.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/schemes/llmtier-unit-test-scheme.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本方案绑定软件模块集合：本方案覆盖 8 个软件模块 `M001-M008`（见 §1）；`design_object_id` 为本项目元数据可选字段，本方案 metadata 未写入该字段（合并方案跨 8 模块，单一 `design_object_id` 无法承载），模块归属改由 §3「来源 ID / 固定版本」列与 Case ID 前缀承担；模块/ISD 基线在 §1.5 固定；实现状态与执行结果不进本方案。
> 本文档对设计验证项（VRC）的引用规则：只引用 ID 与状态，不复制定义/判据/Owner；判据与契约权威归 design 与 tests.asset-design，本文档若细化执行断言需在变更时回溯设计修订并记录。
> **裁剪说明（tailored）**：模板默认“本方案绑定单一软件模块”。本项目按用户授权将 8 个模块的单元层 Case 清单合并为一份项目级方案（`M001-M008` 一次登记），逐模块归属由 §3 的「来源 ID / 固定版本」列与 Case ID 前缀承担；该合并只关清单登记位置，不改变 Case 与模块设计 VRC 的一一追溯。裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 模板定位：方案、用例与计划的边界

- **权威分工**：单元层测试的 Case 清单（ID、分类、优先级、责任摘要、设计状态）以本方案为唯一登记处；单 Case 展开归 `tests.unit-case`（一 Case 一文档）；活动组织归 `tests.unit-test-plan`。
- **只有摘要**：本方案每条 Case 只写责任摘要（要测什么），不写输入构造、Oracle 或步骤。
- **下层 PASS 不关闭本层**；本层 PASS 不关闭上层组合目标。

### 状态语义：用例状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 用例状态 | `Designed` / `Gap`（具名缺口）/ `Tailored-N/A` | 本方案 §3 清单 | 未设计写成已设计；N/A 无设计事实依据 |

任一 Case 在本方案中只报设计状态；实现与执行状态可沿 Case ID 追到 case-design 文档与 Run 报告。

## 1. 目标、范围与被测对象

- 被测对象、设计基线与父对象：LLMTier 源码 `src/http_api`(M001)、`src/web_ui`(M002)、`src/inference`(M003)、`src/management`(M004)、`src/observability`(M005)、`src/libdiag`(M006)、`src/util`(M007)、`src/log`(M008)；父对象为软件系统设计 `llmtier-system-design`；模块/ISD 基线见 §1.5。**M005 `src/observability/` 无独立实现文件**（仅空 `__init__.py`），其单元行为落在 M001 `app.py` 的诊断路由与 M006 `diagnostics.py` 查询面（见 M005 设计 §3/§4；本方案 §3 的 M005 行据此归属）。
- 本阶段测试边界（真实组成 / 边界替身）：被测模块内部为真实代码（`Store` 隔离临时库、`Registry`/`Router`/`UsageRecorder`/`AuditLog`/`OperationalLog`/`DiagnosticsService` 真实实例）；边界替身仅用于外部 collaborator——上游 provider 用进程内 `FakeAdapter`（`tests/unit/v03/fakes.py` 定义的共享 fake）、HTTP 层测试用 `ThreadingHTTPServer` 绑 `127.0.0.1:0` 的 loopback 测试实例、`FakeResponse` 为各测试模块内的**本地 HTTP 响应 stub**（定义于 `test_account_usage.py` / `test_provider_openai.py`，非 `fakes.py` 共享资产），用于 account-usage HTTP 与 OpenAI SSE 响应替身；替身契约由 `llmtier-unit-fakes`（`tests.asset-design` 实例，见 §1.6/§1.7）承载。
- 不证明的组合保证及承接入口：组装后的进程级流程（启动/systemd、反向代理、Piko 联调）、wire 互操作与 OpenAPI 端到端一致性、浏览器 E2E、真实上游 provider 协议；承接＝系统测试方案/计划（`llmtier-system-test-scheme`/`-plan`）与契约层。**本项目未采用独立模块测试层**（无 `tests.module-test-scheme`：模板要求方案绑定单一模块而本项目有 8 个模块，建立合并方案需授权）；本方案已按"被测模块内部为真实实现"即整模块组装层语义运行，模块级 VRC 的行为承接见系统测试方案 §4 裁决。
- 被测函数集合（每个 Case 的具体入口见对应 unit-case §2）：`src/http_api`（`errors.py`、`auth.py`、`sse.py`、`health.py`、`app.py` 含 `Handler._dispatch`/`_auth`/`_auth_either`/`_body`/`_json`/`_static`/`_store_read`/`_correlation`/`_optional_boolean`、模块级 `_int_param`、`_UnavailableDiagnostics`）、`src/inference`（`responses.py`、`embeddings.py`、`models.py`、`routing.py`、`usage.py`、`providers/openai.py`、`providers/base.py`）、`src/management`（`registry.py`、`admin.py`、`audit.py`、`account_usage.py`）、`src/libdiag`（`diagnostics.py`、`injections.py`、`snapshots.py`、`stats.py`、`traces.py`、`settings.py`）、`src/util`（`store.py`）、`src/log`（`logs.py`）、`src/web_ui`（`index.html`/`app.js` 契约）。

## 1.5 测试方法与测试设计技术

- **模块/ISD 基线**：M001 `http-api` v0.1.0-draft.2 / ISD `http-api-isd`；M002 `web-ui` v0.1.0-draft.2 / `web-ui-isd`；M003 `inference` v0.1.0-draft.1 / `inference-isd`；M004 `management` v0.1.0-draft.3 / `management-isd`；M005 `observability` v0.1.0-draft.6 / `observability-isd`；M006 `libdiag` v0.1.0-draft.6 / `libdiag-isd`；M007 `util` v0.1.0-draft.2 / `util-isd`；M008 `log` v0.1.0-draft.1 / `log-isd`。设计要求见各模块设计 §14 与 ISD §9.1。

| Case 家族 | 测试设计技术 | 环境类型引用 | 自动化与判定规则 |
|---|---|---|---|
| normal | 等价类划分（合法请求/合法状态机迁移） | ENV-1 隔离 Python 临时库 | `pytest -q` 全量；单次执行判 PASS/FAIL |
| | · 注入：固定 request、固定 tier/deployment、固定 fixture（`AppFixture.seed`） | | · 断言公开返回/落库行与独立期望严格相等 |
| boundary | 边界值（上限/零/空/刚好满、长度边界） | ENV-1 隔离 Python 临时库 | 单 Case `-k` 选择；超界→既定错误码 |
| | · 注入：空库、`limit` 上限、message 512 边界、`limit=1000`、`running>0` 边界、body 2 MB 边界、`max_output_tokens` 上下界 | | · 边界断言在「接受」与「拒绝」间二选一，无第三态 |
| negative | 错误猜测 + 反例驱动（非法字段/凭据/引用/类型） | ENV-1 隔离 Python 临时库 | 一次性判 PASS/FAIL；不掩盖 FAIL |
| | · 注入：未知 model、缺字段、非布尔开关、非法 cursor、未知 group_by、删除被引用、未知字段/非整数参数 | | · 每错误分支独立 Case，错误码/类型逐一断言 |
| concurrency | 线程对偶 + 受控时序（`threading`/`ThreadingHTTPServer`） | ENV-1 隔离 Python 临时库 + ENV-2 loopback 测试 HTTP 实例 | 固定种子/确定性交错；一次失败标 INVALID 复现 |
| | · 注入：并发 PATCH（ETag）、同 tier 第二个请求 FIFO、并发启动两实例 | | · 失败须记录并发交错样本；不靠“重跑通过”掩盖 |
| recovery | 故障注入 + 异常路径恢复（`LLMTIER_SLOW_ADAPTER_DELAY`/写入失败/断开） | ENV-1 隔离 Python 临时库 | 异常路径后断言无半写/回滚/推理不变 |
| | · 注入：上游 5xx/超时、库写失败、客户端断开、迁移中途失败、诊断初始化/写入失败 | | · 验证回滚/unknown 不补零/无部分表/fail-open 推理不变 |
| security | 鉴权/脱敏/注入边界冒烟（Bearer/LAN 信任、`[REDACTED]`、目录穿越） | ENV-1 隔离 Python 临时库 + ENV-2 loopback 测试 HTTP 实例 | 上游/系统层已覆盖，本层仅冒烟 |
| | · 注入：错误/缺失 Bearer、data 访问 admin、日志含 Authorization/Secret、`../` 路径 | | · 断言状态码与脱敏文本；不做模糊安全测试 |

### 测试设计技术选型表（按 Case 家族）

| Case 家族 | 选用的设计技术 | 选用理由 | 不选用的反模式 |
|---|---|---|---|
| normal | 等价类划分 + 固定 fixture | 覆盖合法输入空间，验证主路径 | 不用全部输入矩阵（规模爆炸） |
| boundary | 边界值（上限/零/空/刚好满/长度） | 边界是缺陷高发区，验证边界与邻近一步 | 不用随机/模糊测试（不可复现） |
| negative | 错误猜测 + 反例驱动 | 异常路径以设计已识别的反例为准 | 不用模糊异常注入（无 oracle/无归因） |
| concurrency | 线程对偶 + 确定性交错 | 状态机驱动，固定时序控制 | 不用随机并发（不可复现 + flaky） |
| recovery | 故障注入 + 异常路径回滚 | 资源归还与回滚基线需在失败路径覆盖 | 不用“重试”模拟恢复（掩盖根因） |
| security | 鉴权/脱敏/注入冒烟 + 契约 | 上游/系统层已覆盖，本层仅冒烟 | 不用模糊安全测试（不可复现 + 上游责任） |
| performance | 不在本层 | 性能预算归系统层 §系统测试方案 | 不用负载/容量测试（本层不负责系统预算） |
| endurance | 不在本层 | 耐久/长稳归系统层 | 不用长跑（本层不负责） |

## 1.6 替身使用策略与边界

- **决策准则**：被测模块内部一切真实；仅替换进程外的上游 provider 与真实网络端口。`Store` 使用临时隔离库（真实 SQLite，非 mock）；provider 用进程内 `FakeAdapter`；HTTP 层用真实 `ThreadingHTTPServer` 绑 `127.0.0.1:0`（loopback 测试实例，真实 socket）。
- **替身形态**：`FakeAdapter` 为进程内 fake（只代返回值/异常/终态，共享于 `tests/unit/v03/fakes.py`）；`FakeResponse` 为各测试模块**本地**定义的 HTTP 响应 stub（`test_account_usage.py` / `test_provider_openai.py` 各自定义，未进 `fakes.py`，也非共享探针 stub）；不用 mock 框架打桩被测自身。
- **替身保真度与契约**：替身契约与自检归 `tests.asset-design`（一资产一文档），本方案与 Case 只引用其 ID 不复制行为。**资产实例已建立**：`llmtier-unit-fakes`（`docs/70_verification/assets/llmtier-unit-fakes.md`，覆盖 `FakeAdapter`/`AppFixture`，候选 ID `FAKE-LLMTIER-ADAPTER`）；§3 各 Case 只引用该文档 ID。
- **交互断言 vs 返回值断言**：优先断言公开返回值、落库行与 wire 信封；必要时断言 `ApiError` 类型/错误码与关键调用序，不耦合被测内部实现。
- **反模式（逐项排除）**：不 mock 被测拥有的接口；不 mock 值对象/纯数据（dict/JSON 直接构造）；不为凑覆盖率而 mock；不过度断言内部细节。

| 协作者类型 | 替身形态 | 替身契约文档（tests.asset-design） | 决策理由 |
|---|---|---|---|
| 上游 provider adapter | 进程内 fake（`FakeAdapter`） | `llmtier-unit-fakes`（`docs/70_verification/assets/llmtier-unit-fakes.md`） | 真实 provider 不可控；fake 只代返回值/异常/终态 |
| provider HTTP 响应 | 本地 stub（各测试模块自定义 `FakeResponse`） | `llmtier-unit-fakes` §2/§3（明确声明 `FakeResponse` 为各模块本地 stub、非本资产成员） | 代 account-usage HTTP 与 OpenAI SSE 的响应体（非 `probe(models)`） |
| SQLite 存储 | 真实 `Store` + 临时隔离库 | 不适用（真实依赖） | 存储是被测对象一部分，用真实实现 + 密隔离 |
| HTTP 监听端口 | 真实 `ThreadingHTTPServer`（`127.0.0.1:0`） | 不适用（真实网络） | 端口是真实路径，仅绑 loopback 临时端口 |
| Web UI 静态产物 | 真实文件读取（`Path.read_text`） | 不适用（真实产物） | UI 契约对真实 `index.html`/`app.js` 断言 |

## 1.7 测试环境类型（方案定义）

| 环境类型 | 行为/真伪 | 契约文档 | 在本层用例中的角色 |
|---|---|---|---|
| ENV-1 隔离 Python 临时库 | 真实：`tempfile.TemporaryDirectory` + `Application`（`Store`+`Registry`+服务）；每 Case 新建、`tearDown` 销毁 | — | 绝大多数单元 Case 的默认环境（`tests/unit/v03/fakes.py::AppFixture`） |
| | · 契约：真实 SQLite 落库；`settings.json` 由 fixture 写入；不复用跨 Case 状态 | | · 用法：`setUp` 建 `AppFixture`、`tearDown` `close()` |
| ENV-2 loopback 测试 HTTP 实例 | 真实：`ThreadingHTTPServer((127.0.0.1, 0), handler_factory(app))` | — | HTTP/wire 契约层 Case（诊断 HTTP、鉴权、别名、静态） |
| | · 契约：真实 socket、临时端口、真实 handler 栈；不代被测 `app.py` 逻辑 | | · 用法：`setUpClass` 起服务、`tearDownClass` shutdown |
| ENV-3 provider 进程内 fake | fake：`FakeAdapter` 只代返回值/异常/终态 | `llmtier-unit-fakes` | 上游交互/失败注入 Case |
| | · 契约：`complete`/`embed`/`probe` 返回可配置结果；不证明真实 provider 协议 | | · 用法：`ResponsesService(..., adapter=FakeAdapter(...))` |

**总体说明**：Python 3.14（`python3 -m pytest`），`PYTHONPATH=src`；fixture 来源为 `tests/unit/v03/fakes.py`（`AppFixture`/`FakeAdapter`）；替身资产契约见 `llmtier-unit-fakes`（`docs/70_verification/assets/`，`Implemented`/`Unverified`）；CI 入口为 `PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`（或按 `-k` 选单 Case）；并发隔离按临时库实例；缺 Python/依赖记 Blocked，不静默换环境。

## 2. 测试分类体系

| 分类（STD 家族词表） | 本阶段适用性 | 裁剪依据 |
|---|---|---|
| normal | 适用 | — |
| boundary | 适用 | — |
| negative | 适用 | — |
| concurrency | 适用 | 同等级 FIFO、并发 PATCH、并发启动（模块设计 §8/§14 事实） |
| recovery | 适用 | fail-open、写入失败、迁移回滚、断开（模块设计 §14 事实） |
| security | 适用（冒烟） | 鉴权/脱敏/目录穿越属单元可测点；深层安全归系统层 |
| performance | 不在本层 | 归系统测试方案与预算 |
| endurance | 不在本层 | 归系统层长期稳定测试 |

## 3. 覆盖分母与 Case 清单

> 来源 ID 与设计验证项（VRC）的边界：本表登记 ID+责任摘要；判据/Oracle/Owner/契约权威归 design 与 tests.asset-design，不在此行复写；变更设计时同步 VRC 同步本清单。
> **分母来源**：8 个模块设计 §14 / ISD §9.1 声明的验证项，共 33 项——M001 `VRC-API-001..004`、M002 `VRC-UI-001..006`、M003 `VRC-INF-001..005`、M004 `VRC-MGMT-001..006`、M005 `VRC-OBS-001..005`、M006 `VRC-DIAG-001..004`、M007 `VRC-UTIL-001..002`、M008 `VRC-LOG-001`。**每个 VRC 至少一条记录**；一个 VRC 可由多 Case 分担（分别写责任摘要），下表逐行登记。
> **粒度来源**：Case 不仅取自 33 个 VRC，还取自 ISD↔code 复核给出的**具体未测行为**（M001 分发/参数/关联标识/别名/fail-open 分支；M002 六项 UI 行为（当前仅字符串契约）；M003 校验顺序/上游失败/准入/用量边界；M004 bootstrap/审计/分页/探测/账号用量缺口；M006 DIAG-002/003 分支；M007 UTIL-001/002 边界；M008 过滤与边界）。这些新增 Case 仍归属其源 VRC。
> **来源 ID 读法**：来源 ID 指向被测模块/单元本体——「模块设计 §14 验证项 / 被测符号」（如 `http-api-design §14.1 · Handler._dispatch`），固定版本随模块行首标注。**版本以 §1.5「模块/ISD 基线」为准**；下表行末 `v0.1.0-draft.N` 为清单登记时点的模块设计版本标签，模块设计升版（如 M004→draft.3、M007→draft.2）不改变 Case ID 与责任摘要，逐行标签可滞后于 §1.5。
> **用例归属（本项目合并方案的补充列）**：M001→`UT-API-*`；M002→`UT-UI-*`；M003→`UT-INF-*`；M004→`UT-MGMT-*`；M005→`UT-OBS-*`；M006→`UT-DIAG-*`；M007→`UT-UTIL-*`；M008→`UT-LOG-*`。

| 来源 ID / 固定版本 | 设计验证项 ID | Case ID | 分类 | 优先级 | 责任摘要（要测什么） | 设计状态 | 上级组合验证入口 |
|---|---|---|---|---|---|---|---|
| M001 http-api §14.1 · `Handler._dispatch` v0.1.0-draft.2 | VRC-API-001 | UT-API-001 | normal | P0 | 分发命中/T-API-01 主路径、统一错误信封与 `X-Request-ID`、健康就绪与空库 not_ready | Designed | 模块测试 / 系统测试 |
| M001 http-api §14.1 · `_dispatch`/`_run` 错误出口 v0.1.0-draft.2 | VRC-API-001 | UT-API-005 | negative | P0 | 未知路由 404；未知异常→500（`unhandled_error` 落日志）；`sqlite3.Error`→503 读路径（`_store_read` 映射 `usage_store_unavailable`） | Designed | 模块测试 / 系统测试 |
| M001 http-api §14.1 · `_int_param`/`_optional_boolean` v0.1.0-draft.2 | VRC-API-001 | UT-API-006 | negative | P1 | 非整数 query 参数→400 `invalid_request`；非布尔开关值→400；布尔/整数合法边界通过 | Designed | 模块测试 / 契约层 |
| M001 http-api §14.1 · `_correlation` v0.1.0-draft.2 | VRC-API-001 | UT-API-007 | normal | P1 | `X-Correlation-ID` 优先回显；无则 `traceparent` W3C 正则提取 32-hex trace-id；皆缺则生成 | Designed | 模块测试 / 系统测试 |
| M001 http-api §14.4 · `sse.response_stream` v0.1.0-draft.2 | VRC-API-003 | UT-API-003 | boundary | P0 | 单帧/事件序列/created 首、terminal 唯一（动态 `response.<status>`）、`[DONE]` | Designed | 契约层 / 系统测试 |
| M001 http-api §14.1 · `Handler._body` v0.1.0-draft.2 | VRC-API-003 | UT-API-009 | boundary | P0 | body >2 MB → 413；非法 JSON → 400；顶层非对象 → 400；`Content-Length` 非整数 → 400 | Designed | 契约层 / 系统测试 |
| M001 http-api §14.5/§14.6 · 静态与健康就绪 v0.1.0-draft.2 | VRC-API-004 | UT-API-004 | security | P1 | 静态资源目录穿越拒绝与 `/readyz` 503（空库 not_ready） | Designed | 模块测试 / 系统测试 |
| M001 http-api §14.1 · `Handler._static` v0.1.0-draft.2 | VRC-API-004 | UT-API-010 | security | P1 | `../` 目录穿越 → 404；mime 与 `Cache-Control`；`/ui/` → `index.html`；`/readyz` 空库 503 | Designed | 模块测试 / 契约层 |
| M001 http-api §14.1 · 契约别名命名空间 v0.1.0-draft.2 | VRC-API-001 | UT-API-011 | normal | P1 | `/tier/admin/v1/*` 别名路由与 `/v1/*` 行为对齐（parity） | Designed | 契约层 / 系统测试 |
| M001 http-api §14.1 · `_UnavailableDiagnostics`/引导 v0.1.0-draft.2 | VRC-API-001 | UT-API-012 | recovery | P1 | `DiagnosticsService` 初始化失败时 fail-open 降级；`bootstrap_error` 置位时 `/healthz`+`/ui/*` 仍可达、`/readyz` →503 | Designed | 模块测试 / 系统测试 |
| M001 http-api §14.1 · `/v1/diagnostics` PATCH v0.1.0-draft.2 | VRC-API-001 | UT-API-013 | negative | P2 | PATCH 未知键 → 400；非布尔开关值 → 400 | Designed | 契约层 / M006 |
| M001 http-api §14.2 · `_auth`/`_auth_either`/`authenticate_any` v0.1.0-draft.2 | VRC-API-002 | UT-API-002 | security | P0 | 访问信任：免登录/bearer 正确与错误/缺失配置 503/`X-Principal-ID`；401 与 403 不可区分存在性 | Designed | 模块测试 / 系统测试 |
| M001 http-api §14.2 · `authorize` 角色选择 v0.1.0-draft.2 | VRC-API-002 | UT-API-008 | security | P0 | data 凭据访问 admin 端点 → 403（分发层）；`_auth_either` admin-first 角色选择；非受信来源缺 `Authorization` → 401 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.1 · `tierState`/`backendState` v0.1.0-draft.2 | VRC-UI-001 | UT-UI-001 | normal | P1 | 5 页加载/tier 与成员状态语义映射（Unknown≠Idle、Disabled 优先、空 tier）/`readyz` 映射/单一数据源 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.1 · `tierState`/`backendState` 行为 v0.1.0-draft.2 | VRC-UI-001 | UT-UI-007 | normal | P1 | `tierState` availability 缺失→Unknown 标签+色调；`backendState` provider-disabled 优先于 deployment 状态 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.2 · `dispatchUiError` v0.1.0-draft.2 | VRC-UI-002 | UT-UI-002 | negative | P0 | 编辑并发 412 stale 保留输入/409 引用/401-403 呈现/429 `Retry-After` 分支 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.2 · `reportLoadFailure` v0.1.0-draft.2 | VRC-UI-002 | UT-UI-008 | negative | P1 | 非列举状态（网络/500）经 `reportLoadFailure` 保留上一屏、标 stale；与 `dispatchUiError` 分工 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.3 · Pause/Resume 确认 v0.1.0-draft.2 | VRC-UI-003 | UT-UI-003 | boundary | P1 | Pause 在 `running>0` 的确认边界、Resume 仅恢复资格、不取消在途 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.5 · `metric`/`usageSummary` v0.1.0-draft.2 | VRC-UI-004 | UT-UI-004 | negative | P0 | 用量 Unknown≠0、版本替换（服务端去重）、503 显式化不显示空表 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.5 · `usageSummary` 分支 v0.1.0-draft.2 | VRC-UI-004 | UT-UI-009 | boundary | P1 | `usageSummary`：not_refreshed/unlimited/Unavailable/percent-null 四态渲染 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.4 · 探测付费确认 v0.1.0-draft.2 | VRC-UI-005 | UT-UI-005 | boundary | P1 | 探测付费确认：未确认不触网（无 POST）、未知结果不自动重复 | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.7 · 诊断页开关 v0.1.0-draft.2 | VRC-UI-006 | UT-UI-006 | normal | P1 | 诊断页 4 tabs、开关关闭→Disabled | Designed | 模块测试 / 系统测试 |
| M002 web-ui §14.1/§14.5 · `statsRange`/`etag`/`fetchProviderModels` v0.1.0-draft.2 | VRC-UI-001 | UT-UI-010 | boundary | P2 | `statsRange` 24h/7d/today/all；`etag()` 格式 `"<id>.v<n>"`；`fetchProviderModels` cache 命中/未命中与失败吞没 | Designed | 模块测试 |
| M003 inference §14.1 · `ResponsesService.create`/`_adapter` v0.1.0-draft.1 | VRC-INF-001 | UT-INF-001 | normal | P0 | Responses 校验与归一：固定 request、缺字段/`store=true`/禁字段、未知 model | Designed | 契约层 / M001 / 系统测试 |
| M003 inference §14.1 · `ResponsesService._validate` v0.1.0-draft.1 | VRC-INF-001 | UT-INF-006 | negative | P0 | 校验顺序与码：未知字段/禁字段→`unsupported_field`（`param`=违规字段名）；`tools` 无能力→`unsupported_request`；`max_output_tokens` 范围/布尔→`invalid_request`；responses 能力 false→`unsupported_model` | Designed | 契约层 / 系统测试 |
| M003 inference §14.2 · `EmbeddingsService.create` v0.1.0-draft.1 | VRC-INF-002 | UT-INF-002 | boundary | P0 | Embeddings：正常/base64、非有限值、非法维数、usage→`prompt_tokens` | Designed | 契约层 / 系统测试 |
| M003 inference §14.2 · `EmbeddingsService.create` 分支 v0.1.0-draft.1 | VRC-INF-002 | UT-INF-007 | negative | P1 | 非法 base64 → 502 `provider_contract_error`；`unsupported_dimensions` 码断言；空向量拒绝 | Designed | 契约层 / 系统测试 |
| M003 inference §14.3 · `UsageRecorder`/terminals v0.1.0-draft.1 | VRC-INF-003 | UT-INF-003 | recovery | P0 | 失败与用量：上游 5xx/超时、两个 terminal、usage 缺失→unknown 不补零、head 单调 | Designed | M-METER / 系统测试 |
| M003 inference §14.3 · `_adapter`/`record_provider_request_id` v0.1.0-draft.1 | VRC-INF-003 | UT-INF-008 | recovery | P1 | 上游 URL/超时错误→503；usage 非整数部分→unknown+NULL；`provider_request_id` 空→no-op（经服务路径）；注入源 `source='injected'` | Designed | M-METER / 系统测试 |
| M003 inference §14.4 · `Router.admit`/`models` v0.1.0-draft.1 | VRC-INF-004 | UT-INF-004 | concurrency | P0 | 准入与目录：占满队列 429、全不健康 503、同等级 FIFO、availability 三态 | Designed | M001 / 系统测试 |
| M003 inference §14.4 · `Router` 限流/快照/模型码 v0.1.0-draft.1 | VRC-INF-004 | UT-INF-009 | boundary | P0 | 队列满/Wait 超时 429+`Retry-After`；`provider RPM`/`min_interval` 节流；`snapshot()` 形状；degraded/unknown→503；`model_unavailable` 码 | Designed | M001 / 系统测试 |
| M003 inference §14.5 · `CON-INFER-005` fail-open v0.1.0-draft.1 | VRC-INF-005 | UT-INF-005 | recovery | P1 | 观测 fail-open / 不二次鉴权：诊断抛错时推理结果不变 | Designed | M-OBS / 系统测试 |
| M004 management §14.1 · `Registry.bootstrap_settings` v0.1.0-draft.2 | VRC-MGMT-001 | UT-MGMT-001 | normal | P0 | 引导与 Secret 引用：合法 settings、重复启动 no-op、空库无 settings→503 `bootstrap_required`、缺节、`env:` 空/`file:` 不存在→503 `bootstrap_invalid` 回滚 | Designed | 启动 / M001 |
| M004 management §14.1 · `bootstrap_settings`/`ensure_fixed_tiers` v0.1.0-draft.2 | VRC-MGMT-001 | UT-MGMT-007 | recovery | P0 | bootstrap 事务中途失败→空库回滚 + not_ready；`ensure_fixed_tiers` 幂等二次补建（与 bootstrap 配置能力不冲突） | Designed | 启动 / M001 |
| M004 management §14.2 · `Registry` CRUD v0.1.0-draft.2 | VRC-MGMT-002 | UT-MGMT-002 | negative | P0 | CRUD 不变量：重复/引用/能力不兼容/冻结等错误路径与 ETag stale(412)、删除被引用、能力编辑冲突回滚（`test_registry.py` 为负向不变量断言，无并发线程） | Designed | M003 / 契约层 |
| M004 management §14.2 · `Registry` 引用删除 v0.1.0-draft.2 | VRC-MGMT-002 | UT-MGMT-008 | negative | P1 | `resource_in_use`：删除被 deployment 引用的 provider / 被 tier 引用的 deployment → 409 | Designed | M003 / 契约层 |
| M004 management §14.3 · `AuditLog`/`OperationalLog` v0.1.0-draft.2 | VRC-MGMT-003 | UT-MGMT-003 | security | P0 | 审计与日志：成功/失败动作落审计、含 Authorization/Secret 脱敏为 `[REDACTED]` | Designed | M002 / 系统测试 |
| M004 management §14.4 · `Admin.page`/`UsageRecorder` v0.1.0-draft.2 | VRC-MGMT-004 | UT-MGMT-004 | boundary | P0 | 分页与清空：首屏后更正、cursor 过期/跨 principal、范围清空计数一致 | Designed | M-METER / 系统测试 |
| M004 management §14.4 · `admin.page`/`reset_usage` v0.1.0-draft.2 | VRC-MGMT-004 | UT-MGMT-009 | boundary | P1 | admin cursor `expires_at` 过期 → `cursor_expired`（400）；usage 快照冻结；`reset_usage` 范围矩阵（model/deployment/both/neither） | Designed | M-METER / 系统测试 |
| M004 management §14.5 · `Admin.probe` v0.1.0-draft.2 | VRC-MGMT-005 | UT-MGMT-005 | normal | P1 | 探测：未确认 400、正常探测、不可达落 `unhealthy` | Designed | M003 适配器 |
| M004 management §14.5 · `probe` 不可达 v0.1.0-draft.2 | VRC-MGMT-005 | UT-MGMT-010 | recovery | P1 | 上游不可达 → `unhealthy` 落库；`probe` 返回含 `may_have_incurred_cost` | Designed | M003 适配器 |
| M004 management §14.6 · `AccountUsage.refresh` v0.1.0-draft.2 | VRC-MGMT-006 | UT-MGMT-006 | negative | P1 | 账号用量：GET 不触网、未确认 POST、凭据缺失、provider 报错→`unavailable`+`error` 快照持久 | Designed | M002 Providers 页 |
| M004 management §14.6 · `AccountUsage.refresh` 分支 v0.1.0-draft.2 | VRC-MGMT-006 | UT-MGMT-011 | negative | P1 | GET 不触网；`not_refreshed`；`credentials_missing`；`provider_api_error`→`unavailable`+`error`（`""` 非 null） | Designed | M002 Providers 页 |
| M005 observability §14.1 · 开关 v0.1.0-draft.6 | VRC-OBS-001 | UT-OBS-001 | normal | P1 | 开关默认关/开/关闭零写入 | Designed | M002 / M006 |
| M005 observability §14.2 · 快照/统计查询 v0.1.0-draft.6 | VRC-OBS-002 | UT-OBS-002 | boundary | P1 | 快照/统计查询与脱敏：字段完整、URL 去 query、存储不可读 503 不空页 | Designed | M003 / M006 |
| M005 observability §14.2 · 快照 URL 脱敏 v0.1.0-draft.6 | VRC-OBS-002 | UT-OBS-006 | security | P1 | 快照端到端 URL 去 query（`?token=` 不落库）；503 `usage_store_unavailable` 不伪装空页 | Designed | M003 / M006 |
| M005 observability §14.3 · 注入与 fail-open v0.1.0-draft.6 | VRC-OBS-003 | UT-OBS-003 | recovery | P1 | 注入与 fail-open：合法/非法注入 400/404、观测库写失败推理不变 | Designed | M003 / M-METER |
| M005 observability §14.4 · trace/关联标识 v0.1.0-draft.6 | VRC-OBS-004 | UT-OBS-004 | normal | P1 | trace 与关联标识：stage 有序、`X-Correlation-ID` 有则回显、去重 request | Designed | M001 / 系统测试 |
| M005 observability §14.4 · `_correlation` traceparent v0.1.0-draft.6 | VRC-OBS-004 | UT-OBS-007 | normal | P1 | `X-Correlation-ID` 有/无回显；`traceparent`→trace-id 提取；无头时缺省 | Designed | M001 / 系统测试 |
| M005 observability §14.5 · trace 时间窗 v0.1.0-draft.6 | VRC-OBS-005 | UT-OBS-005 | boundary | P2 | trace 时间窗查询：分页 `next_cursor` 稳定、越界为空 | Designed | M006 / 系统测试 |
| M006 libdiag §14.1 · 开关 v0.1.0-draft.6 | VRC-DIAG-001 | UT-DIAG-001 | normal | P1 | 开关默认 `{False,False}`、运行时切换、关闭零写入、部分更新保留 | Designed | M005 |
| M006 libdiag §14.2 · 记录与查询 v0.1.0-draft.6 | VRC-DIAG-002 | UT-DIAG-002 | boundary | P1 | 记录与查询：trace/快照/统计字段、URL 去 query、summary 截断、百分位、7 天清理 | Designed | M003 / M005 |
| M006 libdiag §14.2 · `snapshots`/`stats` 分支 v0.1.0-draft.6 | VRC-DIAG-002 | UT-DIAG-005 | boundary | P1 | 快照 `error_summary` 256B UTF-8 字节截断；`snapshot_type` 由 status 判定；开关关→无行；stats 百分位 P50/P95 与 `windows=[]`、`error_4xx/5xx` 分桶 | Designed | M003 / M005 |
| M006 libdiag §14.2/§14.3 · 游标与失败 v0.1.0-draft.6 | VRC-DIAG-002 | UT-DIAG-006 | recovery | P1 | snapshots/traces 非法 cursor → 400 `cursor_expired`；trace 格式 `first_ts|request_id`；correlation 取自 stage detail | Designed | M005 |
| M006 libdiag §14.3 · fail-open v0.1.0-draft.6 | VRC-DIAG-003 | UT-DIAG-003 | recovery | P1 | fail-open：写入失败/初始化失败时推理结果不变、降级运行 | Designed | M003 |
| M006 libdiag §14.3 · 写入失败降级 v0.1.0-draft.6 | VRC-DIAG-003 | UT-DIAG-007 | recovery | P1 | `record_trace`/`record_latency`/`capture_snapshot` 写入失败不阻断；cleanup 失败返回 0；`_UnavailableDiagnostics` 降级 | Designed | M003 |
| M006 libdiag §14.4 · 注入与 traces v0.1.0-draft.6 | VRC-DIAG-004 | UT-DIAG-004 | negative | P0 | 注入与 traces：四类注入、非法类型 400、命中确定、优先级、traces 时间窗/分页 | Designed | M003 / M001 |
| M006 libdiag §14.4 · `stream_wrapper`/优先级 v0.1.0-draft.6 | VRC-DIAG-004 | UT-DIAG-008 | boundary | P1 | `stream_wrapper` 透传 vs 早停 vs 畸形帧；`enabled_stream_injection` 优先级；空 `items` revoke（DELETE） | Designed | M003 / M001 |
| M007 util §14.1 · `Store` 连接/PRAGMA/回收 v0.1.0-draft.1 | VRC-UTIL-001 | UT-UTIL-001 | boundary | P0 | 连接/PRAGMA/回收/安全：`foreign_keys=1`/`wal`、fd 基线、busy、close 异常、world-writable、symlink 拒绝 | Designed | M004 / M-METER / M-OBS |
| M007 util §14.1 · `Store` 边界分支 v0.1.0-draft.1 | VRC-UTIL-001 | UT-UTIL-003 | recovery | P1 | fd 基线（多请求后不泄漏）；busy/lock→`OperationalError`；`close()` 异常上抛；world-writable → `RuntimeWarning` | Designed | M004 / M-METER / M-OBS |
| M007 util §14.2 · `transaction`/`migrate` v0.1.0-draft.1 | VRC-UTIL-002 | UT-UTIL-002 | recovery | P0 | 事务/初始化/拒绝：回滚、幂等 `migrate`、损坏库、版本不匹配、嵌套事务、并发启动、无版本表旧库 | Designed | M004 / M-METER / M-OBS |
| M007 util §14.2 · `migrate`/`_initialize` v0.1.0-draft.1 | VRC-UTIL-002 | UT-UTIL-004 | concurrency | P1 | 损坏文件→`schema_integrity_failed`；迁移中途失败→回滚空库；嵌套事务→`E-UTIL-NESTED-TXN`（409）；并发启动两实例 | Designed | M004 / M-METER / M-OBS |
| M008 log §14.1 · `OperationalLog.record/page` v0.1.0-draft.1 | VRC-LOG-001 | UT-LOG-001 | security | P0 | 脱敏与查询：Bearer/api_key/token 落库 `[REDACTED]`、长度 ≤512、倒序、过滤、`limit` 夹到 200 | Designed | M004 / M002 |
| M008 log §14.1 · `page` 边界 v0.1.0-draft.1 | VRC-LOG-001 | UT-LOG-002 | negative | P1 | `page` 缺 `since`/`until`→400；`page` 存储失败→503 `usage_store_unavailable`；`token=` 与 `api_key` 脱敏用例 | Designed | M004 / M002 |
| M-TOOL 验证工具 `tools/test_report.py`（单元计划 §7 状态映射） | none（工具，非模块 VRC） | UT-TOOL-001 | normal | P1 | 证据链工具：JUnit→状态映射（`passed→PASS`/`failed→FAIL`/`xfailed→BLOCKED` 带原因/`xpassed→XPASS` 不计 PASS/环境 skip→SKIP、计划 skip→NOT_RUN/`error→BLOCKED`）、运行级 SKIP 上限（A≤5/B≤3）、`case_id_from_source`、`build_report` 计数与阻塞口径、`emit_manifests` | Designed | 单元计划 §7 / 证据链 |

**Case 总数：65**（分类：normal 14 / boundary 16 / negative 14 / concurrency 2 / recovery 12 / security 7；Priority P0 23 / P1 39 / P2 3）。其中 8 模块（`M001-M008`）Case 64 个；验证工具（`TOOL` 家族）Case 1 个（`UT-TOOL-001`，不归属模块 VRC，见下）。

**设计验证项覆盖（契约级）**：33 个模块设计 §14 验证项**全部至少一个 Case**——登记覆盖 33/33，无未登记 VRC。**注意**：该 33/33 为**清单登记覆盖**（每个 VRC 至少一个 Case 入清单），不等于"行为级全覆盖"——但**所有行为级未覆盖子项均已按 §4 定稿为 Tailored-N/A（非 Gap）**：M002 `VRC-UI-001..006` 的静态/契约子项由 `UT-UI-001..010` 承接，纯视觉子项（tabs/Disabled 渲染）因本项目无浏览器/JS 宿主定稿 N/A（见 §4，取代原 G-UT-3）；M005 视觉子项同裁决（取代原 G-UT-4）。故「33/33」= 清单登记覆盖，行为级以此 N/A 裁决为准。逐 VRC 覆盖：`VRC-API-001` 7、`VRC-API-002` 2、`VRC-API-003` 2、`VRC-API-004` 2、`VRC-UI-001` 3、`VRC-UI-002` 2、`VRC-UI-003` 1、`VRC-UI-004` 2、`VRC-UI-005` 1、`VRC-UI-006` 1、`VRC-INF-001` 2、`VRC-INF-002` 2、`VRC-INF-003` 2、`VRC-INF-004` 2、`VRC-INF-005` 1、`VRC-MGMT-001` 2、`VRC-MGMT-002` 2、`VRC-MGMT-003` 1、`VRC-MGMT-004` 2、`VRC-MGMT-005` 2、`VRC-MGMT-006` 2、`VRC-OBS-001` 1、`VRC-OBS-002` 2、`VRC-OBS-003` 1、`VRC-OBS-004` 2、`VRC-OBS-005` 1、`VRC-DIAG-001` 1、`VRC-DIAG-002` 3、`VRC-DIAG-003` 2、`VRC-DIAG-004` 2、`VRC-UTIL-001` 2、`VRC-UTIL-002` 2、`VRC-LOG-001` 2。**工具 Case `UT-TOOL-001` 不映射任何模块 VRC**（工具非产品行为）；`M-TOOL` 不计入 33 个模块 VRC 分母，模块 VRC 覆盖仍为 33/33。

> **unit-case 文档映射（清单登记 65 Case，文档 65/65 已建）**：`UT-API-001..004`、`UT-UI-001..006`、`UT-INF-001..005`、`UT-MGMT-001..006`、`UT-OBS-001..005`、`UT-DIAG-001..004`、`UT-UTIL-001..002`、`UT-LOG-001` 为原有 33 份；其后**新增 31 个 Case ID**（`UT-API-005..013`、`UT-UI-007..010`、`UT-INF-006..009`、`UT-MGMT-007..011`、`UT-OBS-006..007`、`UT-DIAG-005..008`、`UT-UTIL-003..004`、`UT-LOG-002`），其 `tests.unit-case` 文档已建齐（`docs/70_verification/specifications/unit-case-UT-*.md`），保留原 ID/VRC 归属；本轮再补登**工具 Case `UT-TOOL-001`**（`tools/test_report.py` 证据链工具，文档 `unit-case-UT-TOOL-001.md`），使登记 Case 总数为 65。**注意**：文档已建 ≠ 全层闭合；首个 Run `run-20260930-01`（341 PASS）已录制，逐 Case Verdict 以 Run 报告为准。逐 Case 实现状态以对应 unit-case 文档 §7 为准（本清单新增 Case 的实现状态由各自文档声称，本表设计状态仍为 `Designed`）。

## 4. 不适用与缺口裁决

> **本表无具名 Gap**：原 `G-UT-1`（Run 证据）/`G-UT-2`（`tests.asset-design`）/`G-UT-5`（损坏库映射）已按事实**修复/覆盖关闭**；原 `G-UT-3`/`G-UT-4`（UI/OBS 视觉）因无浏览器宿主**定稿 Tailored-N/A**（权威 `std-tailoring`＋系统方案 §4）。模块级 VRC 的行为级承接方逐项指向 `llmtier-unit-test-scheme` §3 具体 Case。

| 来源 ID / 事实依据 | 裁决（Tailored-N/A / 已修复 / 已覆盖） | Owner / 权威与恢复条件 |
|---|---|---|
| 模块组装后的进程级流程、systemd/反向代理、Piko 联调 | Tailored-N/A（本层不测；各模块设计 §14「父级组合验证交接」已列承接方） | 归系统测试方案（`llmtier-system-test-scheme`）；本项目未采用独立模块测试层（无 `tests.module-test-scheme`），模块级 VRC 行为承接见系统方案 §4 裁决 |
| 真实上游 provider 协议与 wire 互操作、浏览器 E2E | Tailored-N/A（本层不测；系统方案已承接） | 归契约层与 `llmtier-system-test-scheme` |
| performance / endurance 分类 | Tailored-N/A（本层不纳入；见 §2 裁剪依据） | 归系统测试方案 |
| M002 web-ui 六项 VRC（`VRC-UI-001..006`）的**行为级**（非字符串契约，即真实 JS 执行）断言 | **Tailored-N/A（定稿；非 Gap）** | Owner：M002 web-ui。**权威**：`std-tailoring.md` `LT-TL-013`（单服务、不引入第二宿主）＋系统方案 §4（`VRC-UI-001..006` 定稿 Tailored-N/A）＋本项目 harness 无浏览器/JS 宿主（全仓无 node/jsdom/playwright/selenium）。**已覆盖部分（真实现有宿主）**：模块级 VRC-UI-001..006 的静态/契约子项由 `UT-UI-001..010`（`tests/unit/v03/test_webui_contract.py`）承接——含 `UT-UI-001`（5 页/tier 状态/readyz 映射/图标 sprite/无 bearer 存储）、`UT-UI-002/008`（错误分派与 load 失败保屏）、`UT-UI-003`（pause/resume 复用 deployment PATCH）、`UT-UI-004/009`（Unknown≠0/usageSummary 四态）、`UT-UI-005`（探测付费确认/gated POST）、`UT-UI-006`（诊断页 4 tabs/Disabled）、`UT-UI-007/010`（状态优先级/etag/statsRange）。**未覆盖的纯视觉子项**（tabs/Disabled 的渲染像素）**定稿 N/A**：无 JS 宿主无法驱动，恢复条件＝引入浏览器/JS 宿主后由单元层升级为行为断言。`std-tailoring` 已记录。 |
| M005 observability 的浏览器呈现（诊断页 tabs/Disabled 视觉） | **Tailored-N/A（定稿；非 Gap）** | Owner：M005（视觉）/M002。同上（无浏览器/JS 宿主）；行为级已由 `UT-OBS-001..007`（开关/查询脱敏/注入 fail-open/trace 关联/时间窗）单元承接，视觉子项无宿主故 N/A。与 `VRC-UI-*` 同一裁决，`std-tailoring` 已记录；恢复条件＝引入浏览器/JS 宿主后重评。 |
| 替身契约文档 `tests.asset-design`（`FakeAdapter`） | **已修复（G-UT-2 关闭）** | LLMTier。**关闭事实**：已建立 `llmtier-unit-fakes`（`docs/70_verification/assets/llmtier-unit-fakes.md`，Template `tests.asset-design@0.2.2`，`Implemented`/`Unverified`），覆盖 `FakeAdapter`/`AppFixture` 的 §2 行为契约、§3 可测试性依赖、§4 实现耦合、§5 自检与 §6 状态；§1.6 与 §1.7 已引用其 ID。`FakeResponse` 在资产 §2/§3 明示为各测试模块本地 stub、非本资产成员。仅余自检 Run 录制（记于资产 §7，与 G-UT-1 同批）。 |
| 单元测试正式报告与 Run 证据 | **已修复（G-UT-1 关闭）** | LLMTier。**关闭事实**：已真实执行 `tests/unit/v03`，产出 Run `tests/unit/v03/reports/run-20260930-01`（`junit.xml`＋`test-run.env`（pin `git_commit/schema_version/openapi_version`）＋`case-status.json`（PASS 341/0 FAIL/0 BLOCKED）＋逐 Case `manifest.json`）。单元层首次录制 Run 已落地；正式 `tests.unit-test-report` 的 Markdown 汇总在 Gate 前按计划 §8 依此 Run 生成。 |
| `UT-UTIL-004` 损坏文件的 envelope code（`CorruptStoreTests`） | **已覆盖（G-UT-5 关闭；非 Gap）** | LLMTier。**关闭事实**：损坏库**不被静默接受**由 `tests/unit/v03/test_store_gaps.py::CorruptStoreTests::test_corrupt_file_raises` 断言（抛 `ApiError` 或 `sqlite3.DatabaseError`）；`schema_integrity_failed` 的**确定性映射**由同文件 `IntegrityMappingTests::test_integrity_failure_is_503` 覆盖（`PRAGMA integrity_check != ok` → 503 `schema_integrity_failed`）。即：坏 sqlite 头/页由 `DatabaseError` 直接上抛（非静默）、完整性失败走映射，两条路径均有真实断言，无需新 Case。 |
| `_static` mime/`Cache-Control` 与 `/ui/` exact 字节 | Tailored-N/A（表现层细节由系统层契约测试锁定） | 归系统/契约层；单元层只断言 404 穿越与 `index.html` 命中（`UT-API-010`） |

## 5. 文档联动与清单变更规则

- 方案冻结与变更规则：清单随各模块设计/ISD 基线冻结；新增 Case 先在本清单登记再建 `tests.unit-case` 文档；VRC 变更时同步 §3 与附录 A；Case ID 一经登记不复用、不改名。
- 与 case-design / 计划的同步规则：Case 文档 ID＝Case ID；计划构成表引用本方案版本；本方案合并 8 模块，逐模块切片由 Case ID 前缀承担。
- 新增 Case 的文档状态：本版新增的 `UT-API-005..013`、`UT-UI-007..010`、`UT-INF-006..009`、`UT-MGMT-007..011`、`UT-OBS-006..007`、`UT-DIAG-005..008`、`UT-UTIL-003..004`、`UT-LOG-002` 共 31 个 Case 已入本清单（§3），其 `tests.unit-case` 文档现已建齐于 `docs/70_verification/specifications/`；另补登工具 Case `UT-TOOL-001`（`tools/test_report.py` 证据链工具，文档 `unit-case-UT-TOOL-001.md`）。各 Case 的实现状态以对应文档 §7 为准，执行与 Verdict 归 Run 报告（首个 Run `run-20260930-01` 已录）。
- 新增 Case 示例：新增 `UT-INF-010`（尾随字节）先入本清单再建 `tests.unit-case` 文档；单元计划引用本方案 `0.1.0-draft.8`。

## 附录 A. 本层设计验证项 VRC 汇集（对照用）

| 设计验证项 ID | 要验证什么（名称/责任） | 设计来源 | §3 Case 覆盖 |
|---|---|---|---|
| VRC-API-001 | 分发/错误/资源 | `http-api-isd` §9.1.1 / `http-api-design` §14.1 | UT-API-001/005/006/007/011/012/013 |
| VRC-API-002 | 鉴权 | `http-api-isd` §9.1.2 / `http-api-design` §14.2 | UT-API-002/008 |
| VRC-API-003 | body 与 SSE | `http-api-isd` §9.1.3 / `http-api-design` §14.3/§14.4 | UT-API-003/009 |
| VRC-API-004 | 静态与健康 | `http-api-isd` §9.1.4 / `http-api-design` §14.5/§14.6 | UT-API-004/010 |
| VRC-UI-001 | 加载与状态 | `web-ui-isd` §9.1.1 / `web-ui-design` §14.1 | UT-UI-001/007/010 |
| VRC-UI-002 | 编辑/鉴权 | `web-ui-isd` §9.1.2 / `web-ui-design` §14.2 | UT-UI-002/008 |
| VRC-UI-003 | Pause 边界 | `web-ui-isd` §9.1.3 / `web-ui-design` §14.3 | UT-UI-003 |
| VRC-UI-004 | 用量未知不填零 | `web-ui-isd` §9.1.4 / `web-ui-design` §14.5 | UT-UI-004/009 |
| VRC-UI-005 | 探测付费确认 | `web-ui-isd` §9.1.5 / `web-ui-design` §14.4 | UT-UI-005 |
| VRC-UI-006 | 诊断页 | `web-ui-isd` §9.1.6 / `web-ui-design` §14.7 | UT-UI-006 |
| VRC-INF-001 | 推理与流式契约 | `inference-isd` §9.1.1 / `inference-design` §14.1 | UT-INF-001/006 |
| VRC-INF-002 | 向量化契约 | `inference-isd` §9.1.2 / `inference-design` §14.2 | UT-INF-002/007 |
| VRC-INF-003 | 失败与用量 | `inference-isd` §9.1.3 / `inference-design` §14.3 | UT-INF-003/008 |
| VRC-INF-004 | 准入与目录 | `inference-isd` §9.1.4 / `inference-design` §14.4 | UT-INF-004/009 |
| VRC-INF-005 | 观测 fail-open | `inference-isd` §9.1.5 / `inference-design` §14.5 | UT-INF-005 |
| VRC-MGMT-001 | 引导与 Secret 引用 | `management-isd` §9.1.1 / `management-design` §14.1 | UT-MGMT-001/007 |
| VRC-MGMT-002 | CRUD 与不变量 | `management-isd` §9.1.2 / `management-design` §14.2 | UT-MGMT-002/008 |
| VRC-MGMT-003 | 审计与日志 | `management-isd` §9.1.3 / `management-design` §14.3 | UT-MGMT-003 |
| VRC-MGMT-004 | 分页与清空 | `management-isd` §9.1.4 / `management-design` §14.4 | UT-MGMT-004/009 |
| VRC-MGMT-005 | 探测 | `management-isd` §9.1.5 / `management-design` §14.5 | UT-MGMT-005/010 |
| VRC-MGMT-006 | 账号用量 | `management-isd` §9.1.6 / `management-design` §14.6 | UT-MGMT-006/011 |
| VRC-OBS-001 | 开关 | `observability-isd` §9.1.1 / `observability-design` §14.1 | UT-OBS-001 |
| VRC-OBS-002 | 快照/统计查询与脱敏 | `observability-isd` §9.1.2 / `observability-design` §14.2 | UT-OBS-002/006 |
| VRC-OBS-003 | 注入与 fail-open | `observability-isd` §9.1.3 / `observability-design` §14.3 | UT-OBS-003 |
| VRC-OBS-004 | trace/traces 与关联标识 | `observability-isd` §9.1.4 / `observability-design` §14.4 | UT-OBS-004/007 |
| VRC-OBS-005 | trace 时间窗 | `observability-isd` §9.1.5 / `observability-design` §14.5 | UT-OBS-005 |
| VRC-DIAG-001 | 开关 | `libdiag-isd` §9.1.1 / `libdiag-design` §14.1 | UT-DIAG-001 |
| VRC-DIAG-002 | 记录与查询 | `libdiag-isd` §9.1.2 / `libdiag-design` §14.2 | UT-DIAG-002/005/006 |
| VRC-DIAG-003 | fail-open | `libdiag-isd` §9.1.3 / `libdiag-design` §14.3 | UT-DIAG-003/007 |
| VRC-DIAG-004 | 注入与 traces | `libdiag-isd` §9.1.4 / `libdiag-design` §14.4 | UT-DIAG-004/008 |
| VRC-UTIL-001 | 连接/PRAGMA/回收/安全 | `util-isd` §9.1.1 / `util-design` §14.1 | UT-UTIL-001/003 |
| VRC-UTIL-002 | 事务/初始化/拒绝 | `util-isd` §9.1.2 / `util-design` §14.2 | UT-UTIL-002/004 |
| VRC-LOG-001 | 脱敏与查询 | `log-isd` §9.1.1 / `log-design` §14.1 | UT-LOG-001/002 |
