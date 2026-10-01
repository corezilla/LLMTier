<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-SL-008 — 非法类型输入校验（非数组 deployment_ids）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-SL-008` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-SL-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-SL-008`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-SL-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-SL-008` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `recovery` / `P2`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（类型守卫 400 invalid_request）
- 方案清单登记：`ST-SL-008`（与 §3.2 权威清单一致；本文件名 `st-sl-008.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/service-levels/{id}` 用非数组 `deployment_ids`：HTTP 400 `invalid_request`、`param="deployment_ids"`，零副作用。
- 明确不测什么 / 失败含义：不证明 合法 PATCH（ST-SL-004）、不证明键白名单 400（ST-SL-013）、不证明能力/向量空间冲突 409（ST-SL-006/07）、不证明审计/日志（ST-AUDIT-001/ST-LOGS-001）。本 case 锁 400 类型校验契约（见 §7 修订注记）。

**目的（被测契约）**：验证统一 `ErrorEnvelope` 在**非法类型输入**路径上的契约。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，`ServiceLevelPatch.deployment_ids` 类型应为 `array`）；[`registry._capability_intersection`](../../../../src/management/registry.py) 在迭代前显式校验 `isinstance(deployment_ids, list) and all(isinstance(rid, str) for rid in deployment_ids)`，非数组输入 `raise ApiError(400, "invalid_request", "deployment_ids must be an array of strings", "deployment_ids")`（L300），不再抛 `TypeError → 500`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；机制 `R-CFG-01`；需求/机制链 `LT-FUN-005`、`CT-ADMIN-001`。**不证明什么**：不证明合法 PATCH（ST-SL-004）、不证明键白名单 400（ST-SL-013）、不证明能力/向量空间冲突 409（ST-SL-006/07）、不证明审计/日志（ST-AUDIT-001/ST-LOGS-001）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；本 case 已有实现（`at_adm_sl_08.py`）。初始状态=`Worker` 存在。

## 3. 输入构造

- **输入与构造**：
  ```http
  PATCH /v1/service-levels/Worker HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"deployment_ids": 1}
  ```
  构造点：`deployment_ids` 为 JSON **number**（非 array；`_capability_intersection` 的类型守卫当场拒绝）；`If-Match` 取真实 ETag（使失败点落在类型校验而非 412）；body 键集仍 ⊆ 白名单（否则被更早的键校验拦）。
  > **类型选择**：`ServiceLevelPatch.deployment_ids` 类型应为 `array`；任意非数组 JSON 类型（整数/布尔/null/字符串/对象）都应返回 400 `invalid_request`——本 case 以整数为例。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Worker")`；断言 200；记 `etag`、`version_before`。
  3. `resp = admin_client_b.patch("/v1/service-levels/Worker", json={"deployment_ids": 1}, headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言键集**恰为** `{message,type,code,param,retryable}`、`err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["param"]=="deployment_ids"`、`err["retryable"] is False`。
  5. 断言响应体**不含** Python traceback（`Traceback`/`File "`）、`TypeError`、`'int' object`、secret 字面 `9832`、`omlx-secret-key.txt`（脱敏校验）。
  6. （零副作用核验）`GET /v1/service-levels/Worker` 断言 `version==version_before`。

**重点关注步骤**：① **命中类型守卫**——非数组输入被 `_capability_intersection` 的 `isinstance(deployment_ids, list)` 守卫拒绝为 400 `invalid_request`（不再 500）；② **信封 identity**——恰 5 键、`type="request_error"`、`code=invalid_request`、`param="deployment_ids"`；③ **不泄露**——body 不得含 traceback/内部类型信息/secret；④ **零副作用**——`Worker.version` 不变；⑤ **审计**——失败经 `mutate` 记 `result="failed"`，属允许的审计记录。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail`（5 键）+ `ServiceLevelPatch.deployment_ids` 的 `array` 类型约束 + `ApiError.envelope` 的 `type` 由状态导出规则。
  - HTTP：`400`；`Content-Type: application/json`；body `{"error":{"message":"<nonempty>","type":"request_error","code":"invalid_request","param":"deployment_ids","retryable":false}}`。
  - 脱敏：body 不含 traceback / `TypeError` / 内部类型字符串 / secret 字面。
  - 资源：`Worker.version` 不变。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + 恰 5 键信封 + `code=="invalid_request"` + `type=="request_error"` + `param=="deployment_ids"`；`Worker.version` 不变。
  - **FAIL**：status 非 400（尤其 500 `internal_error`——类型守卫缺失）、信封键集不符、`code`/`param`/`type` 错、泄露内部信息、或 `Worker` 被改。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
  - **INVALID**：用 `127.0.0.1`/mock 冒充被测服务——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需业务 teardown**——拒绝在写库前发生，无资源改动。退出前确认 7 tier 齐全、`Worker.version` 未变、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/api_test_v03/at_adm_sl_08.py`（**Implemented**）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_adm_sl_08.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

- **证据与 Run**：保存GET/PATCH 的请求与原始 400 响应（脱敏后）、`Worker` 前后 `version`、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`registry._capability_intersection`（含类型守卫）；错误目录 `ERR-REQ-VALIDATION`；机制 `R-CFG-01`。自动化入口 [`at_adm_sl_08.py`](../../../../tests/system/api_test_v03/at_adm_sl_08.py)。**不依赖**其它 Case；与 ST-SL-013（键白名单 400）互为"输入校验"的正/反例。

> 实现状态：Implemented（`at_adm_sl_08.py`）；执行状态与 Verdict 只在 Run 报告。

> **设计修订（2026-09-30）**：本 case 早期设计假设 `deployment_ids` 缺失类型预校验、非数组输入会抛 `TypeError → 500 internal_error`，并据此把本 case 建为"服务器错误信封"案例。当前实现 [`registry._capability_intersection`](../../../../src/management/registry.py) 已在迭代前显式校验 `deployment_ids` 必须是字符串数组（`registry.py:300`），非数组输入返回 **400 `invalid_request`（param=`deployment_ids`）**，500 路径不再存在。本 case 已按**当前 code 行为（400）**为 Oracle 修订 §1/§3/§4/§5/§7：验证非法类型输入的 400 类型校验契约与零副作用，不再断言 500，也不再登记已关闭的"类型未预校验"缺陷。
