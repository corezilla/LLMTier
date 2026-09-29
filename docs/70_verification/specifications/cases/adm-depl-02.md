<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-DEPL-02 — 创建 deployment

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-DEPL-02` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-depl-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-DEPL-02` / 系统设计 §8 Deployment CRUD 接口（/v1/deployments） / `VRC-MGMT-001` / `normal` / `P0`
- 方案清单登记：`ADM-DEPL-02`（与 §3.2 权威清单一致；本文件名 `adm-depl-02.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/deployments` 创建 deployment：HTTP 201 + 自动 id + 完整 `DeploymentView` + `ETag`；`capabilities` 恰为 12 键全集。
- 明确不测什么 / 失败含义：不证明 列表/详情（ADM-DEPL-01/03）、不证明更新/删除（ADM-DEPL-04/05）、不证明 capabilities 缺/多字段的 400（ADM-DEPL-06/07）、不证明 provider 引用不存在（ADM-DEPL-08）、不证明 `provider_id` PATCH 行为（ADM-DEPL-09）；本 case 只创建、不触上游。

**目的（被测契约）**：验证 Management Deployment CRUD 的**创建契约**。被测端点/规则：`POST /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createDeployment`，`security=AdminBearerAuth`），请求体 `DeploymentWrite`（键集恰 `{name,provider_id,backend_model,capabilities,enabled}`，`additionalProperties:false`）；成功 `201` + 自动生成 id（`_id("deployment")`）+ `DeploymentView`（`id,name,provider_id,backend_model,capabilities,enabled,health,version`）+ 响应头 `ETag: "<id>.v1"`；`capabilities` 必须键集恰为 `CAPABILITY_KEYS`（12 键，[`registry._validate_capabilities`](../../../../src/management/registry.py)）；`provider_id` 必须已存在，否则 400 `invalid_request`（`param="provider_id"`）。失败：400 `invalid_request` / 409 `resource_conflict`（重名）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`。**不证明什么**：不证明列表/详情（ADM-DEPL-01/03）、不证明更新/删除（ADM-DEPL-04/05）、不证明 capabilities 缺/多字段的 400（ADM-DEPL-06/07）、不证明 provider 引用不存在（ADM-DEPL-08）、不证明 `provider_id` PATCH 行为（ADM-DEPL-09）；本 case 只创建、不触上游。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：1 provider（`prov_b`）/ 1 deployment（`depl_b`）/ 7 fixed tier。`llmtier_b` 对 `depl_b` 的 probe 返回 `healthy`；**TS-003**：`prov_b.endpoint` 必须是 LAN IP 上的 fake provider，**禁止 `127.0.0.1` 作为被测服务的上游 endpoint**。

## 3. 输入构造

- **输入与构造**：创建请求（`provider_id` 取基线 `prov_b`，`capabilities` 12 键）：
  ```http
  POST /v1/deployments HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "New Test Deployment",
    "provider_id": "prov_b",
    "backend_model": "test-model-01",
    "capabilities": {
      "responses": true, "embeddings": false, "tools": true, "structured_outputs": false,
      "input_modalities": ["text"], "output_modalities": ["text"],
      "context_window": 8192, "max_output_tokens": 4096,
      "embedding_space_id": null, "embedding_dimensions": null,
      "embedding_max_batch_inputs": null, "embedding_max_input_tokens": null
    },
    "enabled": true
  }
  ```
  构造点：body 键集恰 `{name,provider_id,backend_model,capabilities,enabled}`；`capabilities` 12 键全集；`provider_id` 指向既存 `prov_b`；`name` 唯一可辨识，便于 teardown 与残留核验；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `resp = admin_client_b.post("/v1/deployments", json=<上表 body>)`；记录 status、headers、body。
  3. 断言 `resp.status_code == 201`。
  4. `data = resp.json()`：断言 `data["name"]/["provider_id"]/["backend_model"]/["enabled"]` 与请求一致；`data["capabilities"] == 请求 capabilities`（12 键等值）；`"id" in data` 且为字符串；`"version" in data`（新建期望 `1`）；`data["health"]` ∈ `{unknown,healthy,degraded,unhealthy}`。
  5. 断言响应头含 `ETag`，且等于 `f'"{data["id"]}.v{data["version"]}"'`（含双引号）；`GET /v1/deployments/{id}` 断言 `200` 且 `ETag` 与创建一致。
  6. （teardown，`finally` 内）以创建响应的 `ETag` `DELETE /v1/deployments/{id}`，断言 `204`；随后 `GET` 断言 `404`。

**重点关注步骤**：① **201 + 自动 id**——不是 200，id 由服务端生成（`deployment_<hex>`）；② **`capabilities` 12 键等值**——`DeploymentWrite` 要求全集，缺/多即 400（由 ADM-DEPL-06/07 覆盖），创建成功必须原样回显；③ **ETag 格式**——`"<id>.v<N>"` **含双引号**，新建为 `.v1`，且 `GET` 回读一致；④ **引用既存 provider**——`prov_b` 必须存在（§2.1 附加）；未知 provider 属 ADM-DEPL-08；⑤ **零污染**——创建后必须 teardown 删除本次创建物，不删除基线 `depl_b`；⑥ **不触上游**——创建只写注册表，不调 `prov_b.endpoint`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentWrite`/`DeploymentView` + ETag 格式（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。
  - HTTP：`201`；`Content-Type: application/json`；响应头 `ETag == "<id>.v1"`。
  - body：`DeploymentView` 8 键；`name/provider_id/backend_model/enabled/capabilities` 与请求一致；`version==1`；`id` 非空。
  - 回读：`GET /v1/deployments/{id}` → `200`，`ETag` 一致。
  - teardown：`DELETE`（If-Match）→ `204`；随后 `GET` → `404`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`201` + body 字段等值 + `capabilities` 12 键 + `ETag` 符合 `"<id>.v1"` + 回读一致 + teardown `204` 且随后 `404`。
  - **FAIL**：status 非 201、字段/`capabilities`/ETag 不符、未自动生成 id，或 teardown 未删净。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 当上游 endpoint 或伪造 201——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——`DELETE /v1/deployments/{id}`（用创建响应的 `If-Match`）删除本 case 创建物，随后 `GET` 校验 `404`；不删除基线 `depl_b`（其被 7 tier 引用，删除会 409 `resource_in_use`）、不改 `prov_b`/7 tier、不写注入。B 类整班结束由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `rm -rf` 临时目录销毁（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)/[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。离开前确认无本次创建物残留。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建请求/原始响应（含 `ETag`）、回读、teardown 的 `DELETE` 与随后 `GET`。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_depl_02.py`](../../../../tests/system/api_test_v03/at_adm_depl_02.py) 创建后仅 `GET` 回读，**未 teardown 删除**本次创建物（依赖整班 B 类临时实例销毁兜底）；按本设计需在 `finally` 中删除后方为完整。

- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；基线 provider `prov_b`（§2.1 附加）；`DeploymentWrite`/`DeploymentView` 机器契约；实现 `src/management/registry.py` `create_deployment`/`_etag`；自动化入口 [`at_adm_depl_02.py`](../../../../tests/system/api_test_v03/at_adm_depl_02.py)。**不依赖**其它 Case（自建被测 deployment）；与 ADM-DEPL-04/05 共享创建前置但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
