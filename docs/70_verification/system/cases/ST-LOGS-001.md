<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-LOGS-001 — 脱敏日志

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-LOGS-001` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-LOGS-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-LOGS-001`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 日志接口（GET /v1/logs）（parent `llmtier-system-design`），设计验证项 `VRC-LOG-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-LOGS-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-LOGS-001` / 系统设计 §8 日志接口（GET /v1/logs） / `VRC-LOG-001` / `security` / `P0`
- **测试方法（§2.2 方法表行）**：鉴权/授权/脱敏冒烟（secret/PII 不泄露）+ 角色隔离
- 方案清单登记：`ST-LOGS-001`（与 计划 §3 权威清单一致；本文件名 `st-logs-001.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/logs?from&to` 返回脱敏的运行日志：HTTP 200 + `LogPage`，且上游 secret `9832` 不出现。
- 明确不测什么 / 失败含义：不证明 缺时间窗 400（ST-LOGS-002）、不证明审计脱敏（ST-AUDIT-001）、不证明 `level`/`module` 过滤（未单独构 case）、不证明日志完整性/保留策略。

**目的（被测契约）**：验证运行日志读取的**脱敏契约**（`T-TRUST-LEAK`）。被测端点/规则：`GET /v1/logs`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listSanitizedLogs`，query `from`/`to` **必填**、`level`/`module`/`request_id` 可选，`security=AdminBearerAuth`）；
[`OperationalLog.page`](../../../../src/log/logs.py) 以 `created_at>=? AND created_at<?`（**半开**）返回 `{data:[LogEntry],page}`；
写入侧 [`OperationalLog.record`](../../../../src/log/logs.py) 用 `_SENSITIVE` 正则把 `authorization`/`bearer …`/`secret`/`api_key`/`token=…` 替换为 `[REDACTED]` 并截断 512。
设计验证项 `VRC-LOG-001`；机制 `T-TRUST-LEAK`；需求/机制链 `LT-FUN-006`、`LT-SEC-004`、`R-OBS-01`、`CT-LOG-001`。**不证明什么**：不证明缺时间窗 400（ST-LOGS-002）、不证明审计脱敏（ST-AUDIT-001）、不证明 `level`/`module` 过滤（未单独构 case）、不证明日志完整性/保留策略。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=计划 §3 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；时间窗用动态 [`recent_window()`](../../../../tests/system/constants.py)；初始状态：m5air `operational_logs` 非空（HTTP/管理请求已写日志）。只读。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/logs?from=<recent_window.from>&to=<recent_window.to> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`from`/`to` 取动态近窗（保证非空）；不传 `level`/`module`/`request_id`；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/logs", params={"from": since, "to": until})`；记录 status、body 原文。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言含 `data`（数组，且**非空**——窗内应至少有本 suite 产生的日志）与 `page`；`page` 键集恰 `{has_more,next_cursor}`。
  5. 抽查每条 `LogEntry` 键集恰 `{id,created_at,level,module,event,message,request_id}`；`level∈{info,warning,error}`；`len(message)≤512`。
  6. **脱敏断言（强制）**：对整段 `resp.text` 及每条 `message`/`module`，断言 **不含上游 secret 字面 `"9832"`**、key 文件名 `"omlx-secret-key.txt"`、`"mnm_api_key"`。

**重点关注步骤**：① **`9832` 必须缺失**（规格明示）——`GET /v1/logs` 响应整体与 `message` 字段都不得出现 `9832`；`_SENSITIVE` 正则并不覆盖裸数字 secret，故这是**实质性**断言而非形式；② **窗内非空**——空 `data` 不能证明脱敏（无内容可审）；须至少有一条日志（本 suite 的 HTTP 请求即产生），否则构造失败（BLOCKED/复核窗口）；③ **半开窗**——`>=from AND <to`；④ **字段完整**——`LogEntry` 7 键、`message≤512`、`level` enum；⑤ **纯读**——`GET /v1/logs` 不写日志；⑥ **与 ST-AUDIT-001 区分**——本 case 面向 `operational_logs`，非 `audit_events`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `LogPage`/`LogEntry` + `T-TRUST-LEAK` 脱敏规则。
  - HTTP：`200`；body `{"data":[...非空...],"page":{...}}`。
  - `LogEntry` 7 键齐全；`message≤512`；`level∈{info,warning,error}`。
  - 响应文本与 `message`/`module` 不含 `9832`/`omlx-secret-key.txt`/`mnm_api_key`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `data` 非空数组 + `LogEntry` 键集正确 + **不含 `9832`** 及其它敏感字面。
  - **FAIL**：status 非 200、`data` 空/非数组、字段缺失、或出现 `9832`/敏感字面。
  - **BLOCKED**：fixture/断言逻辑问题、或窗内确无日志且无法构造（记录并复核窗口）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不改日志/配置/注入。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含 from/to）、原始 HTTP status/body（入库前脱敏 Authorization、`9832`、key 文件内容）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`constants.recent_window`；`LogPage`/`LogEntry` 机器契约；`OperationalLog.page`/`_SENSITIVE`；机制 `T-TRUST-LEAK`。自动化入口 [`ST-LOGS-001.py`](../../../../tests/system/cases/ST-LOGS-001.py)。**不依赖**其它 Case；与 ST-LOGS-002、ST-AUDIT-001 互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
