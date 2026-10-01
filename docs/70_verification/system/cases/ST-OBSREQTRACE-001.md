<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSREQTRACE-001 — 请求全生命周期 trace

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSREQTRACE-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-OBSREQTRACE-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSREQTRACE-001`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSREQTRACE-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSREQTRACE-001` / 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） / `VRC-DIAG-002` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-OBSREQTRACE-001`
- 要测什么（责任展开）：`GET /v1/trace/{request_id}` 返回单请求全生命周期 `TraceView`：`stages` 有序且覆盖 `received…completed`，并组合 `snapshot`/`usage`。
- 明确不测什么 / 失败含义：不证明 未知 id 的 404（ST-OBSREQTRACE-002）、不证明 data token 的 403（ST-OBSREQTRACE-003）、不证明注入命中（ST-RESP-011/22 的 trace `source=injected` 证明）、不证明 trace 列表去重/分页（ST-OBSTRACE-001/02）、不证明别名等价（ST-OBSALIAS-003）。`X-Request-ID` 仅用于获取 `request_id` 的 harness 机制，**不是**本 case 的 Oracle（openapi 未声明 200 响应头）。

**目的（被测契约）**：验证 Observability `GET /v1/trace/{request_id}` 的**单请求全生命周期只读契约**。被测端点/规则：`GET /v1/trace/{request_id}`，成功返回 `TraceView`（键集恰 `{request_id, correlation_id, stages, snapshot, usage}`）；`stages` `minItems:1` 且按 `timestamp` 升序（机制 `INV-5`）；`snapshot` 为 `null` 或 `SnapshotView`、`usage` 为 `null` 或 `UsageView`；该视图**组合** `trace_events`（trace）+ `diagnostic_snapshots`（快照）+ `usage_record_versions`（账本）（[`src/libdiag/traces.py`](../../../../src/libdiag/traces.py) `_trace_view`）；认证 `admin`；错误走统一信封（401/403/404/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-TRACE`、§4.9 `D-OBS-TRACE` 映射、§4.10 `INV-5`）；错误目录 `ERR-NOTFOUND`/`ERR-STORE`；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`TraceView`/`TraceStage`/`SnapshotView`/`UsageView`，`security=AdminBearerAuth`）。**不证明什么**：不证明未知 id 的 404（ST-OBSREQTRACE-002）、不证明 data token 的 403（ST-OBSREQTRACE-003）、不证明注入命中（ST-RESP-011/22 的 trace `source=injected` 证明）、不证明 trace 列表去重/分页（ST-OBSTRACE-001/02）、不证明别名等价（ST-OBSALIAS-003）。`X-Request-ID` 仅用于获取 `request_id` 的 harness 机制，**不是**本 case 的 Oracle（openapi 未声明 200 响应头）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin` 读 + 一次 `data` 推理调用；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；就绪检查含 7 tier 与 responses-capable 上游。fixture：`admin_client`（`admin`）、`api_client`（`data`）（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=§2.3 A 类基线；`trace_events` **无开关、始终写**（机制 §4.10 `CON-OBS-001`）。本 case 产生一次 `store=false` 的无状态推理调用（不落账本配置变更）。

## 3. 输入构造

- **输入与构造**：
  1. 制造一条 trace（`data` 面，固定 prompt）：`POST /v1/responses` body `{"model":"Worker","input":[{"role":"user","content":"Hello"}],"stream":true,"store":false,"max_output_tokens":50}`（成功路径；若上游不稳可用 `Senior` 等 responses-capable tier）。该请求写入 `received`/`validated`/`routed`/`upstream_started`/`upstream_ended`/`completed` 等 stage（[`src/inference/responses.py`](../../../../src/inference/responses.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)）。
  2. **取得 `request_id`（harness，非 Oracle）**：优先 `GET /v1/diagnostics/traces?limit=1`（`admin_client`）取最新一条 `items[0].request_id`（列表按 `first_ts DESC`，最新请求在首）；或读取被测响应头 `X-Request-ID`（运行时注入，**不作契约断言**）。若列表为空则本 case 无数据可查，判 BLOCKED/SKIP。
  3. 查询：`GET /v1/trace/<request_id>`、`Authorization: Bearer dev-admin`。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `POST /v1/responses`（`api_client`，上表 body，流式读取至结束；不把生成内容当 oracle）。
  3. `GET /v1/diagnostics/traces?limit=1` → 取 `items[0].request_id`（若为 `None`/空则 BLOCKED/SKIP）。
  4. `GET /v1/trace/<request_id>`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  5. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  6. 解析 JSON，断言键集**恰为** `{request_id, correlation_id, stages, snapshot, usage}`；`request_id` 等于查询 id；`correlation_id` 字符串或 `null`。
  7. 断言 `stages` 为数组且长度 ≥1；每 `stage` 键集恰 `{stage, timestamp, detail}`；`stages` 的 `timestamp` 序列非降序（`INV-5`）。
  8. 断言本次成功请求的 `stages` 至少包含一个 **上游阶段**（`stage` 含 `upstream_started`/`upstream_ended`）与入口阶段（`received`）——"全生命周期"的结构证据；若仅有 `received` 而缺上游阶段，说明组合不完整，判 FAIL（或若响应为可解释错误，允许结构相应缩减，需在证据中说明）。
  9. 断言 `snapshot` 为 `null` 或合法 `SnapshotView`（11 键）；`usage` 为 `null` 或合法 `UsageView`（8 键：`record_version,is_final,model,input_tokens,output_tokens,total_tokens,measurement_status,source`）。

**重点关注步骤**：① **全阶段组合**——不是"200 即可"，而是 `stages` 覆盖入口到上游结束的完整链且有序（`INV-5`）。② **键集精确**——`TraceView` 恰 5 键、`TraceStage` 恰 3 键。③ **`request_id` 回指**——返回的 `request_id` 必须等于查询 id（同一资源）。④ **`snapshot` 可为 `null`**——`snapshots_enabled=false`（m5air 默认）时 `snapshot=null` **合法**，不得判 FAIL；开启后应出现 `snapshot`。⑤ **`usage` 组合**——来自 `usage_record_versions` 最新版，`null` 合法（尚未记账），但成功请求通常有记录。⑥ **取得 id 的手段不是 Oracle**——`X-Request-ID`/traces 列表仅用于 harness；不得把响应头本身列入断言。⑦ **不依赖模型答案**——只断言结构/阶段，不写"答案正确"。⑧ **降级/存储**——`_UnavailableDiagnostics.trace` 对任意 id 返回 `{stages:[],...}` **200**，`stages=[]` 违反 `minItems:1`，属降级实例 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_reqtrace_01.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `TraceView`/`TraceStage`/`SnapshotView`/`UsageView` wire 形态 + 机制 §4.2/§4.10（`stages` 有序、组合快照/账本）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：键集恰 `{request_id, correlation_id, stages, snapshot, usage}`；`request_id` == 查询 id；`stages` ≥1 且 `timestamp` 非降序；每 stage 恰 3 键；成功请求含入口+上游阶段。
  - `snapshot`：`null` 或 11 键 `SnapshotView`；`usage`：`null` 或 8 键 `UsageView`。
  - **fail-open**：降级实例返回 `stages=[]` 视图——因违反 `minItems:1` 且无法证明组合，判 **BLOCKED/SKIP**（不把空 stages 当 PASS）；健康实例非 200、键集不符、stages 乱序/为空、或 request_id 不匹配 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 键集恰 5 + `request_id` 回指 + `stages` ≥1 有序且含入口/上游阶段 + `snapshot`/`usage` 类型正确。
  - **FAIL**：非 200（存储健康时）、键集不符、`request_id` 不匹配、`stages` 为空/乱序、或成功请求缺上游阶段。
  - **BLOCKED**：测试代码/契约问题、无法取得 `request_id`（trace 列表为空）、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（含 responses-capable 上游离线）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——`store=false` 无状态、A 类只读；不写配置/注入、不删除既有资源。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存制造请求及其响应（SSE 或可解释错误）、取得 `request_id` 的 traces 列表、`GET /v1/trace/{id}` 原始 status/headers/body、`stages` 有序证据、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client`/`api_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；responses-capable tier（`Worker`/`Senior`）；M007 `trace_events`/`diagnostic_snapshots` + 账本 `usage_record_versions`；`TraceView` 等机器契约；实现 [`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)、[`src/inference/responses.py`](../../../../src/inference/responses.py)。自动化入口 `at_obs_reqtrace_01.py`（已实现）。**不依赖**其它 Case；与 ST-OBSREQTRACE-002/03（负向）、ST-OBSTRACE-001（列表去重）语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
