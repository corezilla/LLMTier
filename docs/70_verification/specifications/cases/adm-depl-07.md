# ADM-DEPL-07 — capabilities 未知字段

- **Case ID**：`ADM-DEPL-07`（与 §3.2 权威清单一致；本文件名 `adm-depl-07.md`，唯一对应）。
- **标题**：`POST /v1/deployments` 的 `capabilities` 含未知键：HTTP 400 + `error.code=="invalid_request"`、`param=="capabilities"`，统一错误信封，无副作用。
- **目的（被测契约）**：验证 Deployment **capabilities 键集封闭性的负向契约**。被测端点/规则：`POST /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createDeployment`），`capabilities` 为 `ModelCapabilities`（`additionalProperties:false`）；[`registry._validate_capabilities`](../../../../src/management/registry.py) 断言 `set(value) == CAPABILITY_KEYS`（12 键），多键即 `raise ApiError(400,"invalid_request",…,"capabilities")`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明创建成功（ADM-DEPL-02）、不证明缺字段（ADM-DEPL-06）、不证明 provider 引用（ADM-DEPL-08）、不证明 `provider_id` PATCH（ADM-DEPL-09）；本 case 为纯负向，**不得**创建出任何 deployment。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（实例可启动 + `/healthz` 200；`_BASELINE_SETTINGS` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b`、`admin_client_b`（`Bearer dev-admin`）。
- **输入与构造**：`capabilities` 含 12 个合法键 + 1 个未知键 `unknown_field`：
  ```http
  POST /v1/deployments HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Bad Deployment Unknown Field",
    "provider_id": "prov_b",
    "backend_model": "test-model",
    "capabilities": {
      "responses": true, "embeddings": false, "tools": false, "structured_outputs": false,
      "input_modalities": ["text"], "output_modalities": ["text"],
      "context_window": 4096, "max_output_tokens": 2048,
      "embedding_space_id": null, "embedding_dimensions": null,
      "embedding_max_batch_inputs": null, "embedding_max_input_tokens": null,
      "unknown_field": true
    },
    "enabled": true
  }
  ```
  构造点：`capabilities` 为"合法 12 键 + 1 未知键"（`set` 不等 → 400）；`provider_id` 指向既存 `prov_b`；不注入故障。**顺序**：先 `require(set(body)==required)` 通过，再 `_validate_capabilities` 命中未知键。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `before = admin_client_b.get("/v1/deployments")`；记初始 deployment id 集合。
  3. `resp = admin_client_b.post("/v1/deployments", json=<上表 body>)`；记录 status、body。
  4. 断言 `resp.status_code == 400`。
  5. `err = resp.json()["error"]`：键集恰 5 键；`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["param"] == "capabilities"`、`err["retryable"] is False`。
  6. 零副作用：`after = GET /v1/deployments`；断言 id 集合与 `before` 相同（未创建）。
- **重点关注步骤**：① **400 + code + param 三断言**——`param=="capabilities"` 定位字段；② **拒绝零副作用**——未知键在 INSERT 前被拒，第 6 步证明无新行；③ **信封 identity**——恰 5 键、`type="request_error"`；④ **与缺字段区分**——本 case 是"多键"，ADM-DEPL-06 是"缺键"，两者都必须 400 `invalid_request`，但**不得互相替代**；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ModelCapabilities` 封闭键集 + `ErrorEnvelope`/`ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"code":"invalid_request","type":"request_error","param":"capabilities","retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
  - 无资源变化。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` 且 `code=="invalid_request"`、`param=="capabilities"`、信封 5 键、`type=="request_error"`，且无新 deployment。
  - **FAIL**：status 非 400（如 201 未知键仍创建）、code/param 不符、信封缺/多键，或产生副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 400 或替代路径冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 POST 请求/原始响应（脱敏后）、请求前后 deployment 列表、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_depl_07.py`](../../../../tests/system/api_test_v03/at_adm_depl_07.py) 只断言 `400` + `code=="invalid_request"`，**未断言 `param=="capabilities"` 与零副作用**；按本设计需补齐。
- **清理与复位**：**无需 teardown**——负向拒绝无写副作用。退出前确认 deployment 集合未变、基线 `depl_b` 仍在、无未清空注入；B 类整班结束由 fixture `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；基线 provider `prov_b`；`ModelCapabilities`/`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` `_validate_capabilities`/`create_deployment`；自动化入口 [`at_adm_depl_07.py`](../../../../tests/system/api_test_v03/at_adm_depl_07.py)。**不依赖**其它 Case；与 ADM-DEPL-06（缺字段）互补但各自独立执行。
