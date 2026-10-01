<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-SCAN-001 — 退役路径/响应头 absence 扫描

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-SCAN-001` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-SCAN-001.md` |
| Supersedes | `ST-04` |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-SCAN-001`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 接口面（absence 静态契约）、`CT-SCOPE-001`/`CT-BOUNDARY-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为按 `tests.asset-design` 约束的临时替身实例）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-SCAN-001` / 系统设计 §8 接口面（absence 静态契约） / 无运行层 VRC（见方案 §4 裁决） / `boundary` / `P1`
- **测试方法（§1.5 方法表行）**：边界值抽样 + 反例驱动（ERR-*）（absence 路径/响应头/回显的反例扫描）
- 方案清单登记：`ST-SCAN-001`（与 §3 权威清单一致；本文件名 `st-scan-001.md`，唯一对应）。
- 要测什么（责任展开）：对机器契约（OpenAPI `paths`、兼容清单 capability `path`）与活体 `/healthz` 响应做 absence 扫描——退役/越界路径（`/call`、`/admin/v0/*`、`/legacy/`）不得出现在契约中，`X-Legacy-*` 响应头与框架版本号不得出现在活体响应头，请求携带的敏感值不得被回显。
- 明确不测什么 / 失败含义：不测运行层端点的正向/负向契约（由 `ST-MODEL-*`/`ST-RESP-*`/`ST-AUTH-*` 等承接）；不测 secret 在审计/日志中的脱敏（ST-AUDIT-001/ST-LOGS-001）。失败含义＝退役接口回潮或响应头/回显越界。

**目的（被测契约）**：验证 V0.3 契约面的 **absence 边界**——机器契约只暴露当前 `/v1/*` 面，不含退役路径；活体响应不回显敏感头且不暴露框架版本。被测对象：静态 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json) `paths`、[`compatibility-manifest-v0.3.json`](../../../../interfaces/compatibility/compatibility-manifest-v0.3.json)、活体 `GET /healthz`。契约 `CT-SCOPE-001`/`CT-BOUNDARY-001`（[系统测试方案 §3.6](../llmtier-system-test-scheme.md#36-需求lt--到-case-的可追溯映射3-的-36-等价节)）。**不证明什么**：不证明任何运行层端点行为；不证明 secret 在审计/日志脱敏。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，空 `settings`；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；fixture `llmtier_b_empty`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；静态扫描不需实例（直接读仓库契约文件）。TS-002：私有端点由临时实例承载；无上游调用。

## 3. 输入构造

- **输入与构造**：
  - 静态：读取 `interfaces/openapi/llmtier.openapi.json` 与 `interfaces/compatibility/compatibility-manifest-v0.3.json`。
  - 活体：对 `llmtier_b_empty` 的 `/healthz` 发朴素 GET；再发一次携带 `X-Custom-Auth: Bearer probe-secret` 的 GET（回显探测）。
  - forbidden 路径反例集：`^/call$`、`^/call/`、`^/admin/v0/.*$`、`/legacy/`、`/admin/v0\.`；forbidden 头前缀：`X-Legacy-`。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. 解析 OpenAPI，枚举全部 `paths`；断无路径命中任一 forbidden 模式。
  2. 解析兼容清单；断文本不含 `"/call"`、`"/admin/v0`；断每个 capability `path` 不命中 forbidden 模式。
  3. `GET /healthz`（空实例）；断无 `X-Legacy-*` 响应头；断 `Server` 头不含 `0.3.0`。
  4. `GET /healthz` 带 `X-Custom-Auth: Bearer probe-secret`；断响应头与响应体均不含 `probe-secret`。

**重点关注步骤**：① forbidden 模式必须以 `re.match` 锚定路径（非子串），避免误报；② 活体扫描须覆盖响应**全体**头（不止 Server）；③ 回显扫描须同时覆盖头与 body。

## 5. 独立 Oracle 与预期结果

- **期望结果与独立 Oracle**：独立 Oracle = `CT-SCOPE-001`/`CT-BOUNDARY-001`（absence 契约）+ HTTP 头部语义（不暴露框架版本、不回显请求头）。
  - OpenAPI：无 forbidden 路径。
  - 兼容清单：无 forbidden 字面/路径。
  - `/healthz`：200；无 `X-Legacy-*`；`Server` 不含 `0.3.0`；无 `probe-secret` 回显。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：四类扫描全无命中。
  - **FAIL**：任一 forbidden 路径/头/版本/回显命中。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：把静态契约缺失当成"运行行为命中"——见[系统测试计划 §7](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：纯读——静态文件只读，活体仅 `/healthz`；无副作用。临时实例由 fixture teardown `stop()` + 临时目录删除。

## 7. 自动化位置与状态

- **证据与 Run**：保存扫描出的 forbidden 命中集（如有）、`/healthz` status/headers 快照、命令与 exit code；落位与契约见[系统测试计划 §6](../llmtier-system-test-plan.md#6-证据与-run-记录规则)。
- **依赖**：`llmtier_b_empty` fixture；`CT-SCOPE-001`/`CT-BOUNDARY-001`；静态契约文件。自动化入口 [`ST-SCAN-001.py`](../../../../tests/system/cases/ST-SCAN-001.py)（**Implemented**）。**不依赖**其它 Case；承接方案 §4 absence 裁决（`LT-FUN-007`/`LT-INT-003`/`LT-REL-002`）。

> 实现状态：见上文「依赖」的自动化入口（Implemented）；执行状态与 Verdict 只在 Run 报告。
