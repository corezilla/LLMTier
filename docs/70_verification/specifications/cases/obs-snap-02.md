<!-- STD_DOCUMENT_COVER_BEGIN -->
# OBS-SNAP-02 — 快照无效 cursor

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `OBS-SNAP-02` |
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
| Canonical Path | `docs/70_verification/specifications/cases/obs-snap-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`OBS-SNAP-02` / 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） / `VRC-DIAG-002` / `recovery` / `P2`
- 方案清单登记：`OBS-SNAP-02`
- 要测什么（责任展开）：`GET /v1/diagnostics/snapshots` 提交无效/过期 cursor：HTTP 400 `cursor_expired`（`ERR-CURSOR`），不返回被游标解引用为零匹配的"假空页"。
- 明确不测什么 / 失败含义：不证明 正向页/脱敏（OBS-SNAP-01）、不证明 trace 分页（OBS-TRACE-02）、不证明别名等价（OBS-ALIAS-02）、不证明 `limit` 非法值的 400（`_int_param` → `invalid_request`，非本 case 的 `cursor_expired`）。**契约一致性警示（必须登记）**：当前实现 [`snapshots_page`](../../../../src/libdiag/snapshots.py) **不校验 cursor**——不存在的 cursor 使子查询返回 `NULL`、比较为假 → 返回 `200` + 空页；且 openapi `/v1/diagnostics/snapshots` **未声明 400 响应**。因此本 case 的"400 `cursor_expired`"是按测试设计契约的期望，**当前实现预期为 FAIL/待修复**；详见判定与依赖。

**目的（被测契约）**：验证 `GET /v1/diagnostics/snapshots` 的**分页 cursor 负向契约**。被测端点/规则：非法/不可解析/已失效 cursor → `400 cursor_expired`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) OBS-SNAP-02；§3.5 `/v1/diagnostics/snapshots` 覆盖 `cursor_expired`；§11.1 `ERR-CURSOR → DP-USAGE-04、OBS-SNAP-02、OBS-TRACE-02`）；稳定排序基于 `(captured_at, id)`（[`src/libdiag/snapshots.py`](../../../../src/libdiag/snapshots.py) `ORDER BY captured_at DESC,id DESC`，cursor 谓词 `(captured_at||id) < (SELECT ... WHERE id=?)`）；认证 `admin`；统一错误信封 5 键。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-SNAP` + 分页语义 `T-MET-PAGE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-PAGE`、[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明正向页/脱敏（OBS-SNAP-01）、不证明 trace 分页（OBS-TRACE-02）、不证明别名等价（OBS-ALIAS-02）、不证明 `limit` 非法值的 400（`_int_param` → `invalid_request`，非本 case 的 `cursor_expired`）。**契约一致性警示（必须登记）**：当前实现 [`snapshots_page`](../../../../src/libdiag/snapshots.py) **不校验 cursor**——不存在的 cursor 使子查询返回 `NULL`、比较为假 → 返回 `200` + 空页；且 openapi `/v1/diagnostics/snapshots` **未声明 400 响应**。因此本 case 的"400 `cursor_expired`"是按测试设计契约的期望，**当前实现预期为 FAIL/待修复**；详见判定与依赖。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；执行前附加（B 类）；fixture：`llmtier_b` + `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=基线；本 case 只读（仅 GET），不改变任何状态；本 case 以**语法无效/不存在**的 cursor 为充分输入（快照 cursor 不落 `query_snapshots`，与 DP-USAGE-04 不同）。

## 3. 输入构造

- **输入与构造**：固定请求（无 body）：
  `GET /v1/diagnostics/snapshots?cursor=<invalid>`、`Authorization: Bearer dev-admin`。无效 cursor 构造（逐项独立发起）：
  - `cursor=not-a-real-cursor`（任意非 id 字符串）
  - `cursor=snap_deadbeef0000000000000000000000`（形态合法但库中不存在）
  - `cursor=`（空串：`_int_param` 不涉及；`query.get("cursor")[0]` 为空串，按"无 cursor"或非法，观察实现）
  - `cursor=%00%01`（URL 编码控制字符）

  边界点：本 case 只测 cursor 负向，不带 `limit` 变化（`limit` 非法属 `_int_param` 的 `invalid_request`）；不构造非法 body。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics/snapshots?cursor=not-a-real-cursor`（`admin_client_b`）→ 记录 status/body。
  2. 断言 `resp.status_code == 400`；`err["code"]=="cursor_expired"`、`err["type"]=="request_error"`、`err["retryable"] is False`、键集恰 `{message,type,code,param,retryable}`。
  3. 对每个无效 cursor 变体重复步骤 1–2。
  4. 断言**不得**出现 `200 + {items:[],has_more:false}` 的"假空页"——若出现即 FAIL（这正是当前实现的行为）。
  5. （对照）无 `cursor` 的 `GET /v1/diagnostics/snapshots?limit=1` → 断言 `200` 且页形状正确（正向控制，证明端点本体可用，排除把"端点坏了"误判为 cursor 拒绝）。

**重点关注步骤**：① **"假空页"陷阱**——无效 cursor 最危险的误判是把它当合法空结果（当前实现正是 `NULL` 子查询 → 空页）；必须显式断言 400，不得以"空页合法"放行。② **code 精确**——必须 `cursor_expired`（§11.1 `ERR-CURSOR`），不是 `invalid_request`/`not_found`。③ **错误信封 identity**——恰 5 键、`type` 由状态导出、`param`（如有）可空。④ **与 `limit` 非法区分**——`limit=abc` 走 `_int_param` 的 `400 invalid_request`；本 case 不用该路径。⑤ **契约/实现不一致（登记）**——openapi 未声明 400，实现不校验；执行前必须先解决契约 authority（openapi 补 400 或测试设计降级该项）方可判定，否则按 §9 的"ISD/OpenAPI 语义不清"判 **BLOCKED**。⑥ **零副作用**——GET 拒绝不写任何行。⑦ **降级/存储**——`_UnavailableDiagnostics.snapshots_page` 忽略 cursor 返回空页 200，属降级实例 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_snap_02.py`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 测试设计 §3.2/§3.5/§11.1 的 `cursor_expired` 契约 + `openapi` `ErrorEnvelope`（`code` enum 含 `cursor_expired`）。
  - 每个无效 cursor：HTTP `400`；body `{"error":{"message":<str>,"type":"request_error","code":"cursor_expired","param":<string|null>,"retryable":false}}`（恰 5 键）。
  - 缺失/空 cursor 的预期按契约实现约定（若实现把空串视为"无 cursor"则 200，需在报告中具名说明，不作为 FAIL）。
  - 对照：无 cursor 正向 `200` 页形状正确。
  - **契约缺口**：openapi `/v1/diagnostics/snapshots` 无 400 声明（与 §3.5/§11.1 冲突）；在 authority 未统一前，本 case 判 BLOCKED，并在报告登记 `required_resolution`（补 openapi 400 或调整规格映射）。实现若返回 `200` 空页 → 按目标契约判 **FAIL**（缺失 cursor 校验），并在报告 `failure_step` 指明。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：无效 cursor 均 `400 + cursor_expired`（且正相对照 200 正确、无"假空页"）。
  - **FAIL**：无效 cursor 返回 `200`/空页或其他 code，或把"假空页"当通过。
  - **BLOCKED**：契约 authority 未统一（openapi 无 400）、测试代码/断言不可实现、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交无效 cursor 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯 GET；不写库、不改开关、不注入。离开前确认无残留、`/readyz` 7 tier、无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存每个无效 cursor 的原始 400 信封（或当前实现的 200 空页实测）、正向对照、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ERR-CURSOR`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；实现 [`src/libdiag/snapshots.py`](../../../../src/libdiag/snapshots.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)（当前无 cursor 校验 → 与契约不一致，须登记缺陷）。自动化入口 `at_obs_snap_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-SNAP-01（正向页）、OBS-TRACE-02（trace cursor）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
