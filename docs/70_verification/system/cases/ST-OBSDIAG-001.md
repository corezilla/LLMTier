<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDIAG-001 — 读取诊断开关

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDIAG-001` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDIAG-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDIAG-001`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDIAG-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDIAG-001` / 系统设计 §8 诊断开关接口（/v1/diagnostics） / `VRC-DIAG-001` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-OBSDIAG-001`
- 要测什么（责任展开）：`GET /v1/diagnostics` 读取全局诊断开关：HTTP 200 + 精确 `SwitchState` 字段集/类型（`snapshots_enabled`、`stats_enabled` 均为布尔），纯读、无副作用。
- 明确不测什么 / 失败含义：不证明：本 case 只读、不改变开关，**不证明**开关值对写入的零写入语义（机制 `INV-4`/`CON-OBS-001`，见 ST-OBSDIAG-002 的 PATCH 及其后的写入断言），**不证明**快照/统计/trace 查询（ST-OBSSNAP-001/02、ST-OBSSTATS-001/02、ST-OBSTRACE-001/02），**不证明**别名逐字节等价（ST-OBSALIAS-001），**不证明** `PATCH` 的非法值拒绝（ST-OBSDIAG-003），也**不证明**角色负向（data token 403，由 ST-AUTH-008 及 ST-OBSREQTRACE-003 风格的角色负向承接）。

