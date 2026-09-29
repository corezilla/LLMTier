<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-SL-02B — 创建已存在 fixed tier

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-SL-02B` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-test-design` |
| Template Version | `2.3.0` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/adm-sl-02b.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-SL-02B` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `negative` / `P1`
- 方案清单登记：`ADM-SL-02b`（与 §3.2 权威清单一致；本文件名 `adm-sl-02b.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/service-levels` 用已存在的固定 Tier `id`（`Senior`）创建：HTTP 409 `resource_conflict`。
- 明确不测什么 / 失败含义：不证明 非白名单 id 的 400（ADM-SL-02）、不证明成员能力/向量空间校验（ADM-SL-06/07）、不证明 PATCH/DELETE（ADM-SL-04/05）。本 case **只**锁 409 `resource_conflict`。

**目的（被测契约）**：验证固定 Tier 的**唯一性冲突契约**。被测端点/规则：`POST /v1/service-levels`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createServiceLevel`）；[`registry.create_service_level`](../../../../src/management/registry.py) 通过白名单与能力校验后 `INSERT INTO service_levels`，主键冲突时捕获 `UNIQUE` 并抛 `ApiError(409, "resource_conflict", "Service level already exists")`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-CONFLICT` → wire `code=resource_conflict`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明非白名单 id 的 400（ADM-SL-02）、不证明成员能力/向量空间校验（ADM-SL-06/07）、不证明 PATCH/DELETE（ADM-SL-04/05）。本 case **只**锁 409 `resource_conflict`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=`Senior` 已由 bootstrap 预创建（`_baseline_settings` 的 7 tier 各含 `["depl_b"]`、`enabled=true`）。

## 3. 输入构造

- **输入与构造**：固定请求：
  ```http
  POST /v1/service-levels HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"id": "Senior", "deployment_ids": ["depl_b"], "enabled": true}
  ```
  构造点：`id="Senior"` 是合法固定 Tier 且已存在；`deployment_ids=["depl_b"]` 使 `_capability_intersection` 得 12 键、`_validate_level("Senior", …)` 通过（`depl_b.responses=True`），从而失败点落在**唯一性 INSERT**而非 400/409 能力校验。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`；`GET /v1/service-levels/Senior` 断言 200（存在）。
  2. `resp = admin_client_b.post("/v1/service-levels", json={"id":"Senior","deployment_ids":["depl_b"],"enabled":True})`。
  3. 断言 `resp.status_code == 409`。
  4. `err = resp.json()["error"]`：断言 `err["code"]=="resource_conflict"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels/Senior` 仍 200，`version` 与步骤 1 相同（未被本次 POST 改动）。

**重点关注步骤**：① **区分 400 vs 409**——`Senior` 是合法白名单 id、能力交集合法，因此必须走唯一性冲突 409；若得 400 说明在更早的校验被拦（输入构造错误）；② **失败点在写库**——本 case 的 409 由 `INSERT` 的 `UNIQUE` 触发（`registry.py` 异常分支），与 ADM-SL-02 的 dispatch 前 400 不同；③ **零副作用**——已存在的 `Senior` 行及其 `version` 不得因冲突 POST 改变；④ **审计**——失败经 `mutate` 记 `result="failed"` 审计行、不创建资源；⑤ **错误信封 identity**——恰 5 键、`type=request_error`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 固定 Tier 唯一性约束。
  - HTTP：`409`；body `{"error":{"message":"Service level already exists","type":"request_error","code":"resource_conflict","param":null,"retryable":false}}`。
  - 资源：`GET /v1/service-levels/Senior` 200 且 `version` 不变。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`409` + `code=="resource_conflict"` + `type=="request_error"`，且 `Senior` 未被改动。
  - **FAIL**：status 非 409、`code` 错、或 `Senior` 被修改/新增第二条。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实唯一性约束——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——冲突未改库。退出前确认 7 fixed tier 与其 `version` 未被本次 POST 改动、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存POST 请求/原始 409 响应（脱敏后）、POST 前后 `GET /v1/service-levels/Senior`（含 ETag/version）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ServiceLevelWrite` 机器契约；`registry.create_service_level` 的 UNIQUE 分支；错误目录 `ERR-CONFLICT`。自动化入口 [`at_adm_sl_02b.py`](../../../../tests/system/api_test_v03/at_adm_sl_02b.py)。**不依赖**其它 Case；与 ADM-SL-02（非白名单→400）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
