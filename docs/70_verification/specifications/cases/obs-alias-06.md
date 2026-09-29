<!-- STD_DOCUMENT_COVER_BEGIN -->
# OBS-ALIAS-06 — 别名 diagnostics/traces

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `OBS-ALIAS-06` |
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
| Canonical Path | `docs/70_verification/specifications/cases/obs-alias-06.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`OBS-ALIAS-06` / 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） / `VRC-DIAG-002` / `normal` / `P2`
- 方案清单登记：`OBS-ALIAS-06`
- 要测什么（责任展开）：`/tier/admin/v1/diagnostics/traces` 与 `/v1/diagnostics/traces` 的 GET 由同一 handler 服务：status 与响应体逐字节等价（含无效 cursor 路径的等价观察）。
- 明确不测什么 / 失败含义：不证明 去重/有序（OBS-TRACE-01）、不证明 `limit=1`/无效 cursor 负向（OBS-TRACE-02）、不证明其它别名、不证明别名鉴权负向（AUTH-08）。**契约一致性警示（须登记）**：traces cursor 当前无校验（OBS-TRACE-02 已记）；本 case 只判两路径彼此等价，不改变该缺陷判定。

**目的（被测契约）**：验证 trace 列表别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/diagnostics/traces` 是 `/v1/diagnostics/traces` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/diagnostics/traces": "/v1/diagnostics/traces"`），同一 handler、相同 `TracePage` 形状、相同 `admin` 鉴权（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.traces`）；body 应逐字节等价（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；错误在扁平/别名上亦逐字节等价（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`TracePage`）。**不证明什么**：不证明去重/有序（OBS-TRACE-01）、不证明 `limit=1`/无效 cursor 负向（OBS-TRACE-02）、不证明其它别名、不证明别名鉴权负向（AUTH-08）。**契约一致性警示（须登记）**：traces cursor 当前无校验（OBS-TRACE-02 已记）；本 case 只判两路径彼此等价，不改变该缺陷判定。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；本 case 纯 GET，初态即终态。

## 3. 输入构造

- **输入与构造**：
  - **正向**：同一参数 `?limit=50`（可加相同 `since`/`until`）分别请求两路径。
  - **边界等价观察**：同一无效 cursor `?limit=1&cursor=not-a-real-cursor` 分别请求两路径（当前实现会忽略/应用该 cursor；本 case 只断言两路径行为**相同**，不把 400/200 本身作为 Oracle——那属 OBS-TRACE-02）。
  同凭据、同参数。边界点：`X-Request-ID` 每次不同，**不参与**比较，也不列入 Oracle。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/traces?limit=50`（`admin_client`）→ 记录 status/`Content-Type`/body。
  3. `GET /tier/admin/v1/diagnostics/traces?limit=50`（同 client、同参数）→ 断言两 `200` 且 `resp.content` **逐字节相等**；均为合法 `TracePage`（顶层键集恰 `{items, next_cursor, has_more}`）。
  4. **边界等价**：两路径同带 `?limit=1&cursor=not-a-real-cursor` → 断言两路径 **status 与 body 逐字节相同**（不判该状态是否为 400；负向判定归 OBS-TRACE-02）。
  5. 断言两路径 status 与 body 一致；仅 `X-Request-ID` 不同（不参与断言）。

**重点关注步骤**：① **参数严格对齐**——同 query 才可逐字节比较。② **逐字节 body 等价**——比较 `resp.content`。③ **边界路径只判等价**——无效 cursor 下只要求两路径**行为一致**，不在此判定 cursor 负向是否合规（避免与 OBS-TRACE-02 重复/冲突）。④ **只比 body**——`X-Request-ID` 不参与、不列入 Oracle。⑤ **鉴权等价**——都需 `admin`（正向；负向 AUTH-08）。⑥ **空页也须等价**——`items=[]` 时两路径仍完全一致。⑦ **降级/存储**——降级实例两路径同样空页（等价成立，判 BLOCKED/SKIP 说明语义）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_alias_06.py`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `TracePage` wire 形态。
  - 正向：两路径 `200`，`body_flat == body_alias`（逐字节），均为合法 `TracePage`。
  - 边界：同一无效 cursor 下两路径 status 与 body **完全一致**（无论该状态是什么）。
  - **fail-open**：降级实例两路径同样空页（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：同一参数下两路径 status 相同且 body 逐字节相等（正向与无效 cursor 边界均成立）。
  - **FAIL**：status/body 不等价或别名 404。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存两路径正向响应与逐字节对比、无效 cursor 边界两路径响应、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/diagnostics/traces` 分支）。自动化入口 `at_obs_alias_06.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-TRACE-01/02（内容/分页）、AUTH-08 语义相邻，与其它别名并列但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