**目的（被测契约）**：验证 Observability `GET /v1/diagnostics` 的**开关读契约**。被测端点/规则：`GET /v1/diagnostics`，成功返回 `SwitchState`（`snapshots_enabled`、`stats_enabled` 两个必填 JSON 布尔，`additionalProperties:false`）；
认证角色 `admin`；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（401 `authentication_required` / 403 `permission_denied` / 503 `usage_store_unavailable`）。
设计验证项 `VRC-DIAG-001`；机制 `T-OBS-SWITCH`（见[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.1/§5.1，`IF-OBS-API-SWITCH`/`IF-OBS-SWITCH`）；
需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01`/`R-OBS-02`、`CT-ADMIN-001`/`CT-LOG-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；
机器契约 `interfaces/openapi/llmtier.openapi.json`（`SwitchState`，`security=AdminBearerAuth`）；等价别名 `/tier/admin/v1/diagnostics`（同一 handler）。
**不证明什么**：本 case 只读、不改变开关，**不证明**开关值对写入的零写入语义（机制 `INV-4`/`CON-OBS-001`，见 ST-OBSDIAG-002 的 PATCH 及其后的写入断言），**不证明**快照/统计/trace 查询（ST-OBSSNAP-001/02、ST-OBSSTATS-001/02、ST-OBSTRACE-001/02），**不证明**别名逐字节等价（ST-OBSALIAS-001），**不证明** `PATCH` 的非法值拒绝（ST-OBSDIAG-003），也**不证明**角色负向（data token 403，由 ST-AUTH-008 及 ST-OBSREQTRACE-003 风格的角色负向承接）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；`diagnostic_settings` 单行存在（默认 `{snapshots_enabled:false, stats_enabled:false}`）。本 case 不写库、不改开关，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无查询参数）：

  ```http
  GET /v1/diagnostics HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```

  边界/构造点：**无请求体**（GET 不携带 body）；**无查询参数**（`SwitchState` 读取不接受参数，注入无关 query 不在本 case 范围）；凭据固定为 `admin`（`dev-admin`）；不注入故障；不构造非法输入（非法/缺凭据属 ST-AUTH-*，非法 PATCH body 属 ST-OBSDIAG-003）。值的期望**不固定**（开关默认关闭，但 m5air 实际值以读取为准），只断言字段集与类型。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `GET /v1/diagnostics`（上表），`resp = admin_client.get("/v1/diagnostics")`；记录 status、`Content-Type`（`X-Request-ID` 为运行时注入，openapi 未将其声明为 `/v1/diagnostics` 的 200 头，仅作旁证记录、不作契约断言）。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON body，断言其为对象且键集**恰为** `{snapshots_enabled, stats_enabled}`（不多不少；`additionalProperties:false`）。
  5. 断言两键值类型均为 JSON 布尔（`type(v) is bool`，不得把 `0/1` 当 `true/false`）。
  6. （交叉核对，不改变本 case 判定）与别名 `GET /tier/admin/v1/diagnostics` 同凭据下的响应体逐字节比对，作为 ST-OBSALIAS-001 的旁证；本 case 不承担别名等价判定。

**重点关注步骤**：① **字段集精确性**——不是"含两个字段"，而是"键集恰好等于 `SwitchState`"，多一个键即违反 `additionalProperties:false`；② **类型精确性**——`snapshots_enabled`/`stats_enabled` 必须是 JSON 布尔，不能是 `0/1`/字符串；
③ **纯读、无副作用**——GET 不得写 `diagnostic_settings`（不改开关）、不得写审计（机制 §5.1 明确 PATCH 才"副作用=同事务审计"）、不得新增 trace；④ **不得被错误信封冒充**——若返回非 200，需确认是可解释的 `ERR-AUTH-*`/`ERR-STORE`，而非把错误体当 `SwitchState` 读；
⑤ **不依赖开关值**——不对 `true/false` 做业务断言（m5air 实际值未知，默认关）；⑥ **降级判定**——区分"诊断服务降级返回默认 `SwitchState`"（仍 200，PASS）与"存储不可达返回 503 `usage_store_unavailable`"（环境问题，非本 case 的契约 FAIL，见判定）。
自动化入口 `ST-OBSDIAG-001.py` 已实现（落位遵循 §4.9/§8.5）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `SwitchState` 的 wire 形态（不依赖实现的开关值）。
  - HTTP：`200`；响应头 `Content-Type: application/json`（openapi 未为 `/v1/diagnostics` 的 200 声明任何响应头；`X-Request-ID` 为运行时注入、非契约，不列入 Oracle）。
  - body：JSON 对象，键集**恰为** `{snapshots_enabled, stats_enabled}`；两键均存在且为 JSON 布尔。
  - 值域：无额外约束（默认 `{false,false}`，实际值以库中 `diagnostic_settings.singleton=1` 行为准）。
  - **缺失/降级诊断子系统的表现（fail-open 规则）**：按[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.10/§8.1（`CON-OBS-002`/`INV-6`，`DiagnosticsService` 初始化失败时降级运行），实现以 `_UnavailableDiagnostics` 兜底，其 `switches()` 恒返回 `{"snapshots_enabled": false, "stats_enabled": false}`（[`src/http_api/app.py`](../../../../src/http_api/app.py)）。因此**缺失/降级**表现为 `HTTP 200 + {false,false}`——因 Oracle 只约束字段集/类型、观测故障不得制造新的失败面，这**仍是本 case 的 PASS**。反之，若健康实例返回非 200、或返回体不是合法 `SwitchState`（键集不符/类型非 bool/以错误信封冒充），即 **FAIL**。唯一例外是存储层读取异常由 handler 的 `_store_read` 转为 `503 usage_store_unavailable`（`ERR-STORE`）——这是机制 §4.8.1 明示的存储不可达语义，属环境问题按[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则) 判 BLOCKED/SKIP，不作为契约 FAIL。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 `{snapshots_enabled, stats_enabled}` 且两值均为 JSON 布尔（含降级实例返回默认 `{false,false}` 的 fail-open 形态）。
  - **FAIL**：`status!=200` 且存储健康；或 body 键集不等/缺失/多键；或值非 JSON 布尔；或以错误信封冒充 `SwitchState`。
  - **BLOCKED**：测试代码/契约本身问题（如 fixture 写不出、断言逻辑错、`openapi` 语义不清），或**存储层读取异常被 handler 的 `_store_read` 转为 `503 usage_store_unavailable`（`ERR-STORE`，机制 §4.8.1 明示的存储不可达语义，属环境问题）**——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或未命中真实诊断服务却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为纯读，不写 `diagnostic_settings`、不改开关、不创建/修改/删除资源、不写注入项、不新增 trace。退出前确认无未清空的注入项（本 case 不注入）、`/readyz` 仍显示 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令（`curl`/httpx）、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、双 OMLX、`provider_omlx_m5mac` secret）；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；M007 `diagnostic_settings` 单行（`002_observability.sql`）；`SwitchState` 机器契约（`interfaces/openapi/llmtier.openapi.json`）。自动化入口 `ST-OBSDIAG-001.py`（已实现，落位遵循 §4.9/§8.5）。**不依赖**其它 Case；与 ST-OBSALIAS-001（别名 `/tier/admin/v1/diagnostics` 逐字节等价）、ST-OBSDIAG-002（PATCH 更新开关 + 审计）、ST-OBSDIAG-003（PATCH 非法值 400）语义相邻但各自独立执行；角色负向参照 ST-OBSREQTRACE-003 风格（data token → 403）与 ST-AUTH-008。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
