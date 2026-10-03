<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-STATS-002 — 分组

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-STATS-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-STATS-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-STATS-002`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 统计接口（GET /v1/stats）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-STATS-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-STATS-002` / 系统设计 §8 统计接口（GET /v1/stats） / `VRC-MGMT-006` / `normal` / `P2`
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-STATS-002`（与 计划 §3 权威清单一致；本文件名 `st-stats-002.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/stats?group_by=tier` 显式按 tier 分组：HTTP 200 + `group_by=="tier"` + tier 聚合行。
- 明确不测什么 / 失败含义：不证明 默认分组（ST-STATS-001）、不证明 `group_by=deployment` 分支（未单独构 case）、不证明缺窗 400（ST-STATS-003）、不证明非法 `group_by` 的 400（`group_by ∉ {tier,deployment}` → 400，未单独构 case）。

**目的（被测契约）**：验证统计的**显式 `group_by=tier` 契约**。被测端点/规则：`GET /v1/stats`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getUsageStats`，query `group_by` enum `tier|deployment`）；
[`AdminService.stats`](../../../../src/management/admin.py) 在 `group_by=="tier"` 分支按 `v.model` 聚合（行含 `tier` 键）。设计验证项 `VRC-MGMT-006`；
需求/机制链 `LT-FUN-006`、`R-MET-03`、`CT-USAGE-001`。**不证明什么**：不证明默认分组（ST-STATS-001）、不证明 `group_by=deployment` 分支（未单独构 case）、不证明缺窗 400（ST-STATS-003）、不证明非法 `group_by` 的 400（`group_by ∉ {tier,deployment}` → 400，未单独构 case）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=计划 §3 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；时间窗用动态 [`recent_window()`](../../../../tests/system/constants.py)。初始状态=§2.3 A 类基线；只读。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/stats?from=<recent_window.from>&to=<recent_window.to>&group_by=tier HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：显式 `group_by=tier`（enum 合法值）；`from`/`to` 动态近窗；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/stats", params={"from": since, "to": until, "group_by": "tier"})`。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `group_by == "tier"`（回显）；`data` 为数组。
  5. 抽查每个 `data` 元素含 `tier` 键（非 deployment 分支的 `deployment_id` 等），且 `calls` 为 int、token 字段为 int。
  6. （可选）`model`/`tier` 值 ⊆ 已知 tier 集合或为空（不硬编码具体值）。

**重点关注步骤**：① **显式分支回显**——`body.group_by` 必须为 `"tier"`；② **行形状区分**——tier 分支行含 `tier` 键、deployment 分支行含 `deployment_id`/`deployment_name`/`backend_model`/`provider_*`；本 case 锁定 tier 形状，不得混入 deployment 键；③ **空数据合法**——窗内无记录时 `data==[]`，仍 PASS（只断形状/回显）；④ **半开窗**——同 ST-STATS-001（`[from,to)`）；⑤ **纯读**——不写库。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `AdminService.stats(stats,"tier")` 的 schema + enum 规则。
  - HTTP：`200`；body `{"from":…,"to":…,"group_by":"tier","data":[…]}`；`data` 元素含 `tier`/`calls`/`measured_calls`/`unknown_calls`/token 字段。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `group_by=="tier"` + `data` 为数组且元素为 tier 形状。
  - **FAIL**：status 非 200、`group_by` 回显错、`data` 非数组、行形状错（含 deployment 键）。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含 group_by）、原始 HTTP status/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`constants.recent_window`；`AdminService.stats` 的 tier 分支。自动化入口 [`ST-STATS-002.py`](../../../../tests/system/cases/ST-STATS-002.py)。**不依赖**其它 Case；与 ST-STATS-001（默认分组）/03 互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
