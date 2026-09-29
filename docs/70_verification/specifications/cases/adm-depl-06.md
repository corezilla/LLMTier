# ADM-DEPL-06 — capabilities 缺字段

- **Case ID**：`ADM-DEPL-06`（与 §3.2 权威清单一致；本文件名 `adm-depl-06.md`，唯一对应）。
- **标题**：`POST /v1/deployments` 的 `capabilities` 缺少必填键：HTTP 400 + `error.code=="invalid_request"`、`param=="capabilities"`，统一错误信封，无副作用。
- **目的（被测契约）**：验证 Deployment **capabilities 完整性的负向契约**。被测端点/规则：`POST /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createDeployment`），请求体 `DeploymentWrite.capabilities` 是 `ModelCapabilities`（`additionalProperties:false`、`required` 恰 12 键）；[`registry._validate_capabilities`](../../../../src/management/registry.py) 断言 `set(value) == CAPABILITY_KEYS`，否则 `raise ApiError(400,"invalid_request",…,"capabilities")`。成功契约与 201 见 ADM-DEPL-02；本 case 走缺字段负向。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明创建成功（ADM-DEPL-02）、不证明未知字段（ADM-DEPL-07）、不证明 provider 引用（ADM-DEPL-08）、不证明 `provider_id` PATCH（ADM-DEPL-09）；本 case 为纯负向，**不得**创建出任何 deployment。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。`prov_b` 必须存在（负向只需触达 capabilities 校验即可）。
- **输入与构造**：`capabilities` 少一个键（缺 `embedding_space_id`/`embedding_dimensions`/`embedding_max_batch_inputs`/`embedding_max_input_tokens`）的创建请求：
  ```http
  POST /v1/deployments HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Bad Deployment",
    "provider_id": "prov_b",
    "backend_model": "test-model",
    "capabilities": {
      "responses": true, "embeddings": false, "tools": false, "structured_outputs": false,
      "input_modalities": ["text"], "output_modalities": ["text"],
      "context_window": 4096, "max_output_tokens": 2048
    },
    "enabled": true
  }
  ```
  构造点：`capabilities` 仅 8 键（缺 4 个 embedding 键），其余 body 键集合法；`provider_id` 指向既存 `prov_b`；不注入故障。**顺序**：`create_deployment` 先 `require(set(body)==required)`、再 `_validate_capabilities`，故本输入命中 capabilities 校验。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `before = admin_client_b.get("/v1/deployments")`；记初始 deployment id 集合。**注**：该列表 GET（[`admin.page()`](../../../../src/management/admin.py)）会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`）。
  3. `resp = admin_client_b.post("/v1/deployments", json=<上表 body>)`；记录 status、body。
  4. 断言 `resp.status_code == 400`。
  5. `err = resp.json()["error"]`：键集恰为 `{message,type,code,param,retryable}`；`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["param"] == "capabilities"`、`err["retryable"] is False`。
  6. 对 deployment 资源零副作用：`after = GET /v1/deployments`；断言 id 集合与 `before` 相同（未创建 `"Bad Deployment"`）。**注**：第 2/6 步列表 GET 各自会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照（`admin.page()`），属服务端读路径副作用、非 deployment 资源，报告须登记，**不得笼统声称"零写入"**；"no new rows" 检查只针对 `deployments` 表，不得据 `query_snapshots` 新增判 FAIL。
- **重点关注步骤**：① **400 + code + param 三断言**——不能只断言 400；`param=="capabilities"` 定位字段；② **对 deployment 资源拒绝零副作用**——校验在 INSERT 之前（`create_deployment` 先校验后落库），第 6 步证明无新 deployment 行；但第 2/6 步列表 GET 会在 `query_snapshots` 落 10 分钟 TTL 分页快照（`admin.page()`），须登记该写入、**不得声称"零写入"**；③ **信封 identity**——恰 5 键、`type="request_error"`（400<500）、`retryable=false`；④ **不得误判**——若因 provider 不存在也 400，需确认根因是 capabilities（本输入 provider 存在，故唯一失败面是 capabilities）；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ModelCapabilities` 必填 12 键 + `ErrorEnvelope`/`ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
   - body：`{"error":{"code":"invalid_request","type":"request_error","param":"capabilities","retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
   - 无 deployment 资源变化（deployment 集合不变；第 2/6 步列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` 且 `code=="invalid_request"`、`param=="capabilities"`、信封 5 键、`type=="request_error"`，且无新 deployment（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 400（如 201 缺键仍创建）、code/param 不符、信封缺/多键，或产生 deployment 资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试（断言逻辑/契约语义问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 400 或替代路径冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：POST 请求/原始响应、请求前后 deployment 列表（证明零副作用）。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_depl_06.py`](../../../../tests/system/api_test_v03/at_adm_depl_06.py) 只断言 `400` + `code=="invalid_request"`，**未断言 `param=="capabilities"` 与零副作用**；按本设计需补齐。
- **清理与复位**：**无需 teardown**——负向拒绝对 deployment 资源无写副作用。第/各步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。 退出前确认 deployment 集合未变、基线 `depl_b` 仍在、无未清空注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；基线 provider `prov_b`；`ModelCapabilities`/`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` `_validate_capabilities`/`create_deployment`；自动化入口 [`at_adm_depl_06.py`](../../../../tests/system/api_test_v03/at_adm_depl_06.py)。**不依赖**其它 Case；与 ADM-DEPL-07（未知字段）互补但各自独立执行。
