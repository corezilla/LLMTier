<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-obsreqtrace-002 — 未知 request_id

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-obsreqtrace-002` |
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
| Canonical Path | `docs/70_verification/system/cases/st-obsreqtrace-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-obsreqtrace-002`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-obsreqtrace-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-obsreqtrace-002` / 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） / `VRC-DIAG-002` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-obsreqtrace-002`
- 要测什么（责任展开）：`GET /v1/trace/{request_id}` 查询不存在的 `request_id`：HTTP 404 `not_found`，不返回空 `TraceView` 的 200。
- 明确不测什么 / 失败含义：不证明 已知 id 的全生命周期（ST-obsreqtrace-001）、不证明 data token 403（ST-obsreqtrace-003）、不证明注入命中、不证明别名等价（ST-obsalias-003）。**契约一致性警示（须登记）**：`_UnavailableDiagnostics.trace` 对**任意** id 返回 `200 + {stages:[]}`（fail-open），与健康实现的 404 语义不同；本 case 的 Oracle 以**健康诊断服务**为准。

**目的（被测契约）**：验证单请求 trace 的**资源存在性负向契约**。被测端点/规则：`GET /v1/trace/{request_id}`，`TraceDiagnostics.trace` 在 `_trace_view` 无任何 `trace_events` 阶段时抛 `ApiError(404, "not_found", "No trace for this request_id")`（[`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)）；不存在 id 必须 404，**不得**以 `200 + {stages:[]}` 冒充；认证 `admin`；统一信封 5 键（`type="request_error"`，`retryable=false`）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-TRACE-QUERY` "`trace` 无记录 → `ERR-NOTFOUND`（404）"）；错误目录 `ERR-NOTFOUND` → `not_found`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理) `ERR-NOTFOUND → ...、ST-obsreqtrace-002`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`NotFound`，`TraceView.request_id maxLength:128`）。**不证明什么**：不证明已知 id 的全生命周期（ST-obsreqtrace-001）、不证明 data token 403（ST-obsreqtrace-003）、不证明注入命中、不证明别名等价（ST-obsalias-003）。**契约一致性警示（须登记）**：`_UnavailableDiagnostics.trace` 对**任意** id 返回 `200 + {stages:[]}`（fail-open），与健康实现的 404 语义不同；本 case 的 Oracle 以**健康诊断服务**为准。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；本 case 纯 GET、零写入，初态即终态。为避免与真实 id 冲突，使用带唯一后缀的 id。

## 3. 输入构造

- **输入与构造**：固定请求（无 body）：
  - `GET /v1/trace/req_does_not_exist_<uuid>`、`Authorization: Bearer dev-admin`
  - 形态合法的 `GET /v1/trace/req_deadbeef0000000000000000000000`
  - 边界：`GET /v1/trace/x`（短 id）；`GET /v1/trace/<129 字符>`（超 openapi `maxLength:128`，观察是否 404/400，作为边界记录）

  边界点：这些 id **在库中无任何 `trace_events`**；不制造该 id 的任何请求；不构造非法 body（GET 无 body）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/trace/req_does_not_exist_<uuid>`（`admin_client`）→ 记录 status/body。
  2. 断言 `resp.status_code == 404`；`err["code"]=="not_found"`、`err["type"]=="request_error"`、`err["retryable"] is False`、键集恰 5。
  3. 断言 **不得** 返回 `200 + {stages:[]}`（空 trace 冒充存在）。
  4. 对另外两个边界 id 重复步骤 1–3（超长 id 的 400/404 记录并说明，不作为 FAIL 依据）。
  5. （对照，可选）取一条真实 `request_id`（经 `GET /v1/diagnostics/traces?limit=1`）→ 断言 `200`，证明端点本体可用（排除"端点整体坏"被误判为 404）。

**重点关注步骤**：① **不得空 stages 冒充**——最危险的误判是把 `200 + {stages:[]}` 当"存在但无阶段"；404 才是契约。② **code 精确**——`not_found`（非 `model_not_found`/`invalid_request`）。③ **错误信封 identity**——恰 5 键、`type=request_error`。④ **id 唯一性**——使用不会在库中出现的 id，避免与真实请求冲突造成假 200。⑤ **超长 id 边界**——openapi `maxLength:128`；若实现返回 404（未校验长度）记录为边界说明，不判 FAIL（除非契约要求 400，当前未声明）。⑥ **降级差异**——`_UnavailableDiagnostics` 对任意 id 返回 200 空视图；执行时须确认诊断服务健康（`GET /v1/diagnostics` 200 且非降级默认特征），降级下判 BLOCKED/SKIP。⑦ **零副作用**——404 不写库。⑧ **存储**——`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_reqtrace_02.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `NotFound`（`ErrorEnvelope`）+ 机制 §5.1 `IF-OBS-TRACE-QUERY` 404 语义。
  - 每个未知 id：HTTP `404`；`Content-Type: application/json`；body `{"error":{"message":"No trace for this request_id","type":"request_error","code":"not_found","param":<string|null>,"retryable":false}}`（恰 5 键；`message` 措辞以实现为准，仅断言 code/type）。
  - 对照：真实 id → `200 TraceView`。
  - **fail-open**：降级实例 `200 + {stages:[]}` 与健康 404 语义不同；无法证明契约时判 **BLOCKED/SKIP**；健康实例返回 200 空视图或非 `not_found` → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：未知 id 均 `404 + not_found + type=request_error + retryable=false`；无空 stages 冒充；对照 200 正确。
  - **FAIL**：未知 id 返回 `200`（含空视图）或其他 code。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正提交未知 id 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯 GET，零副作用。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存每个未知 id 的原始 404 信封、超长 id 边界、正相对照、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ERR-NOTFOUND`；实现 [`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)（`trace` 抛 404）、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_reqtrace_02.py`（已实现）。**不依赖**其它 Case；与 ST-obsreqtrace-001（正向）、ST-obsreqtrace-003（角色负向）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
