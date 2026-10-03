<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUSAGE-001 — 管理面 usage

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUSAGE-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-AUSAGE-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-AUSAGE-001`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUSAGE-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUSAGE-001` / 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） / `VRC-MGMT-006` / `normal` / `P1`
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-AUSAGE-001`（与 计划 §3 权威清单一致；本文件名 `st-ausage-001.md`，对应 §3.4 索引 `cases/st-ausage-001.md`）。
- 要测什么（责任展开）：`GET /v1/usage?from&to`（admin 视角）返回聚合用量页：HTTP 200 + `UsagePage`（`data`/`next_cursor`/`has_more`/`snapshot_id`/`snapshot_at`）。
- 明确不测什么 / 失败含义：不证明 cursor 分页边界（ST-AUSAGE-002）、不证明 `DELETE /v1/usage` 清空（ST-AUSAGE-003）、不证明 data 主体隔离（ST-USAGE-006）、不证明 cursor 过期（ST-USAGE-004）、不证明缺窗 400（`/v1/usage` 缺 `from`/`to` 由 `app.py` 拒绝，未单独构 case）。

**目的（被测契约）**：验证管理面 usage 查询的**聚合读契约与页信封**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，`from`/`to` **必填**，query `model`/`request_id`/`cursor`/`limit` 可选，`security`=data 或 admin）；
[`app.py`](../../../../src/http_api/app.py) 用 `_auth_either()`，admin 主体 `admin=True` 时 [`UsageRecorder._page`](../../../../src/inference/usage.py) **不加 principal 过滤**（见全局），返回 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`，窗口 `v.recorded_at>=from AND <to`（**半开**）、稳定排序 `(recorded_at,request_id)`。
设计验证项 `VRC-MGMT-006`；机制 `R-MET-02`、`T-MET-FINAL`；需求/机制链 `LT-FUN-004`、`LT-OPS-002`、`CT-USAGE-001`。**不证明什么**：不证明 cursor 分页边界（ST-AUSAGE-002）、不证明 `DELETE /v1/usage` 清空（ST-AUSAGE-003）、不证明 data 主体隔离（ST-USAGE-006）、不证明 cursor 过期（ST-USAGE-004）、不证明缺窗 400（`/v1/usage` 缺 `from`/`to` 由 `app.py` 拒绝，未单独构 case）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=计划 §3 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；时间窗用动态 [`recent_window()`](../../../../tests/system/constants.py)；初始状态=§2.3 A 类基线。
  > **实现注记**：无 `cursor` 的 usage 查询会向 `query_snapshots`/`query_snapshot_items` 写入一条 kind=`usage` 的冻结快照（10 min TTL，`next_cursor` 指向它）。这是读操作的持久化副作用；本 case 不断言它，清理见"清理与复位"。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/usage?from=<recent_window.from>&to=<recent_window.to> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`from`/`to` 动态近窗；不传 `cursor`/`limit`（默认 `limit=100`）、不传 `model`/`request_id`（admin 全局视图）；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/usage", params={"from": since, "to": until})`。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言五键齐全 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`（`UsagePage.required`）；`data` 为数组、`has_more` 为 bool、`snapshot_id` 为非空字符串、`snapshot_at` 为 RFC3339 字符串。
  5. 断言一致性：`has_more is False ⇒ next_cursor is None`（`UsagePage.allOf` 的 if/then）；`has_more is True ⇒ next_cursor` 为非空字符串（形如 `"<snapshot_id>:<offset>"`）。
  6. 抽查 `data` 元素含 `UsageRecord` 键 `{request_id,record_version,is_final,model,endpoint,recorded_at,updated_at,measurement_status,source,input_tokens,output_tokens,total_tokens,cached_input_tokens,cache_write_tokens,reasoning_tokens}`。

**重点关注步骤**：① **页信封 identity**——五键缺一不可（与 `AdminPageMeta` 的 `{has_more,next_cursor}` 不同，`UsagePage` 多出 `snapshot_id`/`snapshot_at`）；
② **admin 全局视图**——admin 主体不加 principal 过滤（data 主体仅见自身，属 ST-USAGE-006），本 case 只断结构不断言跨主体内容；③ **`snapshot_id`/`snapshot_at`**——无 cursor 请求必回填本次快照 id 与创建时间；
④ **半开窗**——`[from,to)`；⑤ **读操作副作用**——第 2 步会写一条 `query_snapshots`，不得据此判 FAIL，也不得宣称绝对零写；⑥ **不硬编码数值**——`data` 条数与内容随 m5air 运行变化。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `UsagePage`/`UsageRecord` + 半开窗/稳定排序规则。
  - HTTP：`200`；body `{"data":[...],"next_cursor":<str|null>,"has_more":<bool>,"snapshot_id":"snap_…","snapshot_at":<RFC3339>}`。
  - `has_more` 与 `next_cursor` 一致。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 五键齐全 + 类型正确 + `has_more`/`next_cursor` 一致 + `data` 元素含 `UsageRecord` 键。
  - **FAIL**：status 非 200、缺任一页字段、类型错、一致性违反、或出现错误信封。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或硬编码时间窗——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需业务 teardown**——只读查询不改账本/配置；查询写入的临时 `query_snapshots` 行有 10 min TTL、由服务自行过期，不作为残留清理对象。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含 from/to）、原始 HTTP status/body、`snapshot_id`/`snapshot_at`、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`constants.recent_window`；`UsagePage`/`UsageRecord` 机器契约；`UsageRecorder._page`；机制 `R-MET-02`/`T-MET-FINAL`。自动化入口 [`ST-AUSAGE-001.py`](../../../../tests/system/cases/ST-AUSAGE-001.py)。**不依赖**其它 Case；与 ST-AUSAGE-002/03 互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
