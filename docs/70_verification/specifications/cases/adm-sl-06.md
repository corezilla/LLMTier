# ADM-SL-06 — 成员能力不一致

- **Case ID**：`ADM-SL-06`（与 §3.2 权威清单一致；本文件名 `adm-sl-06.md`，唯一对应）。
- **标题**：`PATCH /v1/service-levels/{id}` 绑定能力不一致的 deployment 集合：HTTP 409 `capability_conflict`。
- **目的（被测契约）**：验证 Service Level 成员的**能力交集一致性契约**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`）；[`registry.update_service_level`](../../../../src/management/registry.py) 计算 `_capability_intersection(ids)`（非布尔键要求 `all(v == values[0])`，否则丢弃该键），再看 `_validate_level` 的 `set(capabilities) == CAPABILITY_KEYS`——一旦交集丢键即 `raise ApiError(409, "capability_conflict", …)`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-CAPABILITY` → wire `code=capability_conflict`；机制 `R-CFG-01`、`T-CFG-SPACE`；需求/机制链 `LT-FUN-005`、`CT-ADMIN-001`。**不证明什么**：不证明向量空间冲突（ADM-SL-07）、不证明非白名单/非法字段 400（ADM-SL-02/04b）、不证明合法 PATCH 成功（ADM-SL-04）、不证明 provider_id 不可改（ADM-DEPL-09）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（`/healthz` 200；`_baseline_settings`：`depl_b` `context_window=4096`、`max_output_tokens=2048`、`input_modalities=["text"]`、`responses=True`）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`。初始状态：`Senior` 存在且 `deployment_ids=["depl_b"]`。
- **输入与构造**：分两步：先创建一个 `context_window` 不同的 deployment（用 LAN provider，避免 TS-003 违规——此处只创建引用 `prov_b` 的 deployment，不触发上游），再 PATCH。
  ```http
  POST /v1/deployments HTTP/1.1
  Authorization: Bearer dev-admin
  ```
  ```json
  {"name":"Deployment Different Context","provider_id":"prov_b","backend_model":"model-diff-context",
   "capabilities":{"responses":true,"embeddings":false,"tools":true,"structured_outputs":false,
   "input_modalities":["text"],"output_modalities":["text"],"context_window":8192,"max_output_tokens":2048,
   "embedding_space_id":null,"embedding_dimensions":null,"embedding_max_batch_inputs":null,"embedding_max_input_tokens":null},
   "enabled":true}
  ```
  ```http
  PATCH /v1/service-levels/Senior HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  ```
  ```json
  {"deployment_ids": ["depl_b", "<new_depl_id>"]}
  ```
  构造点：新 deployment `context_window=8192` 与 `depl_b` 的 `4096` 不等（非布尔键被交集丢弃），其余键一致；`deployment_ids` 引用真实存在的两个 deployment（先创建再引用）。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Senior")`；断言 200；记 `etag`、`version_before`。
  3. `new_depl = admin_client_b.post("/v1/deployments", json={…})`；断言 `201`；记 `new_depl_id = new_depl.json()["id"]` 与 `new_depl_etag = new_depl.headers["ETag"]`。
  4. `resp = admin_client_b.patch("/v1/service-levels/Senior", json={"deployment_ids":["depl_b", new_depl_id]}, headers={"If-Match": etag})`。
  5. 断言 `resp.status_code == 409`；`err = resp.json()["error"]`：断言 `err["code"]=="capability_conflict"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  6. （零副作用核验）`GET /v1/service-levels/Senior` 断言 `deployment_ids` 仍为 `["depl_b"]`、`version==version_before`。
  7. （teardown，`finally` 内）`GET /v1/deployments/{new_depl_id}` 取最新 ETag；`DELETE /v1/deployments/{new_depl_id}`（`If-Match`）→ 断言 `204`；`GET` 断言 404。
- **重点关注步骤**：① **交集丢键**——`context_window` 因 `4096≠8192` 被 `_capability_intersection` 丢弃，`set(capabilities) != CAPABILITY_KEYS` 触发 409；须确认失败码是 `capability_conflict` 而非 `resource_conflict`/`embedding_space_conflict`；② **两个真实 deployment**——`deployment_ids` 必须引用已存在 deployment（否则 `_capability_intersection` 早退 400 `invalid_request`，非本 case）；③ **零副作用**——失败后 `Senior` 成员与版本不变；④ **teardown 完整性**——新建 deployment **未被任何 tier 引用**（PATCH 失败回滚），因此可 `DELETE`；必须删除，否则残留污染同 session 的 deployment 列表与 `ADM-DEPL-01`；⑤ **错误信封 identity**——恰 5 键、`type=request_error`。
  > **实现缺口（登记）**：现有 [`at_adm_sl_06.py`](../../../../tests/system/api_test_v03/at_adm_sl_06.py) 创建了 `Deployment Different Context` 却**未在 `finally` 删除**，违反 §2.8 teardown。按本设计，case 级入口须补 `DELETE` 清理后方可判 PASS。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 能力交集规则。
  - POST deployment：`201` + ETag。
  - PATCH SL：`409`；body `{"error":{"message":"Bound deployments do not have one compatible capability set","type":"request_error","code":"capability_conflict","param":null,"retryable":false}}`。
  - 回读：`Senior.deployment_ids==["depl_b"]`、`version` 不变。
  - teardown：`DELETE` new deployment → `204`；随后 `GET` → `404`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `409` + `code=="capability_conflict"`；`Senior` 未变；teardown 删除新建 deployment 且回读 404。
  - **FAIL**：status/code 错（如 400/409 其它 code/200）、`Senior` 被改、或 teardown 未删净。
  - **BLOCKED**：fixture/断言逻辑问题（如 deployment 创建失败、能力交集不可触发）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实交集冲突——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 GET/POST/PATCH/DELETE 的请求与原始响应（含 ETag 头，脱敏后）、`Senior` 前后对比、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 新建的 deployment（最新 ETag；若 412 先重取），不改 `depl_b`、不删既有 tier、不写注入。退出前确认无本次创建的 deployment 残留、7 tier 齐全。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`registry.update_service_level`/`_capability_intersection`/`_validate_level`；错误目录 `ERR-CAPABILITY`；机制 `R-CFG-01`/`T-CFG-SPACE`。自动化入口 [`at_adm_sl_06.py`](../../../../tests/system/api_test_v03/at_adm_sl_06.py)。**不依赖**其它 Case；与 ADM-SL-07（向量空间冲突）共享 PATCH 但不同校验分支。
