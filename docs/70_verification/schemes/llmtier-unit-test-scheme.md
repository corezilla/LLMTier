<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Unit Test Scheme

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-unit-test-scheme` |
| Document Version | `0.1.0-draft.1` |
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

> 本方案绑定软件模块集合：`design_object_id` 字段在本项目按本方案约定记录为 `M001-M008`（见 §1）；单元设计 ID/版本在 §1 固定；实现状态与执行结果不进本方案。
> 本文档对设计验证项（VRC）的引用规则：只引用 ID 与状态，不复制定义/判据/Owner；判据与契约权威归 design 与 tests.asset-design，本文档若细化执行断言需在变更时回溯设计修订并记录。
> **裁剪说明（tailored）**：模板默认“本方案绑定单一软件模块”。本项目按用户授权将 8 个模块的单元层 Case 清单合并为一份项目级方案（`M001-M008` 一次登记），逐模块归属由 §3 的「来源 ID / 用例归属」列承担；该合并只关清单登记位置，不改变 Case 与模块设计 VRC 的一一追溯。裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

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

- 被测对象、设计基线与父对象：LLMTier 源码 `src/http_api`(M001)、`src/web_ui`(M002)、`src/inference`(M003)、`src/management`(M004)、`src/observability`(M005)、`src/libdiag`(M006)、`src/util`(M007)、`src/log`(M008)；父对象为软件系统设计 `llmtier-system-design`；模块/ISD 基线见 §1.5。
- 本阶段测试边界（真实组成 / 边界替身）：被测模块内部为真实代码（`Store` 隔离临时库、`Registry`/`Router`/`UsageRecorder`/`AuditLog`/`OperationalLog`/`DiagnosticsService` 真实实例）；边界替身仅用于外部 collaborator——上游 provider 用进程内 `FakeAdapter`（`tests/unit/v03/fakes.py`）、HTTP 层测试用 `ThreadingHTTPServer` 绑 `127.0.0.1:0` 的 loopback 测试实例、`FakeResponse` 代 provider HTTP 响应；替身契约待 `tests.asset-design` 承载（见 §1.6）。
- 不证明的组合保证及承接入口：组装后的进程级流程（启动/systemd、反向代理、Piko 联调）、wire 互操作与 OpenAPI 端到端一致性、浏览器 E2E、真实上游 provider 协议；承接＝模块测试方案/计划（`tests.module-test-scheme`/`-plan`）、契约层与系统测试方案（`llmtier-system-test-scheme`）。
- 被测函数集合（每个 Case 的具体入口见对应 unit-case §2）：`src/http_api`（`errors.py`、`auth.py`、`sse.py`、`health.py`、`app.py`）、`src/inference`（`responses.py`、`embeddings.py`、`models.py`、`routing.py`、`usage.py`、`providers/openai.py`）、`src/management`（`registry.py`、`admin.py`、`audit.py`、`account_usage.py`）、`src/libdiag`（`diagnostics.py`、`injections.py`、`snapshots.py`、`stats.py`、`traces.py`、`settings.py`）、`src/util`（`store.py`）、`src/log`（`logs.py`）、`src/web_ui`（`index.html`/`app.js` 契约）。

## 1.5 测试方法与测试设计技术

- **模块/ISD 基线**：M001 `http-api` v0.1.0-draft.2 / ISD `http-api-isd`；M002 `web-ui` v0.1.0-draft.2 / `web-ui-isd`；M003 `inference` v0.1.0-draft.1 / `inference-isd`；M004 `management` v0.1.0-draft.2 / `management-isd`；M005 `observability` v0.1.0-draft.6 / `observability-isd`；M006 `libdiag` v0.1.0-draft.6 / `libdiag-isd`；M007 `util` v0.1.0-draft.1 / `util-isd`；M008 `log` v0.1.0-draft.1 / `log-isd`。设计要求见各模块设计 §14 与 ISD §9.1。

| Case 家族 | 测试设计技术 | 环境类型引用 | 自动化与判定规则 |
|---|---|---|---|
| normal | 等价类划分（合法请求/合法状态机迁移） | ENV-1 隔离 Python 临时库 | `pytest -q` 全量；单次执行判 PASS/FAIL |
| | · 注入：固定 request、固定 tier/deployment、固定 fixture（`AppFixture.seed`） | | · 断言公开返回/落库行与独立期望严格相等 |
| boundary | 边界值（上限/零/空/刚好满、长度边界） | ENV-1 隔离 Python 临时库 | 单 Case `-k` 选择；超界→既定错误码 |
| | · 注入：空库、`limit` 上限、message 512 字节边界、`limit=1000`、`running>0` 边界 | | · 边界断言在「接受」与「拒绝」间二选一，无第三态 |
| negative | 错误猜测 + 反例驱动（非法字段/凭据/引用/类型） | ENV-1 隔离 Python 临时库 | 一次性判 PASS/FAIL；不掩盖 FAIL |
| | · 注入：未知 model、缺字段、非布尔开关、非法 cursor、未知 group_by、删除被引用 | | · 每错误分支独立 Case，错误码/类型逐一断言 |
| concurrency | 线程对偶 + 受控时序（`threading`/`ThreadingHTTPServer`） | ENV-1 隔离 Python 临时库 + ENV-2 loopback 测试 HTTP 实例 | 固定种子/确定性交错；一次失败标 INVALID 复现 |
| | · 注入：并发 PATCH（ETag）、同 tier 第二个请求 FIFO、并发启动两实例 | | · 失败须记录并发交错样本；不靠“重跑通过”掩盖 |
| recovery | 故障注入 + 异常路径恢复（`LLMTIER_SLOW_ADAPTER_DELAY`/写入失败/断开） | ENV-1 隔离 Python 临时库 | 异常路径后断言无半写/回滚/推理不变 |
| | · 注入：上游 5xx/超时、库写失败、客户端断开、迁移中途失败 | | · 验证回滚/unknown 不补零/无部分表 |
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
- **替身形态**：`FakeAdapter` 为进程内 fake（只代返回值/异常/终态），`FakeResponse` 为 provider HTTP 响应 stub；不用 mock 框架打桩被测自身。
- **替身保真度与契约**：替身契约与自检归 `tests.asset-design`（一资产一文档），本方案与 Case 只引用其 ID 不复制行为。当前 `tests/asset-design` 尚未建立实例（见 §4 Gap G-UT-2）。
- **交互断言 vs 返回值断言**：优先断言公开返回值、落库行与 wire 信封；必要时断言 `ApiError` 类型/错误码与关键调用序，不耦合被测内部实现。
- **反模式（逐项排除）**：不 mock 被测拥有的接口；不 mock 值对象/纯数据（dict/JSON 直接构造）；不为凑覆盖率而 mock；不过度断言内部细节。

| 协作者类型 | 替身形态 | 替身契约文档（tests.asset-design） | 决策理由 |
|---|---|---|---|
| 上游 provider adapter | 进程内 fake（`FakeAdapter`） | 待建（Gap G-UT-2，候选 ID `FAKE-LLMTIER-ADAPTER`） | 真实 provider 不可控；fake 只代返回值/异常/终态 |
| provider HTTP 响应 | stub（`FakeResponse`） | 待建（Gap G-UT-2） | 只代 `probe(models)` 的 HTTP 响应体 |
| SQLite 存储 | 真实 `Store` + 临时隔离库 | 不适用（真实依赖） | 存储是被测对象一部分，用真实实现 + 密隔离 |
| HTTP 监听端口 | 真实 `ThreadingHTTPServer`（`127.0.0.1:0`） | 不适用（真实网络） | 端口是真实路径，仅绑 loopback 临时端口 |
| Web UI 静态产物 | 真实文件读取（`Path.read_text`） | 不适用（真实产物） | UI 契约对真实 `index.html`/`app.js` 断言 |

## 1.7 测试环境类型（方案定义）

| 环境类型 | 行为/真伪 | 契约文档 | 在本层用例中的角色 |
|---|---|---|---|
| ENV-1 隔离 Python 临时库 | 真实：`tempfile.TemporaryDirectory` + `Application`（`Store`+`Registry`+服务）；每 Case 新建、`tearDown` 销毁 | — | 绝大多数单元 Case 的默认环境（`tests/unit/v03/fakes.py::AppFixture`） |
| | · 契约：真实 SQLite 落库；`settings.json` 由 fixture 写入；不复用跨 Case 状态 | | · 用法：`setUp` 建 `AppFixture`、`tearDown` `close()` |
| ENV-2 loopback 测试 HTTP 实例 | 真实：`ThreadingHTTPServer((127.0.0.1, 0), handler_factory(app))` | — | HTTP/wire 契约层 Case（诊断 HTTP、鉴权） |
| | · 契约：真实 socket、临时端口、真实 handler 栈；不代被测 `app.py` 逻辑 | | · 用法：`setUpClass` 起服务、`tearDownClass` shutdown |
| ENV-3 provider 进程内 fake | fake：`FakeAdapter` 只代返回值/异常/终态 | 待建（Gap G-UT-2） | 上游交互/失败注入 Case |
| | · 契约：`complete`/`embed`/`probe` 返回可配置结果；不证明真实 provider 协议 | | · 用法：`ResponsesService(..., adapter=FakeAdapter(...))` |

**总体说明**：Python 3.14（`python3 -m pytest`），`PYTHONPATH=src`；fixture 来源为 `tests/unit/v03/fakes.py`（`AppFixture`/`FakeAdapter`）；替身资产归 `tests.asset-design`（待建）；CI 入口为 `PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`（或按 `-k` 选单 Case）；并发隔离按临时库实例；缺 Python/依赖记 Blocked，不静默换环境。

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
> **分母来源**：8 个模块设计 §14 / ISD §9.1 声明的验证项，共 33 项——M001 `VRC-API-001..004`、M002 `VRC-UI-001..006`、M003 `VRC-INF-001..005`、M004 `VRC-MGMT-001..006`、M005 `VRC-OBS-001..005`、M006 `VRC-DIAG-001..004`、M007 `VRC-UTIL-001..002`、M008 `VRC-LOG-001`。**一个 VRC 一条记录、一 Case**（来源 ID＝VRC；被测函数集合在对应 unit-case §2/§7 展开）。
> **用例归属（本项目合并方案的补充列）**：M001→`UT-API-*`；M002→`UT-UI-*`；M003→`UT-INF-*`；M004→`UT-MGMT-*`；M005→`UT-OBS-*`；M006→`UT-DIAG-*`；M007→`UT-UTIL-*`；M008→`UT-LOG-*`。

| 来源 ID / 固定版本 | 设计验证项 ID | Case ID | 分类 | 优先级 | 责任摘要（要测什么） | 设计状态 | 上级组合验证入口 |
|---|---|---|---|---|---|---|---|
| M001 `http-api` v0.1.0-draft.2 | VRC-API-001 | UT-API-001 | normal | P0 | 路由分发/未知路由/统一错误信封/健康就绪与空库 not_ready | Designed | 模块测试 / 系统测试 |
| M001 `http-api` v0.1.0-draft.2 | VRC-API-002 | UT-API-002 | security | P0 | 访问信任：免登录/bearer 正确与错误/data 访问 admin 403/不泄露存在性 | Designed | 模块测试 / 系统测试 |
| M001 `http-api` v0.1.0-draft.2 | VRC-API-003 | UT-API-003 | boundary | P0 | body 上限 413/非法 JSON 400 与 SSE 单帧/事件序列/terminal 唯一 | Designed | 模块测试 / 契约层 |
| M001 `http-api` v0.1.0-draft.2 | VRC-API-004 | UT-API-004 | security | P1 | 静态资源目录穿越拒绝与 `/readyz` 503 | Designed | 模块测试 / 系统测试 |
| M002 `web-ui` v0.1.0-draft.2 | VRC-UI-001 | UT-UI-001 | normal | P1 | 5 页加载/tier 与成员状态语义/`readyz` 映射/单一数据源 | Designed | 模块测试 / 系统测试 |
| M002 `web-ui` v0.1.0-draft.2 | VRC-UI-002 | UT-UI-002 | negative | P0 | 编辑并发 412 stale 保留输入/409 引用/401-403 呈现 | Designed | 模块测试 / 系统测试 |
| M002 `web-ui` v0.1.0-draft.2 | VRC-UI-003 | UT-UI-003 | boundary | P1 | Pause 在 `running>0` 的确认边界、Resume 仅恢复资格、不取消在途 | Designed | 模块测试 / 系统测试 |
| M002 `web-ui` v0.1.0-draft.2 | VRC-UI-004 | UT-UI-004 | negative | P0 | 用量 Unknown≠0、版本替换、503 显式化不显示空表 | Designed | 模块测试 / 系统测试 |
| M002 `web-ui` v0.1.0-draft.2 | VRC-UI-005 | UT-UI-005 | boundary | P1 | 探测付费确认：未确认不触网、未知结果不自动重复 | Designed | 模块测试 / 系统测试 |
| M002 `web-ui` v0.1.0-draft.2 | VRC-UI-006 | UT-UI-006 | normal | P1 | 诊断页 4 tabs、开关关闭→Disabled | Designed | 模块测试 / 系统测试 |
| M003 `inference` v0.1.0-draft.1 | VRC-INF-001 | UT-INF-001 | normal | P0 | Responses 校验与归一：固定 request、缺字段/`store=true`/禁字段、未知 model | Designed | 契约层 / M001 / 系统测试 |
| M003 `inference` v0.1.0-draft.1 | VRC-INF-002 | UT-INF-002 | boundary | P0 | Embeddings：正常/base64、非有限值、非法维数、usage→`prompt_tokens` | Designed | 契约层 / 系统测试 |
| M003 `inference` v0.1.0-draft.1 | VRC-INF-003 | UT-INF-003 | recovery | P0 | 失败与用量：上游 5xx/超时、两个 terminal、usage 缺失→unknown 不补零、head 单调 | Designed | M-METER / 系统测试 |
| M003 `inference` v0.1.0-draft.1 | VRC-INF-004 | UT-INF-004 | concurrency | P0 | 准入与目录：占满队列 429、全不健康 503、同等级 FIFO、availability 三态 | Designed | M001 / 系统测试 |
| M003 `inference` v0.1.0-draft.1 | VRC-INF-005 | UT-INF-005 | recovery | P1 | 观测 fail-open / 不二次鉴权：推理结果不变 | Designed | M-OBS / 系统测试 |
| M004 `management` v0.1.0-draft.2 | VRC-MGMT-001 | UT-MGMT-001 | normal | P0 | 引导与 Secret 引用：合法 settings、重复启动、缺节、`env:` 空/`file:` 不存在→503 回滚 | Designed | 启动 / M001 |
| M004 `management` v0.1.0-draft.2 | VRC-MGMT-002 | UT-MGMT-002 | negative | P0 | CRUD 不变量：并发 PATCH、删除被引用、能力不兼容、`Embedding-v1` 冻结 | Designed | M003 / 契约层 |
| M004 `management` v0.1.0-draft.2 | VRC-MGMT-003 | UT-MGMT-003 | security | P0 | 审计与日志：成功/失败动作落审计、含 Authorization/Secret 脱敏 | Designed | M002 / 系统测试 |
| M004 `management` v0.1.0-draft.2 | VRC-MGMT-004 | UT-MGMT-004 | boundary | P0 | 分页与清空：首屏后更正、cursor 过期/跨 principal、范围清空计数一致 | Designed | M-METER / 系统测试 |
| M004 `management` v0.1.0-draft.2 | VRC-MGMT-005 | UT-MGMT-005 | normal | P1 | 探测：未确认 400、正常探测、不可达落 `unhealthy` | Designed | M003 适配器 |
| M004 `management` v0.1.0-draft.2 | VRC-MGMT-006 | UT-MGMT-006 | negative | P1 | 账号用量：GET 不触网、未确认 POST、凭据缺失、provider 报错→`unavailable`+`error` 快照持久 | Designed | M002 Providers 页 |
| M005 `observability` v0.1.0-draft.6 | VRC-OBS-001 | UT-OBS-001 | normal | P1 | 开关默认关/开/关闭零写入 | Designed | M002 / M006 |
| M005 `observability` v0.1.0-draft.6 | VRC-OBS-002 | UT-OBS-002 | boundary | P1 | 快照/统计查询与脱敏：字段完整、URL 去 query、存储不可读 503 不空页 | Designed | M003 / M006 |
| M005 `observability` v0.1.0-draft.6 | VRC-OBS-003 | UT-OBS-003 | recovery | P1 | 注入与 fail-open：合法/非法注入 400/404、观测库写失败推理不变 | Designed | M003 / M-METER |
| M005 `observability` v0.1.0-draft.6 | VRC-OBS-004 | UT-OBS-004 | normal | P1 | trace 与关联标识：stage 有序、`X-Correlation-ID` 有则回显、去重 request | Designed | M001 / 系统测试 |
| M005 `observability` v0.1.0-draft.6 | VRC-OBS-005 | UT-OBS-005 | boundary | P2 | trace 时间窗查询：分页 `next_cursor` 稳定、越界为空 | Designed | M006 / 系统测试 |
| M006 `libdiag` v0.1.0-draft.6 | VRC-DIAG-001 | UT-DIAG-001 | normal | P1 | 开关默认 `{False,False}`、运行时切换、关闭零写入、部分更新保留 | Designed | M005 |
| M006 `libdiag` v0.1.0-draft.6 | VRC-DIAG-002 | UT-DIAG-002 | boundary | P1 | 记录与查询：trace/快照/统计字段、URL 去 query、summary 截断、百分位、7 天清理 | Designed | M003 / M005 |
| M006 `libdiag` v0.1.0-draft.6 | VRC-DIAG-003 | UT-DIAG-003 | recovery | P1 | fail-open：写入失败/初始化失败时推理结果不变、降级运行 | Designed | M003 |
| M006 `libdiag` v0.1.0-draft.6 | VRC-DIAG-004 | UT-DIAG-004 | negative | P0 | 注入与 traces：四类注入、非法类型 400、命中确定、优先级、traces 时间窗/分页 | Designed | M003 / M001 |
| M007 `util` v0.1.0-draft.1 | VRC-UTIL-001 | UT-UTIL-001 | boundary | P0 | 连接/PRAGMA/回收/安全：`foreign_keys=1`/`wal`、fd 基线、busy、close 异常、world-writable、symlink 拒绝 | Designed | M004 / M-METER / M-OBS |
| M007 `util` v0.1.0-draft.1 | VRC-UTIL-002 | UT-UTIL-002 | recovery | P0 | 事务/初始化/拒绝：回滚、幂等 `migrate`、损坏库、版本不匹配、嵌套事务、并发启动、无版本表旧库 | Designed | M004 / M-METER / M-OBS |
| M008 `log` v0.1.0-draft.1 | VRC-LOG-001 | UT-LOG-001 | security | P0 | 脱敏与查询：Bearer/api_key/token 落库 `[REDACTED]`、长度 ≤512、倒序、过滤、`limit` 夹到 200 | Designed | M004 / M002 |

## 4. 不适用与缺口裁决

| 来源 ID / 事实依据 | 裁决（Tailored-N/A 或 Gap） | Owner / 恢复条件 |
|---|---|---|
| 模块组装后的进程级流程、systemd/反向代理、Piko 联调 | Tailored-N/A（本层不测；各模块设计 §14「父级组合验证交接」已列承接方） | 归 `tests.module-test-scheme`/系统方案；恢复条件＝模块/系统层建立 |
| 真实上游 provider 协议与 wire 互操作、浏览器 E2E | Tailored-N/A（本层不测；系统方案已承接） | 归契约层与 `llmtier-system-test-scheme` |
| performance / endurance 分类 | Tailored-N/A（本层不纳入；见 §2 裁剪依据） | 归系统测试方案 |
| 替身契约文档 `tests.asset-design`（`FakeAdapter`/`FakeResponse`） | Gap（G-UT-2） | LLMTier / 恢复条件＝补建 `tests/asset-design` 实例并在 §1.6 填 ID；关闭前 §1.6 保持“待建” |
| 单元测试正式报告与 Run 证据 | Gap（G-UT-1） | LLMTier / 恢复条件＝首次真实执行 `tests/unit/v03` 并按计划 §7 生成 `tests.unit-test-report`；当前无录制 Run |

## 5. 文档联动与清单变更规则

- 方案冻结与变更规则：清单随各模块设计/ISD 基线冻结；新增 Case 先在本清单登记再建 `tests.unit-case` 文档；VRC 变更时同步 §3 与附录 A。
- 与 case-design / 计划的同步规则：Case 文档 ID＝Case ID；计划构成表引用本方案版本；本方案合并 8 模块，逐模块切片由 Case ID 前缀承担。
- 新增 Case 示例：新增 `UT-INF-006`（尾随字节）先入本清单再建 `tests.unit-case` 文档；单元计划引用本方案 `0.1.0-draft.1`。

## 附录 A. 本层设计验证项 VRC 汇集（对照用）

| 设计验证项 ID | 要验证什么（名称/责任） | 设计来源 | §3 Case 覆盖 |
|---|---|---|---|
| VRC-API-001 | 分发/错误/资源 | `http-api-isd` §9.1.1 / `http-api-design` §14 | UT-API-001 |
| VRC-API-002 | 鉴权 | `http-api-isd` §9.1.2 / `http-api-design` §14 | UT-API-002 |
| VRC-API-003 | body 与 SSE | `http-api-isd` §9.1.3 / `http-api-design` §14 | UT-API-003 |
| VRC-API-004 | 静态与健康 | `http-api-isd` §9.1.4 / `http-api-design` §14 | UT-API-004 |
| VRC-UI-001 | 加载与状态 | `web-ui-isd` §9.1.1 / `web-ui-design` §14 | UT-UI-001 |
| VRC-UI-002 | 编辑/鉴权 | `web-ui-isd` §9.1.2 / `web-ui-design` §14 | UT-UI-002 |
| VRC-UI-003 | Pause 边界 | `web-ui-isd` §9.1.3 / `web-ui-design` §14 | UT-UI-003 |
| VRC-UI-004 | 用量未知不填零 | `web-ui-isd` §9.1.4 / `web-ui-design` §14 | UT-UI-004 |
| VRC-UI-005 | 探测付费确认 | `web-ui-isd` §9.1.5 / `web-ui-design` §14 | UT-UI-005 |
| VRC-UI-006 | 诊断页 | `web-ui-isd` §9.1.6 / `web-ui-design` §14 | UT-UI-006 |
| VRC-INF-001 | 推理与流式契约 | `inference-isd` §9.1.1 / `inference-design` §14 | UT-INF-001 |
| VRC-INF-002 | 向量化契约 | `inference-isd` §9.1.2 / `inference-design` §14 | UT-INF-002 |
| VRC-INF-003 | 失败与用量 | `inference-isd` §9.1.3 / `inference-design` §14 | UT-INF-003 |
| VRC-INF-004 | 准入与目录 | `inference-isd` §9.1.4 / `inference-design` §14 | UT-INF-004 |
| VRC-INF-005 | 观测 fail-open | `inference-isd` §9.1.5 / `inference-design` §14 | UT-INF-005 |
| VRC-MGMT-001 | 引导与 Secret 引用 | `management-isd` §9.1.1 / `management-design` §14 | UT-MGMT-001 |
| VRC-MGMT-002 | CRUD 与不变量 | `management-isd` §9.1.2 / `management-design` §14 | UT-MGMT-002 |
| VRC-MGMT-003 | 审计与日志 | `management-isd` §9.1.3 / `management-design` §14 | UT-MGMT-003 |
| VRC-MGMT-004 | 分页与清空 | `management-isd` §9.1.4 / `management-design` §14 | UT-MGMT-004 |
| VRC-MGMT-005 | 探测 | `management-isd` §9.1.5 / `management-design` §14 | UT-MGMT-005 |
| VRC-MGMT-006 | 账号用量 | `management-isd` §9.1.6 / `management-design` §14 | UT-MGMT-006 |
| VRC-OBS-001 | 开关 | `observability-isd` §9.1.1 / `observability-design` §14 | UT-OBS-001 |
| VRC-OBS-002 | 快照/统计查询与脱敏 | `observability-isd` §9.1.2 / `observability-design` §14 | UT-OBS-002 |
| VRC-OBS-003 | 注入与 fail-open | `observability-isd` §9.1.3 / `observability-design` §14 | UT-OBS-003 |
| VRC-OBS-004 | trace/traces 与关联标识 | `observability-isd` §9.1.4 / `observability-design` §14 | UT-OBS-004 |
| VRC-OBS-005 | 诊断页 | `observability-isd` §9.1.5 / `observability-design` §14 | UT-OBS-005 |
| VRC-DIAG-001 | 开关 | `libdiag-isd` §9.1.1 / `libdiag-design` §14 | UT-DIAG-001 |
| VRC-DIAG-002 | 记录与查询 | `libdiag-isd` §9.1.2 / `libdiag-design` §14 | UT-DIAG-002 |
| VRC-DIAG-003 | fail-open | `libdiag-isd` §9.1.3 / `libdiag-design` §14 | UT-DIAG-003 |
| VRC-DIAG-004 | 注入与 traces | `libdiag-isd` §9.1.4 / `libdiag-design` §14 | UT-DIAG-004 |
| VRC-UTIL-001 | 连接/PRAGMA/回收/安全 | `util-isd` §9.1.1 / `util-design` §14 | UT-UTIL-001 |
| VRC-UTIL-002 | 事务/初始化/拒绝 | `util-isd` §9.1.2 / `util-design` §14 | UT-UTIL-002 |
| VRC-LOG-001 | 脱敏与查询 | `log-isd` §9.1.1 / `log-design` §14 | UT-LOG-001 |
