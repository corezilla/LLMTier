# ADM-PROV-09 — 删除缺 If-Match

- **Case ID**：`ADM-PROV-09`（与 §3.2 权威清单一致；本文件名 `adm-prov-09.md`，唯一对应）。
- **标题**：`DELETE /v1/providers/{id}` **缺** `If-Match`：HTTP 412 + `error.code=="version_conflict"` + `error.current_version`，资源保留。
- **目的（被测契约）**：验证 Management Provider CRUD 的**删除前置校验（缺前置条件）**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；当 `If-Match` 缺省时，[`registry.delete_provider`](../../../../src/management/registry.py) 的版本比较失败，抛 `ApiError(412, "version_conflict", extra={"current_version": <N>})`；wire 信封含额外键 `current_version`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-STALE` → `version_conflict`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功删除（ADM-PROV-08）、不证明被引用 409（ADM-PROV-10）、不证明 PATCH 的缺 If-Match（ADM-PROV-06）、不证明过期 ETag 值（本 case 只发**缺头**）；本 case 只锁定"缺头"这一种前置失败。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足 §2.1 **附加（B 类）**（实例 `/healthz` 200；`_BASELINE_SETTINGS` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier）；`depl_b` probe `healthy`。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`Bearer dev-admin`）。**TS-003**：新建 provider 的 `endpoint` 用 LAN 常量，**禁止 `127.0.0.1`**。
- **输入与构造**：先创建独立 provider，再发**不带** `If-Match` 的 DELETE：
  ```http
  POST /v1/providers HTTP/1.1   # kind=local, endpoint=LAN, secret_ref=null, enabled=true
  DELETE /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  ```
  构造点：DELETE **完全不携带 `If-Match`**；`rid` 取自创建响应。不注入故障；不构造其它非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={…})`；断言 `201`，记 `rid`、`etag`、`version_before`。
  3. `del_resp = admin_client_b.delete(f"/v1/providers/{rid}")`（**无** `headers`）；断言 `status_code == 412`。
  4. `err = del_resp.json()["error"]`：`err["code"] == "version_conflict"`、`err["type"] == "request_error"`、`err["retryable"] is False`、`err["current_version"] == version_before`。
  5. 交叉核对：`GET /v1/providers/{rid}` 断言 `200`（**资源被保留**）、`version`/ETag 未变。
  6. （teardown，`finally` 内）以 `GET` 的 ETag `DELETE`，断言 `204`；`GET` 断言 `404`。
- **重点关注步骤**：① **412 而非 204**——缺 `If-Match` 的 DELETE 必须被拒，绝不落入删除分支；② **资源保留**——第 5 步 `GET` 必须 200 且 `version` 不变，证明拒绝无副作用；③ **`current_version` 正确**——等于创建后的版本；④ **与 ADM-PROV-08 区分**——08 带正确头 204，09 缺头 412；⑤ **teardown 补删**——拒绝后资源仍在，`finally` 必须用正确 ETag 删除，避免 B 类实例残留。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-STALE` + 删除 CAS 规则。
  - HTTP：`412`；`Content-Type: application/json`。
  - body：`{"error":{"code":"version_conflict","type":"request_error","param":null,"retryable":false,"current_version":<version_before>, "message":"<nonempty>"}}`。
  - 资源保留：`GET` 仍 `200`，版本未变。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==412` 且 `error.code=="version_conflict"` 且 `error.current_version==version_before`、`type=="request_error"`、`retryable is False`；资源保留；teardown 成功。
  - **FAIL**：status 非 412（如 204 误删）、`code` 不符、缺 `current_version`、或资源被删。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 412 或以带正确头的 DELETE 冒充缺头场景——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存创建/DELETE（证明**无** `If-Match`）/回读/teardown 的请求与响应（脱敏后）、`current_version`、发出命令、exit code、`elapsed`；`manifest.json` 必含 `environment:"b"`、`inputs`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`、`reproduction_cmd`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**必须 teardown（`finally` 强制）**——拒绝后资源仍在，须用正确 ETag 删除本 case 创建的 provider；不改 `prov_b`/`depl_b`、不写注入。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ErrorEnvelope` 机器契约；CAS/ETag 规则 `registry.delete_provider`/`_etag`；机制 `T-CFG-CAS`；错误目录 `ERR-STALE`；自动化入口 [`at_adm_prov_09.py`](../../../../tests/system/api_test_v03/at_adm_prov_09.py)。**不依赖**其它 Case；与 ADM-PROV-08/10 互补但各自独立。
