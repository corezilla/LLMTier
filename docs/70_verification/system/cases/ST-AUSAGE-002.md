<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUSAGE-002 — 管理面分页

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUSAGE-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-AUSAGE-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-AUSAGE-002`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUSAGE-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUSAGE-002` / 系统设计 §8 管理 usage 接口（GET/DELETE /v1/usage） / `VRC-MGMT-006` / `boundary` / `P1`
- **测试方法（§1.5 方法表行）**：边界值抽样 + 契约字段比对
- 方案清单登记：`ST-AUSAGE-002`（与 §3.2 权威清单一致；本文件名 `st-ausage-002.md`，对应 §3.4 索引 `cases/st-ausage-002.md`）。
- 要测什么（责任展开）：`GET /v1/usage?from&to&limit=1`（admin 视角）有界分页：HTTP 200 + `data.length ≤ 1` + 页元数据一致。
- 明确不测什么 / 失败含义：不证明 cursor 跨页去重/重放（ST-USAGE-003/07）、不证明过期 cursor 400（ST-USAGE-004）、不证明清空（ST-AUSAGE-003）、不证明 data 主体隔离（ST-USAGE-006）。本 case 只断 `limit=1` 边界与页元数据一致性。

**目的（被测契约）**：验证管理面 usage 的**有界分页与 cursor 元数据契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，query `limit` 默认 100/上限 200，`cursor` 可选）；[`UsageRecorder._page`](../../../../src/inference/usage.py) 冻结快照后 `LIMIT limit+1`，`more = len(rows) > limit`，返回 `next_cursor="<snapshot_id>:<offset+limit>" if more else None`，稳定排序 `(recorded_at,request_id)`。设计验证项 `VRC-MGMT-006`；机制 `T-MET-PAGE`；需求/机制链 `LT-FUN-004`、`R-MET-02`、`CT-USAGE-001`。**不证明什么**：不证明 cursor 跨页去重/重放（ST-USAGE-003/07）、不证明过期 cursor 400（ST-USAGE-004）、不证明清空（ST-AUSAGE-003）、不证明 data 主体隔离（ST-USAGE-006）。本 case 只断 `limit=1` 边界与页元数据一致性。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；时间窗用动态 [`recent_window()`](../../../../tests/system/constants.py)。只读（会写一条临时 `query_snapshots`）。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/usage?from=<recent_window.from>&to=<recent_window.to>&limit=1 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`limit=1`（下界边界）；`from`/`to` 动态近窗；不传 `cursor`（首页）；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/usage", params={"from": since, "to": until, "limit": 1})`。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `len(data) <= 1`；五键 `{data,next_cursor,has_more,snapshot_id,snapshot_at}` 齐全；`has_more` 为 bool。
  5. 断言一致性：`has_more is True ⇒ next_cursor` 非空且形如 `"<snapshot_id>:<offset>"`；`has_more is False ⇒ next_cursor is None`。
  6. （可选）用步骤 4 的 `next_cursor` 发第二页（同参数 + `cursor`），断言返回不重复且 `offset` 前进（本 case 不断言重放语义，仅作边界观察）。

**重点关注步骤**：① **`limit=1` 边界**——首页返回条数必须 ≤1（空表 0 亦合法）；② **`next_cursor` 与 `has_more` 一致**——`has_more=true` 时 `next_cursor` 必须非空且 `snapshot_id` 前缀与 `body.snapshot_id` 相同（cursor 绑定本次快照）；③ **稳定排序**——`(recorded_at,request_id)`；本 case 只断首页结构；④ **读取副作用**——写临时 `query_snapshots`，非 FAIL 依据；⑤ **不硬编码条数**——是否 `has_more` 取决于 m5air 窗内记录数，不得硬编码为真/假。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `UsagePage` + `limit` 边界 + cursor 绑定规则。
  - HTTP：`200`；body `{"data":[...≤1...],"next_cursor":<str|null>,"has_more":<bool>,"snapshot_id":"snap_…","snapshot_at":<RFC3339>}`。
  - `has_more`/`next_cursor` 一致；`next_cursor` 前缀 == `snapshot_id`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `len(data)≤1` + 五键齐全 + `has_more`/`next_cursor` 一致（含 cursor 前缀绑定）。
  - **FAIL**：status 非 200、`len(data)>1`、缺键、或一致性违反。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或硬编码 `has_more` 期望——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需业务 teardown**——只读；临时 `query_snapshots` 10 min TTL 自行过期。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含 limit）、原始 HTTP status/body、`snapshot_id`/`next_cursor`、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`constants.recent_window`；`UsagePage` 机器契约；`UsageRecorder._page`；机制 `R-MET-02`/`T-MET-PAGE`。自动化入口 [`ST-AUSAGE-002.py`](../../../../tests/system/cases/ST-AUSAGE-002.py)。**不依赖**其它 Case；cursor 重放/过期属 ST-USAGE-003/04/07。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
