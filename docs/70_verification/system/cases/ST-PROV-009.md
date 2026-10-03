<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROV-009 — 删除缺 If-Match

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROV-009` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-PROV-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROV-009`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROV-009` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROV-009` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-002` / `negative` / `P1`
- **测试方法（§2.2 方法表行）**：状态机驱动（If-Match/412 串行化）+ 错误猜测 + 反例驱动
- 方案清单登记：`ST-PROV-009`（与 计划 §3 权威清单一致；本文件名 `st-prov-009.md`，唯一对应）。
- 要测什么（责任展开）：`DELETE /v1/providers/{id}` **缺** `If-Match`：HTTP 412 + `error.code=="version_conflict"` + `error.current_version`，资源保留。
- 明确不测什么 / 失败含义：不证明 成功删除（ST-PROV-008）、不证明被引用 409（ST-PROV-010）、不证明 PATCH 的缺 If-Match（ST-PROV-006）、不证明过期 ETag 值（本 case 只发**缺头**）；本 case 只锁定"缺头"这一种前置失败。

**目的（被测契约）**：验证 Management Provider CRUD 的**删除前置校验（缺前置条件）**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；
当 `If-Match` 缺省时，[`registry.delete_provider`](../../../../src/management/registry.py) 的版本比较失败，抛 `ApiError(412, "version_conflict", extra={"current_version": <N>})`；
wire 信封含额外键 `current_version`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-STALE` → `version_conflict`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。
**不证明什么**：不证明成功删除（ST-PROV-008）、不证明被引用 409（ST-PROV-010）、不证明 PATCH 的缺 If-Match（ST-PROV-006）、不证明过期 ETag 值（本 case 只发**缺头**）；
本 case 只锁定"缺头"这一种前置失败。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**TS-003**：请求中的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1`**。

## 3. 输入构造

- **输入与构造**：先创建独立 provider，再发**不带** `If-Match` 的 DELETE：
  ```http
  POST /v1/providers HTTP/1.1   # kind=local, endpoint=LAN, secret_ref=null, enabled=true
  DELETE /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  ```
  构造点：DELETE **完全不携带 `If-Match`**；`rid` 取自创建响应。不注入故障；不构造其它非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={…})`；断言 `201`，记 `rid`、`etag`、`version_before`。
  3. `del_resp = admin_client_b.delete(f"/v1/providers/{rid}")`（**无** `headers`）；断言 `status_code == 412`。
  4. `err = del_resp.json()["error"]`：`err["code"] == "version_conflict"`、`err["type"] == "request_error"`、`err["retryable"] is False`、`err["current_version"] == version_before`。
  5. 交叉核对：`GET /v1/providers/{rid}` 断言 `200`（**资源被保留**）、`version`/ETag 未变。
  6. （teardown，`finally` 内）以 `GET` 的 ETag `DELETE`，断言 `204`；`GET` 断言 `404`。

**重点关注步骤**：① **412 而非 204**——缺 `If-Match` 的 DELETE 必须被拒，绝不落入删除分支；② **资源保留**——第 5 步 `GET` 必须 200 且 `version` 不变，证明拒绝无副作用；③ **`current_version` 正确**——等于创建后的版本；④ **与 ST-PROV-008 区分**——08 带正确头 204，09 缺头 412；⑤ **teardown 补删**——拒绝后资源仍在，`finally` 必须用正确 ETag 删除，避免 B 类实例残留。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-STALE` + 删除 CAS 规则。
  - HTTP：`412`；`Content-Type: application/json`。
  - body：`{"error":{"code":"version_conflict","type":"request_error","param":null,"retryable":false,"current_version":<version_before>, "message":"<nonempty>"}}`。
  - 资源保留：`GET` 仍 `200`，版本未变。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==412` 且 `error.code=="version_conflict"` 且 `error.current_version==version_before`、`type=="request_error"`、`retryable is False`；资源保留；teardown 成功。
  - **FAIL**：status 非 412（如 204 误删）、`code` 不符、缺 `current_version`、或资源被删。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造 412 或以带正确头的 DELETE 冒充缺头场景——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——拒绝后资源仍在，须用正确 ETag 删除本 case 创建的 provider；不改 `prov_b`/`depl_b`、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见计划 §7/§10；失败现场不截断。**本 case 额外证据**：创建/DELETE（证明**无** `If-Match`）/回读/teardown 的请求与响应、`current_version`。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`ErrorEnvelope` 机器契约；CAS/ETag 规则 `registry.delete_provider`/`_etag`；机制 `T-CFG-CAS`；错误目录 `ERR-STALE`；自动化入口 [`ST-PROV-009.py`](../../../../tests/system/cases/ST-PROV-009.py)。**不依赖**其它 Case；与 ST-PROV-008/10 互补但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
