# ADM-SL-07 — 冻结向量空间冲突

- **Case ID**：`ADM-SL-07`（与 §3.2 权威清单一致；本文件名 `adm-sl-07.md`，唯一对应）。
- **标题**：`PATCH /v1/service-levels/Embedding-v1` 绑定非冻结向量空间的 embedding deployment：HTTP 409 `embedding_space_conflict`。
- **目的（被测契约）**：验证 `Embedding-v1` 的**冻结 BGE-M3 向量空间契约**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`）；[`registry._validate_level`](../../../../src/management/registry.py) 对 `level_id=="Embedding-v1"` 要求 `embedding_space_id=="bge-m3-dense-1024-v1"`、`embedding_dimensions==[1024]`、`embedding_max_batch_inputs==32`、`embedding_max_input_tokens==8192`，否则 `raise ApiError(409, "embedding_space_conflict", …)`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-EMBEDDING-SPACE` → wire `code=embedding_space_conflict`；机制 `T-CFG-SPACE`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明能力键缺失型的 `capability_conflict`（ADM-SL-06）、不证明非 Embedding-v1 tier 的 responses 校验、不证明 embedding 数据面（DP-EMB-*）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（`/healthz` 200；`_baseline_settings`）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`。初始状态：`Embedding-v1` 存在。
- **输入与构造**：先创建 embedding deployment（错误的 `embedding_space_id`），再 PATCH：
  ```http
  POST /v1/deployments HTTP/1.1
  Authorization: Bearer dev-admin
  ```
  ```json
  {"name":"Embedding Wrong Space","provider_id":"prov_b","backend_model":"embedding-model",
   "capabilities":{"responses":false,"embeddings":true,"tools":false,"structured_outputs":false,
   "input_modalities":["text"],"output_modalities":["text"],"context_window":4096,"max_output_tokens":2048,
   "embedding_space_id":"wrong-space-id","embedding_dimensions":[1024],"embedding_max_batch_inputs":32,
   "embedding_max_input_tokens":8192},
   "enabled":true}
  ```
  ```http
  PATCH /v1/service-levels/Embedding-v1 HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  ```
  ```json
  {"deployment_ids": ["<new_embedding_depl_id>"]}
  ```
  构造点：新 deployment `embeddings=true`、`responses=false` 使 `_validate_level` 先通过 embedding-only 校验，再在 `embedding_space_id` 冻结检查处失败（确保命中 `embedding_space_conflict` 而非 `capability_conflict`）。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Embedding-v1")`；断言 200；记 `etag`、`version_before`、原 `deployment_ids`。
  3. `new_depl = admin_client_b.post("/v1/deployments", json={…})`；断言 `201`；记 `new_depl_id`、`new_depl_etag`。
  4. `resp = admin_client_b.patch("/v1/service-levels/Embedding-v1", json={"deployment_ids":[new_depl_id]}, headers={"If-Match": etag})`。
  5. 断言 `resp.status_code == 409`；`err = resp.json()["error"]`：断言 `err["code"]=="embedding_space_conflict"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  6. （零副作用核验）`GET /v1/service-levels/Embedding-v1` 断言 `deployment_ids` 与 `version` 均为原值。
  7. （teardown，`finally` 内）`DELETE /v1/deployments/{new_depl_id}`（最新 ETag）→ `204`；`GET` 断言 404。
- **重点关注步骤**：① **命中正确分支**——`embedding_space_id` 错误但 embedding/responses 标志正确，必须得 `embedding_space_conflict`；若得 `capability_conflict` 说明构造使交集丢键（错误构造）；② **Embedding-v1 专属**——该冻结检查仅对 `level_id=="Embedding-v1"` 生效；③ **零副作用**——失败后 `Embedding-v1` 成员/版本不变；④ **teardown 完整性**——新建 embedding deployment 未被引用（PATCH 失败回滚），可删除；必须删，否则残留；现有 [`at_adm_sl_07.py`](../../../../tests/system/api_test_v03/at_adm_sl_07.py) **未删除**该 deployment，须补齐；⑤ **错误信封 identity**——恰 5 键、`type=request_error`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 冻结向量空间规则（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）。
  - POST deployment：`201` + ETag。
  - PATCH SL：`409`；body `{"error":{"message":"Embedding-v1 requires the frozen BGE-M3 vector space","type":"request_error","code":"embedding_space_conflict","param":null,"retryable":false}}`。
  - 回读：`Embedding-v1.deployment_ids` 与 `version` 不变。
  - teardown：`DELETE` new deployment → `204`；随后 `GET` → `404`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `409` + `code=="embedding_space_conflict"`；`Embedding-v1` 未变；teardown 删除新建 deployment 且回读 404。
  - **FAIL**：status/code 错、`Embedding-v1` 被改、或 teardown 未删净。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实向量空间检查——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 GET/POST/PATCH/DELETE 的请求与原始响应（含 ETag 头，脱敏后）、`Embedding-v1` 前后对比、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 新建的 embedding deployment（最新 ETag；412 先重取），不改 `depl_b`/`Embedding-v1`、不写注入。退出前确认无残留 deployment、7 tier 齐全。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`registry.update_service_level`/`_validate_level`；错误目录 `ERR-EMBEDDING-SPACE`；机制 `T-CFG-SPACE`。自动化入口 [`at_adm_sl_07.py`](../../../../tests/system/api_test_v03/at_adm_sl_07.py)。**不依赖**其它 Case；与 ADM-SL-06 共享 PATCH 但校验分支不同。
