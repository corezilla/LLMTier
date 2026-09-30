<!-- STD_DOCUMENT_COVER_BEGIN -->
# OBS-ALIAS-03 — 别名 trace

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `OBS-ALIAS-03` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/obs-alias-03.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`OBS-ALIAS-03`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `OBS-ALIAS-03` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`OBS-ALIAS-03` / 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） / `VRC-DIAG-002` / `normal` / `P2`
- 方案清单登记：`OBS-ALIAS-03`
- 要测什么（责任展开）：`/tier/admin/v1/trace/{request_id}` 与 `/v1/trace/{request_id}` 的 GET 由同一 handler 服务：status 与响应体逐字节等价（含未知 id 的 404 信封）。
- 明确不测什么 / 失败含义：不证明 全生命周期内容（OBS-REQTRACE-01）、不证明未知 id 404 语义本身（OBS-REQTRACE-02）、不证明角色负向（OBS-REQTRACE-03、AUTH-08）、不证明其它别名（OBS-ALIAS-01/02/04/05/06）。**契约一致性警示（须登记）**：`_UnavailableDiagnostics.trace` 对任意 id 返回 `200` 空视图，等价比对在降级实例下仍可做但语义受限（判 BLOCKED/SKIP）。

**目的（被测契约）**：验证单请求 trace 别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/trace/{request_id}` 是 `/v1/trace/{request_id}` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/trace/{request_id}": "/v1/trace/{request_id}"`），同一 handler、相同 `TraceView` 形状、相同 `admin` 鉴权与相同错误语义（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.trace`）；body 应逐字节等价（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；错误在扁平/别名上亦逐字节等价（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`TraceView`、`NotFound`）。**不证明什么**：不证明全生命周期内容（OBS-REQTRACE-01）、不证明未知 id 404 语义本身（OBS-REQTRACE-02）、不证明角色负向（OBS-REQTRACE-03、AUTH-08）、不证明其它别名（OBS-ALIAS-01/02/04/05/06）。**契约一致性警示（须登记）**：`_UnavailableDiagnostics.trace` 对任意 id 返回 `200` 空视图，等价比对在降级实例下仍可做但语义受限（判 BLOCKED/SKIP）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线。本 case 纯 GET，初态即终态。

## 3. 输入构造

- **输入与构造**：
  - **正向（若有数据）**：经 `GET /v1/diagnostics/traces?limit=1`（`admin_client`）取一个真实 `request_id`，分别 `GET /v1/trace/<id>` 与 `GET /tier/admin/v1/trace/<id>`。
  - **404 等价（确定性，无需数据）**：`GET /v1/trace/req_does_not_exist` 与 `GET /tier/admin/v1/trace/req_does_not_exist`。
  同凭据。边界点：两路径必须查**同一 id**；`X-Request-ID` 每次不同，**不参与**比较，也不列入 Oracle；404 路径用于保证即使 trace 列表为空也能完成等价判定。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics/traces?limit=1`（`admin_client`）→ 若 `items` 非空取 `request_id`；空则可选。
  2. **404 等价（必做）**：`GET /v1/trace/req_does_not_exist` 与别名同 id → 断言两 `status == 404` 且 `resp.content` **逐字节相等**，`code=="not_found"`。
  3. **正向等价（有 id 时）**：对 `request_id` 分别请求两路径 → 断言两 `status == 200` 且 `resp.content` **逐字节相等**；均为合法 `TraceView`（键集恰 `{request_id, correlation_id, stages, snapshot, usage}`）。
  4. 断言 `status` 与 body 在两路径上一致；仅 header 中的 `X-Request-ID` 不同（不参与断言）。

**重点关注步骤**：① **同 id 比较**——两路径必须查同一 `request_id`，否则 body 本可不同。② **逐字节 body 等价**——比较 `resp.content`。③ **错误路径也等价**——404 信封在扁平/别名上应逐字节相同（本 case 用 404 作确定性锚点）。④ **只比 body**——`X-Request-ID` 不参与、不列入 Oracle。⑤ **鉴权等价**——都需 `admin`（本 case 正向；负向 AUTH-08）。⑥ **数据不足处理**——无真实 trace 时以 404 等价完成判定，不算 FAIL（但报告须说明未覆盖正向）。⑦ **降级/存储**——降级实例两路径同样返回 200 空视图（等价成立但语义受限，判 BLOCKED/SKIP）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_alias_03.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `TraceView`/`NotFound` wire 形态。
  - 404 路径：两路径 `404`，`body_flat == body_alias`（逐字节），`code=="not_found"`。
  - 正向路径（有 id）：两路径 `200`，`body_flat == body_alias`（逐字节），均为合法 `TraceView`。
  - **fail-open**：降级实例两路径同样 200 空视图（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：同一 id 下两路径 status 相同且 body 逐字节相等（404 路径必做；有数据时 200 路径亦做）。
  - **FAIL**：status/body 不等价、别名 404（端点缺失）或错误 code 不同。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存两路径 404 响应与逐字节对比、正向对比（若有）、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/trace/...` 分支）。自动化入口 `at_obs_alias_03.py`（已实现）。**不依赖**其它 Case；与 OBS-REQTRACE-01/02（内容/404）、AUTH-08 语义相邻，与其它别名并列但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
