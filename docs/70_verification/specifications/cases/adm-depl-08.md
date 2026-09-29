# ADM-DEPL-08 — 引用不存在 provider

- **Case ID**：`ADM-DEPL-08`（与 §3.2 权威清单一致；本文件名 `adm-depl-08.md`，唯一对应）。
- **标题**：`POST /v1/deployments` 引用不存在的 `provider_id`：HTTP 400 + `error.code=="invalid_request"`、`param=="provider_id"`，统一错误信封，无副作用。
- **目的（被测契约）**：验证 Deployment **provider 引用完整性的负向契约**。被测端点/规则：`POST /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createDeployment`），`DeploymentWrite.provider_id` 必须指向已存在 provider；[`registry.create_deployment`](../../../../src/management/registry.py) 在 capabilities 校验之后 `require(SELECT 1 FROM providers WHERE id=? is not None, 400, "invalid_request", "Unknown provider", "provider_id")`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明创建成功（ADM-DEPL-02）、不证明 capabilities 校验（ADM-DEPL-06/07）、不证明 `provider_id` PATCH（ADM-DEPL-09）、不证明 provider CRUD（ADM-PROV-*）；本 case 为纯负向，**不得**创建出任何 deployment。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。
- **输入与构造**：`capabilities` 合法但 `provider_id` 指向不存在 provider：
  ```http
  POST /v1/deployments HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Deployment Bad Provider",
    "provider_id": "nonexistent_provider",
    "backend_model": "test-model",
    "capabilities": {
      "responses": true, "embeddings": false, "tools": false, "structured_outputs": false,
      "input_modalities": ["text"], "output_modalities": ["text"],
      "context_window": 4096, "max_output_tokens": 2048,
      "embedding_space_id": null, "embedding_dimensions": null,
      "embedding_max_batch_inputs": null, "embedding_max_input_tokens": null
    },
    "enabled": true
  }
  ```
  构造点：`provider_id="nonexistent_provider"`（不在基线）；`capabilities` 为合法 12 键（使唯一失败面是 provider 引用）；不注入故障。**顺序**：`create_deployment` 先校验 body 键集与 capabilities，**再**校验 provider 存在性，故本输入以 provider 引用失败。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `before = admin_client_b.get("/v1/deployments")`；记初始 deployment id 集合。**注**：该列表 GET（[`admin.page()`](../../../../src/management/admin.py)）会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`）。
  3. `resp = admin_client_b.post("/v1/deployments", json=<上表 body>)`；记录 status、body。
  4. 断言 `resp.status_code == 400`。
  5. `err = resp.json()["error"]`：键集恰 5 键；`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["param"] == "provider_id"`、`err["retryable"] is False`。
  6. 对 deployment 资源零副作用：`after = GET /v1/deployments`；断言 id 集合与 `before` 相同（未创建）。**注**：第 2/6 步列表 GET 各自会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照（`admin.page()`），属服务端读路径副作用、非 deployment 资源，报告须登记，**不得笼统声称"零写入"**；"no new rows" 检查只针对 `deployments` 表，不得据 `query_snapshots` 新增判 FAIL。
- **重点关注步骤**：① **400 + code + param 三断言**——`param=="provider_id"` 定位引用字段；② **对 deployment 资源拒绝零副作用**——provider 不存在在 INSERT 前被拒，第 6 步证明无新 deployment 行；但第 2/6 步列表 GET 会在 `query_snapshots` 落 10 分钟 TTL 分页快照（`admin.page()`），须登记该写入、**不得声称"零写入"**；③ **不返回 404**——引用不存在是 **400 `invalid_request`**，不是 404（对比 GET 不存在 deployment 的 404）；④ **capabilities 合法**——构造时确保 capabilities 完整，避免把失败归因混淆；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentWrite` provider 引用约束 + `ErrorEnvelope`/`ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
   - body：`{"error":{"code":"invalid_request","type":"request_error","param":"provider_id","retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
   - 无 deployment 资源变化（第 2/6 步列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` 且 `code=="invalid_request"`、`param=="provider_id"`、信封 5 键、`type=="request_error"`，且无新 deployment（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 400（如 404/201）、code/param 不符、信封缺/多键，或产生 deployment 资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 400 或替代路径冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：POST 请求/原始响应、请求前后 deployment 列表（证明零副作用）。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_depl_08.py`](../../../../tests/system/api_test_v03/at_adm_depl_08.py) 只断言 `400` + `code=="invalid_request"`，**未断言 `param=="provider_id"` 与零副作用**；按本设计需补齐。
- **清理与复位**：**无需 teardown**——负向拒绝对 deployment 资源无写副作用。第/各步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。 退出前确认 deployment 集合未变、基线 `depl_b` 仍在、无未清空注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`DeploymentWrite`/`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` `create_deployment`；自动化入口 [`at_adm_depl_08.py`](../../../../tests/system/api_test_v03/at_adm_depl_08.py)。**不依赖**其它 Case；与 ADM-DEPL-06/07（capabilities 负向）互补但各自独立执行。
