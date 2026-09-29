<!-- STD_DOCUMENT_COVER_BEGIN -->
# OBS-TRACE-01 — trace 列表去重

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `OBS-TRACE-01` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-test-design` |
| Template Version | `2.3.0` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/obs-trace-01.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`OBS-TRACE-01` / 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） / `VRC-DIAG-002` / `normal` / `P1`
- 方案清单登记：`OBS-TRACE-01`
- 要测什么（责任展开）：`GET /v1/diagnostics/traces` 按 `request_id` 去重列出请求 trace：`TracePage` 中同一 `request_id` 至多出现一次，分页排序稳定，每项为合法 `TraceView`（`stages` 有序且 ≥1）。
- 明确不测什么 / 失败含义：不证明 `limit=1` 分页/无效 cursor（OBS-TRACE-02）、不证明单请求全生命周期（OBS-REQTRACE-01）、不证明快照/统计（OBS-SNAP-01、OBS-STATS-01）、不证明别名等价（OBS-ALIAS-06）。**契约一致性警示（须登记）**：`since`/`until`/`deployment_id`/`model` 在 openapi 中 `required:false`，实现亦允许缺省——本 case 可用无参或宽窗请求。

**目的（被测契约）**：验证 Observability `GET /v1/diagnostics/traces` 的**去重 + 稳定分页只读契约**。被测端点/规则：`GET /v1/diagnostics/traces?since=&until=&deployment_id=&model=&limit=&cursor=`，返回 `TracePage`（顶层键集恰 `{items, next_cursor, has_more}`）；每项 `TraceView` 必填 5 键（`request_id, correlation_id, stages, snapshot, usage`），`stages` `minItems:1` 且按 `timestamp` 升序（机制 `INV-5`）；同一 `request_id` 在结果集中**去重**（实现 `GROUP BY te.request_id`，一个请求即使有多个 `trace_events` 也只出现一次）；稳定排序基于 `(first_ts, request_id)`（[`src/libdiag/traces.py`](../../../../src/libdiag/traces.py) `ORDER BY first_ts DESC, rid DESC`，cursor = `"<first_ts>|<rid>"`）；认证 `admin`；失败走统一信封（401/403/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-TRACE`/`D-OBS-PAGE`、§4.10 "同 request 的 stages 升序（INV-5）、trace 始终写、保留 7 天"）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`TracePage`/`TraceView`/`TraceStage`，`security=AdminBearerAuth`）。**不证明什么**：不证明 `limit=1` 分页/无效 cursor（OBS-TRACE-02）、不证明单请求全生命周期（OBS-REQTRACE-01）、不证明快照/统计（OBS-SNAP-01、OBS-STATS-01）、不证明别名等价（OBS-ALIAS-06）。**契约一致性警示（须登记）**：`since`/`until`/`deployment_id`/`model` 在 openapi 中 `required:false`，实现亦允许缺省——本 case 可用无参或宽窗请求。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；`trace_events` **无开关、始终写**（机制 §4.10 `CON-OBS-001` 明确 trace 不受 `snapshots_enabled`/`stats_enabled` 影响），故正常有流量的 m5air `items` 可能非空。本 case 纯读，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body）：
  `GET /v1/diagnostics/traces?limit=50`（如需限定可加 `?since=<RFC3339>&until=<RFC3339>`）。`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：不带 cursor（正向首分页）；`limit` 取默认 50（不触 `limit=1` 稳定性断言，属 OBS-TRACE-02）；不构造非法 cursor（OBS-TRACE-02）；`items` 是否非空不固定，只断言去重与形状/有序不变量。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/traces?limit=50`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层键集**恰为** `{items, next_cursor, has_more}`；`items` 数组、`has_more` JSON 布尔、`next_cursor` 字符串或 `null`。
  5. **去重断言**：`items` 中 `request_id` 列表长度 == 去重后长度（同一 request 不得出现两次）。
  6. 对每个 `item`：断言键集**恰为** `{request_id, correlation_id, stages, snapshot, usage}`；`request_id` 为非空字符串；`correlation_id` 字符串或 `null`；`stages` 为数组且长度 ≥1，每 `stage` 键集恰 `{stage, timestamp, detail}`（`stage` 字符串 ≤64、`timestamp` date-time、`detail` 对象或 `null`）；`snapshot` 为 `null` 或 `SnapshotView`；`usage` 为 `null` 或 `UsageView`。
  7. **有序断言**：每个 `item.stages` 的 `timestamp` 序列非降序（机制 `INV-5` 升序）。
  8. （分页稳定性交叉核对，不改变判定）若 `has_more` 为真且 `next_cursor` 非空，重放 `GET ...&cursor=<next_cursor>`，断言返回合法 `TracePage` 且不与前一页 `request_id` 重叠；本 case 不承担 cursor 负向/`limit=1` 判定。

**重点关注步骤**：① **去重是本 case 核心**——不是"列表里有 trace"，而是"同一 `request_id` 至多一次"；重复即 FAIL。② **`stages` 有序**——按 `timestamp` 升序（`INV-5`），乱序即 FAIL。③ **`stages` 非空**——`minItems:1`；空 `stages` 的 `TraceView` 非法（但 `items` 为空是合法的空页）。④ **页/项键集精确**——顶层 3 键、项 5 键、stage 3 键。⑤ **`snapshot`/`usage` 可为 `null`**——`snapshots_enabled=false` 时 `snapshot=null` 合法；`usage` 取决于账本，不得因 `null` 判 FAIL。⑥ **空页合法**——无 trace 时 `{"items":[],"next_cursor":null,"has_more":false}` 合法（PASS），不要求非空。⑦ **降级/存储**——`_UnavailableDiagnostics.traces` 恒返回空页 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_trace_01.py`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `TracePage`/`TraceView`/`TraceStage` wire 形态 + 机制 §4.10 去重/有序保证（不依赖实现内部）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：`{"items":[...], "next_cursor": <string|null>, "has_more": <bool>}`，顶层键集恰 3。
  - 去重：`request_id` 唯一。
  - 项：键集恰 5；`stages` ≥1 且按 `timestamp` 升序，每 stage 键集恰 3；`snapshot`/`usage` 为 `null` 或对应 schema。
  - 空页合法。
  - **fail-open**：降级实例 `200 + 空 TracePage` → **PASS**（本 case 不要求非空）；健康实例非 200、键集不符、`request_id` 重复、`stages` 乱序/为空 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 页键集恰 3 + `request_id` 去重 + 每项恰 5 键且 `stages` ≥1 有序 + 空页合法（含 fail-open）。
  - **FAIL**：非 200（存储健康时）、键集不符、`request_id` 重复、`stages` 为空或乱序、stage 键集不符。
  - **BLOCKED**：测试代码/契约问题或存储不可达 `503 usage_store_unavailable`——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不写 `trace_events`、不改开关、不注入。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers/body、命令/exit code/`elapsed`、环境快照；分页稳定性交叉证据（重放页与去重统计）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；M007 `trace_events`（`002_observability.sql`，trace 不受开关）；`TracePage`/`TraceView`/`TraceStage` 机器契约；实现 [`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_trace_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-TRACE-02（分页/游标）、OBS-REQTRACE-01（单请求全生命周期）语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
