# ADM-DEPL-04 — 更新 deployment

- **Case ID**：`ADM-DEPL-04`（与 §3.2 权威清单一致；本文件名 `adm-depl-04.md`，唯一对应）。
- **标题**：`PATCH /v1/deployments/{id}` 携带正确 `If-Match` 更新 deployment：HTTP 200 + 字段生效 + `version`/`ETag` 推进；`provider_id` 保持不变。
- **目的（被测契约）**：验证 Management Deployment CRUD 的**乐观并发更新契约**。被测端点/规则：`PATCH /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateDeployment`，`security=AdminBearerAuth`），请求体 `DeploymentPatch`（`minProperties:1`、`additionalProperties:false`，可含 `name/provider_id/backend_model/capabilities/enabled`）；`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；成功 `200` + 新 `DeploymentView` + 响应头 `ETag: "<id>.v<N+1>"`（`version` 单调 +1，[`registry.update_deployment`](../../../../src/management/registry.py)）；失败 400 `invalid_request` / 404 `not_found` / 409 `resource_conflict` / 412 `version_conflict`。设计验证项 `VRC-MGMT-002`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明缺/过期 `If-Match` 的 412（ADM-PROV-06/07 同机制；本 case 走正确 ETag 路径）、不证明删除（ADM-DEPL-05）、不证明 capabilities 校验的 400（ADM-DEPL-06/07）、不证明 `provider_id` PATCH 的负向（ADM-DEPL-09）；本 case 更新 `name`/`enabled` 两个标量，不改 `provider_id`、不触上游。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**TS-003**：`prov_b.endpoint` 必须是 LAN IP 上的 fake provider，**禁止 `127.0.0.1` 作为被测服务的上游 endpoint**。
- **输入与构造**：先创建独立 deployment（避免改动基线 `depl_b`），再 PATCH：
  ```http
  POST /v1/deployments HTTP/1.1    # 创建：provider_id=prov_b, capabilities 12 键, enabled=true
  PATCH /v1/deployments/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v1"
  Content-Type: application/json
  ```
  ```json
  {"name": "Updated Deployment Name", "enabled": false}
  ```
  构造点：`If-Match` **必须取自创建响应（或 GET）的 `ETag`**（绝不硬编码版本）；PATCH 体键集 ⊆ `{name,provider_id,backend_model,capabilities,enabled}` 且非空；不提交 `provider_id`；不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/deployments", json=<DeploymentWrite, provider_id="prov_b">)`；断言 `201`，记 `rid`、`original_version`、`original_etag = create.headers["ETag"]`、`original_provider_id`。
  3. `patch = admin_client_b.patch(f"/v1/deployments/{rid}", json={"name":"Updated Deployment Name","enabled":False}, headers={"If-Match": original_etag})`。
  4. 断言 `patch.status_code == 200`；`updated = patch.json()`：`updated["name"]=="Updated Deployment Name"`、`updated["enabled"] is False`、`updated["version"] > original_version`（期望 `+1`）、`updated["provider_id"] == original_provider_id`（**未变**）。
  5. 断言 `patch.headers` 含 `ETag`，等于 `f'"{rid}.v{updated["version"]}"'`；`GET /v1/deployments/{rid}` 断言新值持久化且 ETag 一致。
  6. （teardown，`finally` 内）以最新 `GET` 的 `ETag` `DELETE` 本 deployment，断言 `204`；随后 `GET` 断言 `404`。
- **重点关注步骤**：① **CAS 语义**——`If-Match` 必须与当前版本严格相等，用**真实读取的 ETag**（绝不硬编码 `v1`）；② **版本推进**——`version` 必 +1 且新 ETag 与之一致，旧 ETag 立即失效；③ **字段生效、未提交字段保持**——`name`/`enabled` 回显新值，`provider_id`/`backend_model`/`capabilities` 保持原值；④ **412 后必须重取**——若因并发得 412，不得覆盖式重发旧 ETag，须重新 `GET` 取新 ETag；⑤ **teardown 用最新 ETag**——更新后版本已推进；⑥ **拒绝零副作用**——若 400/404/409，确认 deployment 未被改。
  > **契约 vs 实现偏差（登记，不在本 case 失败面）**：§3.2 `ADM-DEPL-04` 标注"`provider_id` 不可改"。实际 [`registry.update_deployment`](../../../../src/management/registry.py) 允许 PATCH `provider_id`，只要新值指向**已存在** provider（`require(SELECT 1 FROM providers ...)`）；仅"换成不存在 provider"才 400（ADM-DEPL-09 覆盖该负向）。即"不可改"当前**未被真正强制**：把 `provider_id` 改为另一个既存 provider 会成功。本 case 只 PATCH `name`/`enabled` 并断言 `provider_id` 不变；偏差在运行报告登记。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentPatch`/`DeploymentView` + ETag/CAS 规则。
  - 创建：`201`，ETag `"<rid>.v1"`。
  - PATCH：`200`；`name`/`enabled` 为更新值；`version == original+1`；`provider_id` 不变；响应头 `ETag == "<rid>.v<original+1>"`。
  - 回读：新值持久化、ETag 一致。
  - teardown：`DELETE`（最新 If-Match）→ `204`；随后 `GET` → `404`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `200` + 字段生效 + `version` 推进 + `provider_id` 不变 + 新 ETag 一致；回读一致；teardown `204` 且随后 `404`。
  - **FAIL**：任一断言不符（status 错、版本未推进、ETag 不符、字段未生效、`provider_id` 被改、teardown 未删净）。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：硬编码/伪造 ETag 绕过真实读取，或用 `127.0.0.1` 作上游 endpoint——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建/PATCH/回读/teardown 的请求与原始响应（含 `If-Match` 与 `ETag` 头）。
- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 创建的 deployment（用最新 ETag；412 则重取）；不改基线 `depl_b`/`prov_b`/7 tier、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[§4.7](../llmtier-api-test-specification.md)）。离开前确认无本次创建物残留。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；基线 provider `prov_b`；`DeploymentPatch`/`DeploymentView` 机器契约；ETag/CAS 规则 `registry.update_deployment`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_depl_04.py`](../../../../tests/system/api_test_v03/at_adm_depl_04.py)。**不依赖**其它 Case（自建被测 deployment）；与 ADM-DEPL-09（`provider_id` PATCH 负向）互补但各自独立执行。
