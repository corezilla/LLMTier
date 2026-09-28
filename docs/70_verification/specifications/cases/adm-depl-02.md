# ADM-DEPL-02 — 创建 deployment

- **Case ID**：`ADM-DEPL-02`（与 §3.2 权威清单一致；本文件名 `adm-depl-02.md`，唯一对应）。
- **标题**：`POST /v1/deployments` 创建 deployment：HTTP 201 + 自动 id + 完整 `DeploymentView` + `ETag`；`capabilities` 恰为 12 键全集。
- **目的（被测契约）**：验证 Management Deployment CRUD 的**创建契约**。被测端点/规则：`POST /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createDeployment`，`security=AdminBearerAuth`），请求体 `DeploymentWrite`（键集恰 `{name,provider_id,backend_model,capabilities,enabled}`，`additionalProperties:false`）；成功 `201` + 自动生成 id（`_id("deployment")`）+ `DeploymentView`（`id,name,provider_id,backend_model,capabilities,enabled,health,version`）+ 响应头 `ETag: "<id>.v1"`；`capabilities` 必须键集恰为 `CAPABILITY_KEYS`（12 键，[`registry._validate_capabilities`](../../../../src/management/registry.py)）；`provider_id` 必须已存在，否则 400 `invalid_request`（`param="provider_id"`）。失败：400 `invalid_request` / 409 `resource_conflict`（重名）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`。**不证明什么**：不证明列表/详情（ADM-DEPL-01/03）、不证明更新/删除（ADM-DEPL-04/05）、不证明 capabilities 缺/多字段的 400（ADM-DEPL-06/07）、不证明 provider 引用不存在（ADM-DEPL-08）、不证明 `provider_id` PATCH 行为（ADM-DEPL-09）；本 case 只创建、不触上游。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite，同机第二个进程；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动且 `GET /healthz` 200；`_BASELINE_SETTINGS` fixture 注入 **1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier**；`llmtier_b` 对 `depl_b` 的 probe 返回 `healthy`；`prov_b.endpoint` 必须是本机 LAN IP 上的 fake provider（TS-003），**禁止 `127.0.0.1` 作为被测服务的上游 endpoint**。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b`、`admin_client_b`（`Bearer dev-admin`）。初始状态 = 1 provider（`prov_b`）/ 1 deployment（`depl_b`）/ 7 fixed tier。
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
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `resp = admin_client_b.post("/v1/deployments", json=<上表 body>)`；记录 status、headers、body。
  3. 断言 `resp.status_code == 201`。
  4. `data = resp.json()`：断言 `data["name"]/["provider_id"]/["backend_model"]/["enabled"]` 与请求一致；`data["capabilities"] == 请求 capabilities`（12 键等值）；`"id" in data` 且为字符串；`"version" in data`（新建期望 `1`）；`data["health"]` ∈ `{unknown,healthy,degraded,unhealthy}`。
  5. 断言响应头含 `ETag`，且等于 `f'"{data["id"]}.v{data["version"]}"'`（含双引号）；`GET /v1/deployments/{id}` 断言 `200` 且 `ETag` 与创建一致。
  6. （teardown，`finally` 内）以创建响应的 `ETag` `DELETE /v1/deployments/{id}`，断言 `204`；随后 `GET` 断言 `404`。
- **重点关注步骤**：① **201 + 自动 id**——不是 200，id 由服务端生成（`deployment_<hex>`）；② **`capabilities` 12 键等值**——`DeploymentWrite` 要求全集，缺/多即 400（由 ADM-DEPL-06/07 覆盖），创建成功必须原样回显；③ **ETag 格式**——`"<id>.v<N>"` **含双引号**，新建为 `.v1`，且 `GET` 回读一致；④ **引用既存 provider**——`prov_b` 必须存在（§2.1 附加）；未知 provider 属 ADM-DEPL-08；⑤ **零污染**——创建后必须 teardown 删除本次创建物，不删除基线 `depl_b`；⑥ **不触上游**——创建只写注册表，不调 `prov_b.endpoint`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentWrite`/`DeploymentView` + ETag 格式（[测试设计 §4.10](../llmtier-api-test-specification.md)）。
  - HTTP：`201`；`Content-Type: application/json`；响应头 `ETag == "<id>.v1"`。
  - body：`DeploymentView` 8 键；`name/provider_id/backend_model/enabled/capabilities` 与请求一致；`version==1`；`id` 非空。
  - 回读：`GET /v1/deployments/{id}` → `200`，`ETag` 一致。
  - teardown：`DELETE`（If-Match）→ `204`；随后 `GET` → `404`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`201` + body 字段等值 + `capabilities` 12 键 + `ETag` 符合 `"<id>.v1"` + 回读一致 + teardown `204` 且随后 `404`。
  - **FAIL**：status 非 201、字段/`capabilities`/ETag 不符、未自动生成 id，或 teardown 未删净。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 当上游 endpoint 或伪造 201——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存创建请求/原始响应（含 `ETag`，脱敏后）、回读、teardown 的 `DELETE` 与随后 `GET`、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`（如 `2026-09-28/B-api`），落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_depl_02.py`](../../../../tests/system/api_test_v03/at_adm_depl_02.py) 创建后仅 `GET` 回读，**未 teardown 删除**本次创建物（依赖整班 B 类临时实例销毁兜底）；按本设计需在 `finally` 中删除后方为完整。
- **清理与复位**：**必须 teardown（`finally` 强制）**——`DELETE /v1/deployments/{id}`（用创建响应的 `If-Match`）删除本 case 创建物，随后 `GET` 校验 `404`；不删除基线 `depl_b`（其被 7 tier 引用，删除会 409 `resource_in_use`）、不改 `prov_b`/7 tier、不写注入。B 类整班结束由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `rm -rf` 临时目录销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。离开前确认无本次创建物残留。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；基线 provider `prov_b`（§2.1 附加）；`DeploymentWrite`/`DeploymentView` 机器契约；实现 `src/management/registry.py` `create_deployment`/`_etag`；自动化入口 [`at_adm_depl_02.py`](../../../../tests/system/api_test_v03/at_adm_depl_02.py)。**不依赖**其它 Case（自建被测 deployment）；与 ADM-DEPL-04/05 共享创建前置但各自独立执行。
