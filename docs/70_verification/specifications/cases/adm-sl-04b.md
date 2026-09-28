# ADM-SL-04b — 更新非法字段

- **Case ID**：`ADM-SL-04b`（与 §3.2 权威清单一致；本文件名 `adm-sl-04b.md`，唯一对应）。
- **标题**：`PATCH /v1/service-levels/{id}` 提交未知字段：HTTP 400 `invalid_request`（"Unknown or empty …"）。
- **目的（被测契约）**：验证 Service Level PATCH 的**字段白名单校验**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，body `ServiceLevelPatch.additionalProperties:false`）；[`registry.update_service_level`](../../../../src/management/registry.py) 首行做 PATCH 字段白名单校验（仅接受 `deployment_ids`/`enabled`，否则 400 `invalid_request`，[测试设计 §4.10](../llmtier-api-test-specification.md)）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明合法 PATCH 成功（ADM-SL-04）、不证明缺/过期 `If-Match` 412（SL 412 未单独构 case）、不证明成员能力/向量空间冲突（ADM-SL-06/07）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（`/healthz` 200；`_baseline_settings`）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`。初始状态：`Worker` 存在。
- **输入与构造**：
  ```http
  PATCH /v1/service-levels/Worker HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"unknown_field": "value"}
  ```
  构造点：body 键 `unknown_field` 不在 `{deployment_ids,enabled}` 白名单内，且 body 非空；`If-Match` 用真实 ETag（使失败点确为**字段校验**而非 412）。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Worker")`；断言 200；记 `etag = get.headers["ETag"]`、`version_before = body["version"]`。
  3. `resp = admin_client_b.patch("/v1/service-levels/Worker", json={"unknown_field":"value"}, headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`"Unknown or empty" in err["message"]`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels/Worker` 断言 `version == version_before`（字段校验在 `txn` 之前，未改库）。
- **重点关注步骤**：① **拒绝位置**——`require` 在 `with txn` 之前，未知字段请求**不得**改写 `Worker`（`version` 不变）；② **400 而非 412**——必须用真实有效 ETag 以隔离字段校验；若得 412 说明输入构造错误；③ **错误信封 identity**——恰 5 键，`type=request_error`，`code=invalid_request`；④ **param 语义**——该 `require` 未传 `param`，故 `param==null`（不要错误期望 `"unknown_field"`）；⑤ **审计**——失败经 `mutate` 记 `result="failed"` 审计行，非资源修改。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelPatch.additionalProperties:false` + `ErrorEnvelope`。
  - HTTP：`400`；body `{"error":{"message":"Unknown or empty service level patch","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 资源：`Worker.version` 不变。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `"Unknown or empty" in message`，且 `Worker.version` 未变。
  - **FAIL**：status 非 400、`code`/message 错、`version` 被推进。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或注入未命中——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 GET/PATCH 请求与原始 400 响应（脱敏后）、PATCH 后 `GET` 的 `version`、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——校验失败未改库。退出前确认 `Worker.version` 与 `enabled` 保持原值、无注入残留。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ServiceLevelPatch` 机器契约；`registry.update_service_level` 的白名单 `require`。自动化入口 [`at_adm_sl_04b.py`](../../../../tests/system/api_test_v03/at_adm_sl_04b.py)。**不依赖**其它 Case；与 ADM-SL-04（合法 PATCH）互补。
