<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-SL-04B — 更新非法字段

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-SL-04B` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/adm-sl-04b.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-SL-04B`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-SL-04B` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-SL-04B` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `negative` / `P1`
- 方案清单登记：`ADM-SL-04b`（与 §3.2 权威清单一致；本文件名 `adm-sl-04b.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/service-levels/{id}` 提交未知字段：HTTP 400 `invalid_request`（"Unknown or empty …"）。
- 明确不测什么 / 失败含义：不证明 合法 PATCH 成功（ADM-SL-04）、不证明缺/过期 `If-Match` 412（SL 412 未单独构 case）、不证明成员能力/向量空间冲突（ADM-SL-06/07）。

**目的（被测契约）**：验证 Service Level PATCH 的**字段白名单校验**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，body `ServiceLevelPatch.additionalProperties:false`）；[`registry.update_service_level`](../../../../src/management/registry.py) 首行做 PATCH 字段白名单校验（仅接受 `deployment_ids`/`enabled`，否则 400 `invalid_request`，[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明合法 PATCH 成功（ADM-SL-04）、不证明缺/过期 `If-Match` 412（SL 412 未单独构 case）、不证明成员能力/向量空间冲突（ADM-SL-06/07）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=`Worker` 存在。

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
  {"unknown_field": "value"}
  ```
  构造点：body 键 `unknown_field` 不在 `{deployment_ids,enabled}` 白名单内，且 body 非空；`If-Match` 用真实 ETag（使失败点确为**字段校验**而非 412）。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Worker")`；断言 200；记 `etag = get.headers["ETag"]`、`version_before = body["version"]`。
  3. `resp = admin_client_b.patch("/v1/service-levels/Worker", json={"unknown_field":"value"}, headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`"Unknown or empty" in err["message"]`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels/Worker` 断言 `version == version_before`（字段校验在 `txn` 之前，未改库）。

**重点关注步骤**：① **拒绝位置**——`require` 在 `with txn` 之前，未知字段请求**不得**改写 `Worker`（`version` 不变）；② **400 而非 412**——必须用真实有效 ETag 以隔离字段校验；若得 412 说明输入构造错误；③ **错误信封 identity**——恰 5 键，`type=request_error`，`code=invalid_request`；④ **param 语义**——该 `require` 未传 `param`，故 `param==null`（不要错误期望 `"unknown_field"`）；⑤ **审计**——失败经 `mutate` 记 `result="failed"` 审计行，非资源修改。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelPatch.additionalProperties:false` + `ErrorEnvelope`。
  - HTTP：`400`；body `{"error":{"message":"Unknown or empty service level patch","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 资源：`Worker.version` 不变。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `"Unknown or empty" in message`，且 `Worker.version` 未变。
  - **FAIL**：status 非 400、`code`/message 错、`version` 被推进。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或注入未命中——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——校验失败未改库。退出前确认 `Worker.version` 与 `enabled` 保持原值、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存GET/PATCH 请求与原始 400 响应（脱敏后）、PATCH 后 `GET` 的 `version`、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ServiceLevelPatch` 机器契约；`registry.update_service_level` 的白名单 `require`。自动化入口 [`at_adm_sl_04b.py`](../../../../tests/system/api_test_v03/at_adm_sl_04b.py)。**不依赖**其它 Case；与 ADM-SL-04（合法 PATCH）互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
