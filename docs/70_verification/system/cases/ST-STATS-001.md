<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-STATS-001 — 统计聚合

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-STATS-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-STATS-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-STATS-001`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 统计接口（GET /v1/stats）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-STATS-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-STATS-001` / 系统设计 §8 统计接口（GET /v1/stats） / `VRC-MGMT-006` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-STATS-001`（与 §3.2 权威清单一致；本文件名 `st-stats-001.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/stats?from&to` 返回时间窗内 token 用量聚合：HTTP 200 + `{from,to,group_by,data[]}`（半开窗 `[from,to)`）。
- 明确不测什么 / 失败含义：不证明 `group_by=tier` 的显式分支细节（ST-STATS-002）、不证明缺时间窗 400（ST-STATS-003）、不证明 usage 分页（ST-AUSAGE-002）、不证明账本写入时机（ST-USAGE-002）。

**目的（被测契约）**：验证管理统计的**聚合读契约与半开时间窗**。被测端点/规则：`GET /v1/stats`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getUsageStats`，query `from`/`to` **必填**，`group_by∈{tier,deployment}` 默认 `tier`，`security=AdminBearerAuth`）；
[`app.py`](../../../../src/http_api/app.py) 缺 `from`/`to` → 400；[`AdminService.stats`](../../../../src/management/admin.py) 以 `v.recorded_at>=?
 AND v.recorded_at<?`（**半开**）聚合 `usage_record_versions`（只计 head version），返回 `{from,to,group_by,data[]}`。设计验证项 `VRC-MGMT-006`；
需求/机制链 `LT-FUN-006`、`R-MET-03`、`T-MET-FINAL`、`CT-USAGE-001`。**不证明什么**：不证明 `group_by=tier` 的显式分支细节（ST-STATS-002）、不证明缺时间窗 400（ST-STATS-003）、不证明 usage 分页（ST-AUSAGE-002）、不证明账本写入时机（ST-USAGE-002）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；时间窗用 [`constants.recent_window()`](../../../../tests/system/constants.py)（**动态**：`now-30d … now`，RFC3339 `Z`，秒精度），不得硬编码日期。初始状态=§2.3 A 类基线；本 case 只读。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/stats?from=<recent_window.from>&to=<recent_window.to> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`from`/`to` 取动态近窗口（覆盖 m5air 既有 usage）；不显式传 `group_by`（用默认 `tier`）；不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/stats", params={"from": since, "to": until})`；记录 status、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言含 `from`、`to`、`group_by`、`data` 四键；`from==since`、`to==until`（回显）、`group_by=="tier"`（默认）、`data` 为数组。
  5. 抽查每个 `data` 元素键集含 `{tier,calls,measured_calls,unknown_calls,input_tokens,output_tokens,total_tokens,cached_tokens,cache_write_tokens,reasoning_tokens}`（`AdminService.stats` 的 tier 分支，`admin.py:59-61`），且 `calls` 为 int。
  6. （可选）交叉核对：`request_id` 型查询——本 case 不断言具体数值，只断结构。

**重点关注步骤**：① **半开窗**——SQL 条件为 `>=from AND <to`；记录恰好落在 `to` 的记录不计入（可在报告中说明，但本 case 主断言为聚合结构）；② **必填 query**——`from`/`to` 缺任一 → 400（ST-STATS-003），本 case 必传；
③ **回显一致性**——`body.from/to` 必须等于请求参数（未做时区/格式改写）；④ **默认 `group_by`**——不传时为 `"tier"`（实现 `query.get("group_by",["tier"])`）；
⑤ **只计 head version**——聚合 join `usage_heads` 且 `record_version=head_record_version`，不得重复计历史版本（结构断言，不断言总数）；⑥ **纯读**——`stats` 直接查库，不创建 `query_snapshots`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `AdminService.stats` 的返回 schema + 半开窗规则。
  - HTTP：`200`；body `{"from":<since>,"to":<until>,"group_by":"tier","data":[...]}`。
  - `data` 元素为 tier 聚合行，键集为上述 10 键；`calls` 等为 int。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 四键齐全 + `from`/`to` 回显一致 + `group_by=="tier"` + `data` 为数组且元素键集正确。
  - **FAIL**：status 非 200、缺键、回显不符、`data` 非数组、元素键集错、或出现错误信封。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或硬编码日期窗冒充动态窗——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不改账本/配置/注入。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含 from/to）、原始 HTTP status/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`constants.recent_window`；`AdminService.stats`；机制 `R-MET-03`/`T-MET-FINAL`。自动化入口 [`ST-STATS-001.py`](../../../../tests/system/cases/ST-STATS-001.py)。**不依赖**其它 Case；与 ST-STATS-002（显式 group_by=tier）/03（缺窗 400）互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
