<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-pusage-002 — 刷新缺确认

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-pusage-002` |
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
| Canonical Path | `docs/70_verification/system/cases/st-pusage-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-pusage-002`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage）（parent `llmtier-system-design`），设计验证项 ``VRC-MGMT-006`、`VRC-DIAG-004``；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-pusage-002` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-pusage-002` / 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） / ``VRC-MGMT-006`、`VRC-DIAG-004`` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-pusage-002`（与 §3.2 权威清单一致；本文件名 `st-pusage-002.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/providers/{id}/usage` 未携带显式二次确认：HTTP 400，统一错误信封；**缺 `confirm_external_call` 键**时实际 `code=="invalid_request"`，键存在但值非 `true` 时为 `code=="confirmation_required"`。
- 明确不测什么 / 失败含义：不证明 带确认刷新（ST-pusage-003）、不证明只读快照（ST-pusage-001）、不证明未知 provider 的 404（ST-pusage-004）、不证明上游用量 API 行为；本 case 的拒绝必须**在触上游之前**完成（无外部调用、无快照写入）。

**目的（被测契约）**：验证 provider 账号用量**刷新缺确认的拒绝契约**。被测端点/规则：`POST /v1/providers/{provider_id}/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `refreshProviderAccountUsage`，`security=AdminBearerAuth`），请求体 schema `additionalProperties:false`、`required=[confirm_external_call]`、`confirm_external_call.const=true`。入口 [`app.py`](../../../../src/http_api/app.py) 先做**键集精确检查** `set(body) != {"confirm_external_call"}` → 400 `invalid_request`（`param=null`）；仅当键集通过、值非 `true` 时才落入 [`AccountUsageService.refresh`](../../../../src/management/account_usage.py) 的 `require(confirm_external_call is True, 400, "confirmation_required", …)`。设计验证项 `VRC-MGMT-006`、`VRC-DIAG-004`；需求/机制链 `LT-FUN-005/006`、`LT-OPS-002`、`R-CFG-01`、`R-OBS-01`、`T-CFG-SECRET`、`CT-ADMIN-001`/`CT-OPS-001`。**不证明什么**：不证明带确认刷新（ST-pusage-003）、不证明只读快照（ST-pusage-001）、不证明未知 provider 的 404（ST-pusage-004）、不证明上游用量 API 行为；本 case 的拒绝必须**在触上游之前**完成（无外部调用、无快照写入）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 §2.1.6 必需的 `provider_local`。执行前记录 `GET /v1/providers/provider_local/usage` 的快照（`checked_at`）以便证明拒绝路径未写快照。

## 3. 输入构造

- **输入与构造**：两条拒绝输入（均**不**含有效确认）：
  ```http
  POST /v1/providers/provider_local/usage HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {}
  ```
  ```json
  {"confirm_external_call": false}
  ```
  构造点：输入 A = 空对象 `{}`（**缺键**）；输入 B = `{"confirm_external_call": false}`（**键在、值非真**）；两者键集均**不**满足有效刷新。不注入故障；provider_id 固定为既存 `provider_local`（存在性不干扰本负向）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 记录前置快照：`before = admin_client.get("/v1/providers/provider_local/usage")`；记 `before.json()["checked_at"]`。
  3. 输入 A：`resp_a = admin_client.post("/v1/providers/provider_local/usage", json={})`；断言 `404/403` 均不出现。
  4. 断言 `resp_a.status_code == 400`；`err_a = resp_a.json()["error"]`：键集恰为 5 键、`err_a["code"] == "invalid_request"`、`err_a["type"] == "request_error"`、`err_a["param"] is None`、`err_a["retryable"] is False`。
  5. 输入 B：`resp_b = admin_client.post(..., json={"confirm_external_call": False})`；断言 `400` 且 `err_b["code"] == "confirmation_required"`、`err_b["type"] == "request_error"`。
  6. 断言零副作用：再次 `GET /v1/providers/provider_local/usage`，`checked_at` 与第 2 步 `before` 一致（未刷新、未触上游）。

**重点关注步骤**：① **两条拒绝臂的 code 不同**——空对象（缺键）实际为 `invalid_request`（入口键集检查先于确认值检查），`confirmation_required` 仅由"键在、值非真"触发；不得把两者混为一谈；② **拒绝先于外部调用**——400 必须在触上游与写 `provider_usage_snapshots` 之前完成（第 6 步以 `checked_at` 不变证明）；③ **信封 identity**——恰 5 键、`type="request_error"`、`param=null`、`retryable=false`；④ **provider 存在性不干扰**——用既存 `provider_local`，使唯一拒绝原因就是缺确认；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable。
  > **契约 vs 实现偏差（登记，本 case 以实际源码为准断言）**：§3.2 `ST-pusage-002` 与系统设计 §7.8 `ERR-CONFIRM` 描述"缺二次确认 → `confirmation_required`（400）"，但实际实现中**缺键**返回 `invalid_request`（[`app.py`](../../../../src/http_api/app.py) 第 269 行的键集检查），仅 `{"confirm_external_call": false}` 才返回 `confirmation_required`（[`account_usage.py`](../../../../src/management/account_usage.py) 第 158 行）。现有 [`at_adm_prov_usage_02.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_02.py) 只覆盖空对象臂并断言 `invalid_request`。本 case 同时断言两臂，以完整覆盖 `ERR-CONFIRM` 语义；偏差在运行报告登记。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-CONFIRM`（并对照实际实现的 code 分流）。
  - 输入 A（`{}`）：`400`；`error.code == "invalid_request"`；5 键信封；`type="request_error"`。
  - 输入 B（`{"confirm_external_call": false}`）：`400`；`error.code == "confirmation_required"`；5 键信封；`type="request_error"`。
  - 零副作用：快照 `checked_at` 不变、无上游调用。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：输入 A 得 `400 invalid_request`、输入 B 得 `400 confirmation_required`，两信封均 5 键且 `type="request_error"`，且快照未变。
  - **FAIL**：任一 status 非 400、code 不符（含把两臂 code 写反）、信封缺/多键，或拒绝路径产生了快照写入/上游调用。
  - **BLOCKED**：无法执行/无法判定且可重试（断言逻辑/契约语义问题）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造 400 或替代路径冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——两条输入均为被拒请求，无写副作用；本 case 不刷新快照、不改 provider。退出前确认 `/readyz` 7 tier、provider 列表未变、无未清空注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：两条 POST 的请求与原始响应、前置与后置 `GET .../usage` 快照（证明零副作用）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；既存 provider `provider_local`；`ErrorEnvelope` 机器契约；系统设计 §7.8 `ERR-CONFIRM`；实现 `src/http_api/app.py` / `src/management/account_usage.py`；自动化入口 [`at_adm_prov_usage_02.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_02.py)。**不依赖**其它 Case；与 ST-pusage-003（带确认成功）互补，各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
