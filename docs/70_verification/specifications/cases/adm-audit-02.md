<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-AUDIT-02 — 审计分页

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-AUDIT-02` |
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
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/adm-audit-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-AUDIT-02`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 审计接口（GET /v1/audit）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-AUDIT-02` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-AUDIT-02` / 系统设计 §8 审计接口（GET /v1/audit） / `VRC-MGMT-006` / `boundary` / `P1`
- **测试方法（§1.5 方法表行）**：边界值抽样 + 契约字段比对
- 方案清单登记：`ADM-AUDIT-02`（与 §3.2 权威清单一致；本文件名 `adm-audit-02.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/audit?limit=1` 有界分页：HTTP 200 + `data.length ≤ 1` + `page.has_more`/`next_cursor` 一致。
- 明确不测什么 / 失败含义：不证明 cursor 跨页去重/重放（审计当前无 cursor；`/v1/usage` 的 cursor 语义见 DP-USAGE-03/07）、不证明非法 `limit` 400（ADM-AUDIT-03）、不证明字段脱敏（ADM-AUDIT-01）、不证明稳定排序的全部语义（本 case 只断 `limit=1` 边界）。

**目的（被测契约）**：验证审计的**有界页契约**。被测端点/规则：`GET /v1/audit`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listAuditEvents`，query `limit` 默认 50/上限 200）；[`AuditLog.page`](../../../../src/management/audit.py) `LIMIT max(1,min(limit,200))`，固定返回 `page={has_more:false,next_cursor:null}`（当前实现**不提供** cursor 翻页）。设计验证项 `VRC-MGMT-006`；机制 `T-MET-PAGE`；需求/机制链 `LT-FUN-006`、`R-OBS-01`、`CT-ADMIN-001`、`CT-LOG-001`。**不证明什么**：不证明 cursor 跨页去重/重放（审计当前无 cursor；`/v1/usage` 的 cursor 语义见 DP-USAGE-03/07）、不证明非法 `limit` 400（ADM-AUDIT-03）、不证明字段脱敏（ADM-AUDIT-01）、不证明稳定排序的全部语义（本 case 只断 `limit=1` 边界）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态：审计表非空；只读。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/audit?limit=1 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`limit=1`（下界边界，`minimum:1`）；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/audit?limit=1")`。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `len(data) <= 1`；`page` 键集恰 `{has_more,next_cursor}`；`isinstance(page["has_more"], bool)`。
  5. 断言一致性：`page["has_more"] is True ⇒ page["next_cursor"]` 为非空字符串；`page["has_more"] is False ⇒ page["next_cursor"] is None`。
  6. （可选对照）`GET /v1/audit`（默认 50）的 `data` 长度 ≥ `limit=1` 时的长度（不强制，避免空表误判）。

**重点关注步骤**：① **边界 `limit=1`**——返回条数必须 ≤1（不是必须 ==1；空表时 0 亦合法）；② **`has_more`/`next_cursor` 一致**——本实现恒 `has_more=false`、`next_cursor=null`，因此断言其一致即可，**不得**因 `has_more=false` 误判"分页失效"（审计当前无 cursor 分页是已知契约）；③ **布尔类型**——`has_more` 必须 JSON bool，不能是 0/1；④ **不得当 cursor 端点**——审计不接受 `cursor` query（无 cursor 语义），不得构造 cursor 断言；⑤ **纯读**——不写审计。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `AdminPageMeta`/`AuditPage` + `limit` 边界规则。
  - HTTP：`200`；body `{"data":[...≤1...],"page":{"has_more":false,"next_cursor":null}}`。
  - `has_more` 为 bool 且与 `next_cursor` 一致。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `len(data)≤1` + `page` 键集正确 + `has_more` 为 bool 且与 `next_cursor` 一致。
  - **FAIL**：status 非 200、`len(data)>1`、`page` 形状错、`has_more` 非 bool、或一致性违反。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含 `limit=1`）、原始 HTTP status/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`AdminPageMeta`/`AuditPage` 机器契约；`AuditLog.page`；机制 `T-MET-PAGE`。自动化入口 [`at_adm_audit_02.py`](../../../../tests/system/api_test_v03/at_adm_audit_02.py)。**不依赖**其它 Case；与 ADM-AUDIT-01/03 互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
