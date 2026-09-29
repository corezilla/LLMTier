<!-- STD_DOCUMENT_COVER_BEGIN -->
# OBS-TRACE-02 — trace 列表分页/游标

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `OBS-TRACE-02` |
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
| Canonical Path | `docs/70_verification/specifications/cases/obs-trace-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`OBS-TRACE-02` / 系统设计 §8 诊断 trace 接口（/v1/diagnostics/traces） / `VRC-DIAG-002` / `recovery` / `P2`
- 方案清单登记：`OBS-TRACE-02`
- 要测什么（责任展开）：`GET /v1/diagnostics/traces` `limit=1` 稳定分页 + 无效/过期 cursor → `400 cursor_expired`（`ERR-CURSOR`）。
- 明确不测什么 / 失败含义：不证明 去重/正向页（OBS-TRACE-01）、不证明快照 cursor（OBS-SNAP-02）、不证明别名等价（OBS-ALIAS-06）、不证明 `limit=abc` 的 `invalid_request`（属 `_int_param`，非本 case 的 `cursor_expired`）。**契约一致性警示（必须登记）**：当前实现 [`traces`](../../../../src/libdiag/traces.py) **不校验 cursor**——仅当 cursor 含 `"|"` 才用于 `(first_ts,rid)<(?,?)`，否则**静默忽略**；不存在/过期 cursor 不抛 `cursor_expired`。故"400 `cursor_expired`"是测试设计契约期望，**当前实现预期为 FAIL/待修复**（openapi 已声明 400，authority 较 snapshots 清晰）。

**目的（被测契约）**：验证 `GET /v1/diagnostics/traces` 的**分页与 cursor 负向契约**。被测端点/规则：`limit∈[1,500]`（实现 `max(1,min(limit,500))`），`limit=1` 时单页至多 1 项、`has_more`/`next_cursor` 与数据量一致；cursor 稳定基于 `(first_ts, request_id)`（`"<first_ts>|<rid>"`）；**无效/过期 cursor → `400 cursor_expired`**（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) OBS-TRACE-02；§3.5 `/v1/diagnostics/traces` 覆盖 `cursor_expired`；§11.1 `ERR-CURSOR → DP-USAGE-04、OBS-SNAP-02、OBS-TRACE-02`）；openapi `/v1/diagnostics/traces` **声明 400**（`BadRequest`）；认证 `admin`；统一信封 5 键。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-TRACE` + `T-MET-PAGE`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明去重/正向页（OBS-TRACE-01）、不证明快照 cursor（OBS-SNAP-02）、不证明别名等价（OBS-ALIAS-06）、不证明 `limit=abc` 的 `invalid_request`（属 `_int_param`，非本 case 的 `cursor_expired`）。**契约一致性警示（必须登记）**：当前实现 [`traces`](../../../../src/libdiag/traces.py) **不校验 cursor**——仅当 cursor 含 `"|"` 才用于 `(first_ts,rid)<(?,?)`，否则**静默忽略**；不存在/过期 cursor 不抛 `cursor_expired`。故"400 `cursor_expired`"是测试设计契约期望，**当前实现预期为 FAIL/待修复**（openapi 已声明 400，authority 较 snapshots 清晰）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture：`llmtier_b` + `admin_client_b`/`api_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。为产生可分页的 trace，**先制造 >1 个带 `request_id` 的 trace**：对 `depl_b` 发起 ≥2 次 `POST /v1/responses`（`api_client_b`，`stream=true`,`store=false`；`depl_b` 为 healthy，响应为 SSE 或可解释错误），入口对每次请求写 `received`（及可能的 `completed`）`trace_events`，即使响应非 200 也会有 trace（trace 始终写）。若制造失败无法得到 ≥2 个 trace，则退化为仅测无效 cursor（仍有效）并在报告说明数据限制。

## 3. 输入构造

- **输入与构造**：先制造 trace，再固定请求（无 body）：
  - 分页：`GET /v1/diagnostics/traces?limit=1`；随后 `GET /v1/diagnostics/traces?limit=1&cursor=<next_cursor>`（取上一页 `next_cursor`）。
  - 无效 cursor：`GET /v1/diagnostics/traces?limit=1&cursor=not-a-real-cursor`、`cursor=2020-01-01T00:00:00Z|req_deadbeef`、`cursor=%00`。

  `Authorization: Bearer dev-admin`。边界点：cursor 内部分隔使用 `|`；无 `|` 的 cursor 在当前实现被忽略（正是缺陷点）；不测 `limit=abc`（属 `_int_param`）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. 制造 ≥2 个请求级 trace（≥2 次 `POST /v1/responses`，记录发出的请求，不把模型内容当 oracle）。
  2. `GET /v1/diagnostics/traces?limit=1` → 断言 `200`、顶层键集恰 3、`len(items) ≤ 1`；若数据 ≥2 则 `has_more is True` 且 `next_cursor` 为字符串。
  3. `GET /v1/diagnostics/traces?limit=1&cursor=<next_cursor>` → 断言 `200` 且下一页 `request_id` 与前一页**不重叠**（稳定分页）。
  4. 对每个无效 cursor 变体 `GET` → 断言 `400`；`err["code"]=="cursor_expired"`、`err["type"]=="request_error"`、`err["retryable"] is False`、键集恰 5。
  5. 断言无效 cursor **不得**返回 `200` 页（尤其不得被静默忽略后返回首页/空页）。

**重点关注步骤**：① **无效 cursor 必须 400**——最危险的是"cursor 被忽略 → 200"（当前实现即此）；若出现即 FAIL。② **`limit=1` 单页不变量**——`len(items) ≤ 1`；`has_more`/`next_cursor` 与数据量一致（有下一页则 `next_cursor` 非空）。③ **稳定分页**——同 cursor 重放返回相同成员（`first_ts|rid` 排序确定性），跨页不重不漏（`(first_ts,rid)` 严格递减）。④ **code 精确**——`cursor_expired`（§11.1 `ERR-CURSOR`）。⑤ **与 `limit` 非法区分**——`limit=abc` 是 `invalid_request`；本 case 不混用。⑥ **trace 制造不改变 oracle**——用真实请求产生 trace，但断言只针对页/游标契约，不针对响应内容。⑦ **契约 authority**——openapi 已声明 400，故 authority 清晰；实现缺失按 FAIL 登记（`required_resolution`=为 traces cursor 增加校验）。⑧ **降级/存储**——`_UnavailableDiagnostics.traces` 忽略 cursor 返回空页 200，属降级 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_trace_02.py`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 测试设计 §3.2/§3.5/§11.1 的 `cursor_expired` 契约 + `openapi` `BadRequest`（`ErrorEnvelope`，`code` enum 含 `cursor_expired`）+ `TracePage` 页形状。
  - `limit=1`：`200`；页键集恰 3；`len(items) ≤ 1`；有更多时 `has_more=true` 且 `next_cursor` 非空。
  - 稳定分页：相邻页 `request_id` 不重叠、`(first_ts,rid)` 单调。
  - 无效 cursor：`400`；body `{"error":{"message":<str>,"type":"request_error","code":"cursor_expired","param":<string|null>,"retryable":false}}`（恰 5 键）。
  - **契约 vs 实现**：当前实现返回 `200`（忽略/错误应用 cursor）→ 按目标契约判 **FAIL**，`failure_step` 指明"cursor 未校验"；openapi 已声明 400，不构成 authority 缺口。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`limit=1` 分页稳定且不重叠；所有无效 cursor 均 `400 + cursor_expired`；无"忽略 cursor 的 200"。
  - **FAIL**：无效 cursor 返回 200（含首页/空页）或其他 code、`limit=1` 超 1 项或跨页重叠。
  - **BLOCKED**：测试代码/断言不可实现、无法制造 ≥2 trace 且降级实例无法证明契约、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交无效 cursor 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需数据 teardown**（本 case 不写配置/注入；制造的 trace 属正常观测数据，由保留期 `cleanup(7)` 管理，不删除既有资源）；不改开关、不写注入。离开前确认无残留、`/readyz` 7 tier、无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存制造 trace 的请求、`limit=1` 两页响应、跨页 `request_id` 对比、每个无效 cursor 的原始 400（或当前实现的 200 实测）、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)（B 类附加）；`llmtier_b`/`admin_client_b`/`api_client_b` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ERR-CURSOR`；实现 [`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)（当前无 cursor 校验 → 与契约不一致，须登记缺陷）、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_trace_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-TRACE-01（去重/正向页）、OBS-SNAP-02（快照 cursor）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
