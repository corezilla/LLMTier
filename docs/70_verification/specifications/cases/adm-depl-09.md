# ADM-DEPL-09 — provider_id 改为不存在 provider

- **Case ID**：`ADM-DEPL-09`（与 §3.2 权威清单一致；本文件名 `adm-depl-09.md`，唯一对应）。
- **标题**：`PATCH /v1/deployments/{id}` 试图把 `provider_id` 改为不存在的 provider：HTTP 400 + `error.code=="invalid_request"`、`param=="provider_id"`，统一错误信封，`provider_id`/`version` 不变。
- **目的（被测契约）**：验证 Deployment **`provider_id` 变更的引用负向契约**。被测端点/规则：`PATCH /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateDeployment`，`security=AdminBearerAuth`），`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；[`registry.update_deployment`](../../../../src/management/registry.py) 在 `If-Match` 校验通过后 `require(SELECT 1 FROM providers WHERE id=values["provider_id"], 400, "invalid_request", "Unknown provider", "provider_id")`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-REQ-VALIDATION`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`。**不证明什么**：不证明正常更新（ADM-DEPL-04）、不证明缺/过期 `If-Match` 的 412（本 case 用正确 ETag）、不证明删除（ADM-DEPL-05）、不证明 provider CRUD（ADM-PROV-*）；本 case 为纯负向，**不得**改动 deployment。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**被测对象**：基线 `depl_b`（provider_id 原值 `prov_b`），本 case 只 PATCH 一个非法 `provider_id`，不改动 baseline。
- **输入与构造**：先 `GET` 基线 deployment 取 `ETag`，再 PATCH 非法引用：
  ```http
  GET /v1/deployments/depl_b HTTP/1.1
  Authorization: Bearer dev-admin

  PATCH /v1/deployments/depl_b HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<depl_b>.v<N>"
  Content-Type: application/json
  ```
  ```json
  {"provider_id": "nonexistent_provider"}
  ```
  构造点：`If-Match` **必须取自先前的 `GET /v1/deployments/depl_b`**（绝不硬编码；若用错误 ETag 会先得 412 而非 400，本 case 须避免）；PATCH 体只含 `provider_id`（键集 ⊆ 允许集且非空）；目标值 `nonexistent_provider` 不在注册表；不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/deployments/depl_b")`；断言 `200`，记 `etag = get.headers["ETag"]`、`before = get.json()`（`provider_id`/`version`）。
  3. `resp = admin_client_b.patch("/v1/deployments/depl_b", json={"provider_id":"nonexistent_provider"}, headers={"If-Match": etag})`；记录 status、body。
  4. 断言 `resp.status_code == 400`。
  5. `err = resp.json()["error"]`：键集恰 5 键；`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["param"] == "provider_id"`、`err["retryable"] is False`。
  6. 零副作用：`after = GET /v1/deployments/depl_b`；断言 `after.json()["provider_id"] == before["provider_id"]`（仍 `prov_b`）、`after.json()["version"] == before["version"]`（未 +1），且 `ETag` 与第 2 步一致。
- **重点关注步骤**：① **先 GET 再 PATCH**——`If-Match` 必须真实有效，否则会先命中 412 而测不到本 case 的 400（`update_deployment` 的 `If-Match` 校验先于 provider 校验）；② **400 + code + param 三断言**——`param=="provider_id"` 定位字段，且**不是 404**；③ **拒绝零副作用**——校验在 `UPDATE` 之前，第 6 步证明 `provider_id`/`version`/ETag 均未变；④ **只改一个字段**——PATCH 体仅 `provider_id`，避免与 capabilities 重算路径混淆；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable。
  > **契约 vs 实现偏差（登记，不在本 case 失败面）**：§3.2 `ADM-DEPL-09` 标题为"`provider_id` 不可 PATCH"，暗示 `provider_id` 为不可变字段。实际 [`registry.update_deployment`](../../../../src/management/registry.py) **允许** PATCH `provider_id`，只要新值指向**已存在** provider（仅拒绝未知 provider，即本 case 的 400）；把 `provider_id` 改为另一个既存 provider 会成功并推进 `version`。即"不可 PATCH"当前**未被真正强制**，仅"未知引用被拒"被实现。本 case 以受测实现为准断言未知引用的 400；"不可变"语义缺口在运行报告登记。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentPatch` provider 引用约束 + `ErrorEnvelope`/`ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"code":"invalid_request","type":"request_error","param":"provider_id","retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
  - 无资源变化：`provider_id` 仍 `prov_b`、`version`/`ETag` 不变。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` 且 `code=="invalid_request"`、`param=="provider_id"`、信封 5 键、`type=="request_error"`，且 `depl_b` 的 `provider_id`/`version`/ETag 未变。
  - **FAIL**：status 非 400（如 200 成功改 provider_id、404、412）、code/param 不符、信封缺/多键，或 baseline 被改动。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：硬编码/伪造 `If-Match`（绕过真实 GET），或伪造 400——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`GET`（取 ETag）、PATCH 请求/原始响应、PATCH 后 `GET`（证明零副作用）。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_depl_09.py`](../../../../tests/system/api_test_v03/at_adm_depl_09.py) 断言 `400` + `code=="invalid_request"`，但**未断言 `param=="provider_id"`，也未回读证明 `provider_id`/`version`/ETag 未变**；按本设计需补齐零副作用断言。
- **清理与复位**：**无需 teardown**——负向拒绝无写副作用，基线 `depl_b` 保持原值。退出前确认 `depl_b` 的 `provider_id=="prov_b"`、`version`/ETag 与执行前一致、7 tier 仍在、无未清空注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；基线 provider `prov_b` / deployment `depl_b`；`DeploymentPatch`/`ErrorEnvelope` 机器契约；ETag/CAS 规则 `registry.update_deployment`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_depl_09.py`](../../../../tests/system/api_test_v03/at_adm_depl_09.py)。**不依赖**其它 Case；与 ADM-DEPL-04（正常 PATCH）互补但各自独立执行。
