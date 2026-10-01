<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-sl-002 — 创建非 fixed tier

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-sl-002` |
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
| Canonical Path | `docs/70_verification/system/cases/st-sl-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-sl-002`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-sl-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-sl-002` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-sl-002`（与 §3.2 权威清单一致；本文件名 `st-sl-002.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/service-levels` 用非固定 Tier 的 `id` 创建：HTTP 400 `invalid_request`，`param="id"`。
- 明确不测什么 / 失败含义：不证明 已存在固定 Tier 的重复创建 409（ST-sl-012）、不证明成员能力/向量空间校验（ST-sl-006/07）、不证明成功创建（无正向 Case；固定 Tier 由 bootstrap/`ensure_fixed_tiers` 预置）、不证明认证负向（ST-auth-003/09）。

**目的（被测契约）**：验证 Service Level 创建的 **固定 Tier 白名单校验**。被测端点/规则：`POST /v1/service-levels`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createServiceLevel`，body `ServiceLevelWrite`={`id`,`deployment_ids`,`enabled`}，`security=AdminBearerAuth`）；[`registry.create_service_level`](../../../../src/management/registry.py) 先做 body 键集校验，再做固定 Tier 白名单校验（非 `FIXED_TIERS` id → 400 `invalid_request`，[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-MGMT-002`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明已存在固定 Tier 的重复创建 409（ST-sl-012）、不证明成员能力/向量空间校验（ST-sl-006/07）、不证明成功创建（无正向 Case；固定 Tier 由 bootstrap/`ensure_fixed_tiers` 预置）、不证明认证负向（ST-auth-003/09）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=7 fixed tier 已存在、`diagnostic_injections` 为空。

## 3. 输入构造

- **输入与构造**：固定请求：
  ```http
  POST /v1/service-levels HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"id": "CustomTier", "deployment_ids": ["depl_b"], "enabled": true}
  ```
  构造点：`id="CustomTier"` 不在 `FIXED_TIERS`；`deployment_ids` 引用真实 `depl_b`（保证失败点确为 id 校验而非后续引用错误）；`enabled=true`。不注入故障；不构造其它非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `resp = admin_client_b.post("/v1/service-levels", json={"id":"CustomTier","deployment_ids":["depl_b"],"enabled":True})`。
  3. 断言 `resp.status_code == 400`。
  4. `err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["param"]=="id"`、`"not a fixed Tier" in err["message"]`；核对 `err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels` 断言 `CustomTier` 不存在，且 7 fixed tier 仍在。

**重点关注步骤**：① **拒绝位置**——必须在写库前拒绝（`require` 在 `txn` 之前），`CustomTier` **不得**出现在资源表；② **错误信封 identity**——恰 5 键 `{message,type,code,param,retryable}`（无 `category`），`param=="id"`，`type` 由 400 导出为 `request_error`；③ **区分 400 与 409**——本 case 是非白名单 id（400），不同于已存在固定 Tier 的 409 `resource_conflict`（ST-sl-012）；④ **审计副作用**——经 `AdminService.mutate` 的失败会在 `audit_events` 记 `action="service_level.create"`、`result="failed"`、`request_id`，这是允许的审计记录、不是资源创建；不得误判为零写入；⑤ **不硬编码 message 全文**，断言稳定子串 `"not a fixed Tier"`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `FIXED_TIERS` 白名单规则。
  - HTTP：`400`；`Content-Type: application/json`；body `{"error":{"message":"Service Level ID is not a fixed Tier","type":"request_error","code":"invalid_request","param":"id","retryable":false}}`。
  - 资源表：`GET /v1/service-levels` 无 `CustomTier`。
  - 审计：`audit_events` 出现一条 `result="failed"` 的 `service_level.create`（可选交叉核对）。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `param=="id"` + `type=="request_error"`，且 `CustomTier` 未被创建。
  - **FAIL**：status 非 400（含 409/500）、`code`/`param` 错、`CustomTier` 被写入。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充被测服务，或未真正发往 B 实例——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——失败未创建资源。退出前确认 `GET /v1/service-levels` 仅 7 fixed tier、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存POST 请求/原始响应（错误信封，脱敏后）、teardown 前 `GET /v1/service-levels` 快照、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ServiceLevelWrite` 机器契约；`registry.create_service_level`/`FIXED_TIERS`。自动化入口 [`at_adm_sl_02.py`](../../../../tests/system/api_test_v03/at_adm_sl_02.py)。**不依赖**其它 Case；与 ST-sl-012（已存在固定 Tier→409）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
