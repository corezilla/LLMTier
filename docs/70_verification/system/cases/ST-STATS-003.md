<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-STATS-003 — 缺时间窗

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-STATS-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-STATS-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-STATS-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 统计接口（GET /v1/stats）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-STATS-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-STATS-003` / 系统设计 §8 统计接口（GET /v1/stats） / `VRC-MGMT-006` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-STATS-003`（与 §3.2 权威清单一致；本文件名 `st-stats-003.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/stats` 缺 `from`/`to`：HTTP 400 `invalid_request`。
- 明确不测什么 / 失败含义：不证明 缺窗时的 usage/logs 同类校验（ST-AUSAGE-* 无缺窗 case、ST-LOGS-002）、不证明非法 `group_by` 400（未单独构 case）、不证明成功聚合（ST-STATS-001/02）、不证明认证负向（ST-AUTH-003/09）。

**目的（被测契约）**：验证统计查询的**必填时间窗校验**。被测端点/规则：`GET /v1/stats`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getUsageStats`，`from`/`to` 均 `required:true`）；
[`app.py`](../../../../src/http_api/app.py) 在鉴权后、handler 前执行 `from`/`to` 必填校验（缺任一 → 400 `invalid_request`）。设计验证项 `VRC-MGMT-006`；
错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；需求/机制链 `LT-FUN-006`、`R-MET-03`、`CT-USAGE-001`。**不证明什么**：不证明缺窗时的 usage/logs 同类校验（ST-AUSAGE-* 无缺窗 case、ST-LOGS-002）、不证明非法 `group_by` 400（未单独构 case）、不证明成功聚合（ST-STATS-001/02）、不证明认证负向（ST-AUTH-003/09）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；拒绝路径无副作用。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/stats HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：**不带 `from`/`to`**（也可构造只带其一的两种变体，均期望同一 400）；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/stats")`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （边界变体，可选）`GET /v1/stats?from=<since>`（缺 `to`）与 `GET /v1/stats?to=<until>`（缺 `from`）各断言 400 `invalid_request`。

**重点关注步骤**：① **必填两参数**——`from`/`to` 缺任一都必须 400，不是空窗聚合（不得返回 200 `{data:[]}` 冒充）；② **校验位置**——`app.py` 在带 admin 凭据分派后、调用 `AdminService.stats` 前抛错，不触库、无副作用；③ **错误信封 identity**——恰 5 键、`type=request_error`、`code=invalid_request`；④ **param 语义**——该 `raise` 未传 `param`，故 `param==null`；⑤ **不把 400 当 200 空页**——`usage_store_unavailable`/空 `data` 不属本 case。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `from`/`to` required 规则。
  - HTTP：`400`；body `{"error":{"message":"from and to are required","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 无账本/配置副作用。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `type=="request_error"`（三种缺参变体均如此）。
  - **FAIL**：status 非 400（含 200）、`code` 错、或返回空聚合。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL/headers、原始 400 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`app.py` 的 `from`/`to` 必填校验；错误目录 `ERR-REQ-VALIDATION`。自动化入口 [`ST-STATS-003.py`](../../../../tests/system/cases/ST-STATS-003.py)。**不依赖**其它 Case；与 ST-STATS-001/02 的成功路径互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
