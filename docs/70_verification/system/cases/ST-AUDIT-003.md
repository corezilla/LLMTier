<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUDIT-003 — 审计非法分页参数

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUDIT-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-AUDIT-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-AUDIT-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 审计接口（GET /v1/audit）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-003`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUDIT-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUDIT-003` / 系统设计 §8 审计接口（GET /v1/audit） / `VRC-MGMT-003` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-AUDIT-003`（与 §3.2 权威清单一致；本文件名 `st-audit-003.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/audit?limit=abc` 非法分页参数：HTTP 400 `invalid_request`。
- 明确不测什么 / 失败含义：不证明 默认 50/边界 `limit=1`（ST-AUDIT-001/02）、不证明字段脱敏（ST-AUDIT-001）、不证明角色负向（`/v1/audit` 为 admin 守门，data 凭据的 403 属 ST-AUTH-003/09 的跨切面角色覆盖，**不是本 case**）、不证明 `cursor`（审计无 cursor）。
  > **规格注记**：§3.2 将 `ST-AUDIT-003` 登记为"审计非法分页参数 → 400 `invalid_request`"，§11.1 亦将 `ERR-REQ-VALIDATION` 映射到本 Case。`ST-RUNTIME-002` 才是 `data→403` 的角色负向。运行时若以 data 凭据访问 `/v1/audit`，会在 `_int_param` 之前被 admin 守门以 403 拒绝——本 case 不构造该路径。

**目的（被测契约）**：验证审计 `limit` 的**整数参数校验**。被测端点/规则：`GET /v1/audit`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listAuditEvents`，query `limit` `type:integer`）；[`app.py`](../../../../src/http_api/app.py) `app.audit.page(_int_param(query, "limit", 50))`，[`_int_param`](../../../../src/http_api/app.py) 对无法 `int()` 的输入抛 400 `invalid_request`（在 admin 鉴权后、handler 前）。设计验证项 `VRC-MGMT-003`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；机制 `R-OBS-01`；需求/机制链 `LT-FUN-006`、`R-OBS-01`、`CT-ADMIN-001`。**不证明什么**：不证明默认 50/边界 `limit=1`（ST-AUDIT-001/02）、不证明字段脱敏（ST-AUDIT-001）、不证明角色负向（`/v1/audit` 为 admin 守门，data 凭据的 403 属 ST-AUTH-003/09 的跨切面角色覆盖，**不是本 case**）、不证明 `cursor`（审计无 cursor）。
  > **规格注记**：§3.2 将 `ST-AUDIT-003` 登记为"审计非法分页参数 → 400 `invalid_request`"，§11.1 亦将 `ERR-REQ-VALIDATION` 映射到本 Case。`ST-RUNTIME-002` 才是 `data→403` 的角色负向。运行时若以 data 凭据访问 `/v1/audit`，会在 `_int_param` 之前被 admin 守门以 403 拒绝——本 case 不构造该路径。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；本 case 自动化入口 [`ST-AUDIT-003.py`](../../../../tests/system/cases/ST-AUDIT-003.py) 已实现（§3.2 `RUN`）。拒绝路径无副作用。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/audit?limit=abc HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`limit=abc` 为非整数（`int("abc")` 抛 `ValueError`）；凭据为 admin（使失败点确为参数解析而非 403）；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/audit", params={"limit": "abc"})`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （边界变体，可选）`limit=`（空串）与 `limit=1.5` 各断言 400 `invalid_request`。
  5. （对照，非本 case 判定）`GET /v1/audit?limit=1` 断言 200（证明 400 来自参数值而非端点/鉴权）。

**重点关注步骤**：① **非整数必须 400**——不得静默回退默认 50 或返回 200 空页；② **校验位置**——`_int_param` 在 admin 鉴权之后、`app.audit.page` 之前抛错，不触库、无副作用；③ **错误信封 identity**——恰 5 键、`type=request_error`、`code=invalid_request`；④ **param 语义**——`_int_param` 未传 `param`，故 `param==null`；⑤ **区分缺参**——`limit` 缺省是合法默认（50），本 case 锁"有值但非法"，二者不同；⑥ **非角色负向**——本 case 不是 data→403（见目的注记）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `limit` integer 类型规则。
  - HTTP：`400`；body `{"error":{"message":"limit must be an integer","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 无审计/配置副作用。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `type=="request_error"`（含可选变体）。
  - **FAIL**：status 非 400（含 200 静默回退）、`code` 错、或返回审计数据。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存请求 URL（含非法 `limit`）、原始 400 响应（脱敏后）、`limit=1` 对照响应、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`app.py::_int_param`；错误目录 `ERR-REQ-VALIDATION`。自动化入口 [`ST-AUDIT-003.py`](../../../../tests/system/cases/ST-AUDIT-003.py)。**不依赖**其它 Case；与 ST-AUDIT-001/02（成功/边界读）互补。

> 实现状态：Implemented（`ST-AUDIT-003.py`）；执行状态与 Verdict 只在 Run 报告。
