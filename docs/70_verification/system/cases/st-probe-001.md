<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-probe-001 — 探测缺确认

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-probe-001` |
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
| Canonical Path | `docs/70_verification/system/cases/st-probe-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-probe-001`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 探测接口（POST /v1/probes）（parent `llmtier-system-design`），设计验证项 `VRC-DIAG-004`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-probe-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-probe-001` / 系统设计 §8 探测接口（POST /v1/probes） / `VRC-DIAG-004` / `negative` / `P0`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-probe-001`（与 §3.2 权威清单一致；本文件名 `st-probe-001.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/probes` 缺显式确认：HTTP 400 `confirmation_required`。
- 明确不测什么 / 失败含义：不证明 带确认的成功探测（ST-probe-002）、不证明未知 deployment 的 404（ST-probe-003）、不证明探测对 deployment health 的写入（ST-probe-002/`apply_probe_result`）、不证明认证负向（ST-auth-003/09）。

**目的（被测契约）**：验证外部探测的**显式确认门**。被测端点/规则：`POST /v1/probes`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `probeDeployment`，body `ProbeRequest`=`{deployment_id,confirm_external_call}`，`security=AdminBearerAuth`）；[`AdminService.probe`](../../../../src/management/admin.py) 首行按 `confirm_external_call` 确认门规则校验（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-DIAG-004`；错误目录 `ERR-CONFIRM` → wire `code=confirmation_required`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-OBS-01`、`CT-ADMIN-001`、`CT-OPS-001`。**不证明什么**：不证明带确认的成功探测（ST-probe-002）、不证明未知 deployment 的 404（ST-probe-003）、不证明探测对 deployment health 的写入（ST-probe-002/`apply_probe_result`）、不证明认证负向（ST-auth-003/09）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。本 case 为**拒绝路径**，不触上游、不产生费用。

## 3. 输入构造

- **输入与构造**：
  ```http
  POST /v1/probes HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {}
  ```
  构造点：空对象使 `body.get("confirm_external_call") is True` 为假且键集不符；**不**提供 `deployment_id`（拒绝发生在 deployment 解析之前）。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.post("/v1/probes", json={})`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="confirmation_required"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （可选交叉核对）`POST /v1/probes` body `{"deployment_id":"dep_local_gemma"}`（有 deployment 但无 confirm）→ 仍 400 `confirmation_required`（确认门先于资源解析）。

**重点关注步骤**：① **确认门优先**——缺 `confirm_external_call` 必须在**任何上游调用/deployment 解析前**返回 400，不得先 404/502；② **错误码正确性**——是 `confirmation_required`（`ERR-CONFIRM`），不是 `invalid_request`（键集/确认联合 `require` 统一抛 `confirmation_required`）；③ **零副作用**——拒绝不触上游、不写 `probe_results`、不改 `deployments.health`、不产生费用；④ **错误信封 identity**——恰 5 键、`type=request_error`；⑤ **审计**——本路径直接用 `app.admin.probe`（非 `mutate`），故**不**写审计；不得期望审计行。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 探测确认规则。
  - HTTP：`400`；body `{"error":{"message":"Probe requires explicit confirmation","type":"request_error","code":"confirmation_required","param":null,"retryable":false}}`。
  - 无上游调用、无 health 变化。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="confirmation_required"` + `type=="request_error"`，且无上游/health 副作用。
  - **FAIL**：status 非 400、`code` 错、或观察到上游调用/health 变更。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存POST 请求与原始 400 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照（`GET /v1/deployments/dep_local_gemma` 前后 health 对比以证无副作用）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ProbeRequest` 机器契约；`AdminService.probe` 的 `require`；错误目录 `ERR-CONFIRM`。自动化入口 [`at_adm_probe_01.py`](../../../../tests/system/api_test_v03/at_adm_probe_01.py)。**不依赖**其它 Case；与 ST-probe-002（带确认→200）互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
