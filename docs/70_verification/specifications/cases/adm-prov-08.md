# ADM-PROV-08 — 删除 provider

- **Case ID**：`ADM-PROV-08`（与 §3.2 权威清单一致；本文件名 `adm-prov-08.md`，唯一对应）。
- **标题**：`DELETE /v1/providers/{id}` 携带正确 `If-Match` 删除无引用 provider：HTTP 204，随后 `GET` 404。
- **目的（被测契约）**：验证 Management Provider CRUD 的**删除契约**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；被删除前须确认无 deployment 引用；成功 `204 No Content`（空 body）；失败 404 `not_found` / 409 `resource_in_use`（被引用，ADM-PROV-10）/ 412 `version_conflict`（ADM-PROV-09）。设计验证项 `VRC-MGMT-001`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明缺/过期 `If-Match` 的 412（ADM-PROV-09）、不证明被引用 409（ADM-PROV-10）、不证明删除 deployment/service-level；本 case 删除**本 case 新建且无引用**的 provider。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足 §2.1 **附加（B 类）**（实例 `/healthz` 200；`_BASELINE_SETTINGS` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`Bearer dev-admin`）。**TS-003**：新建 provider 的 `endpoint` 用 LAN 常量，**禁止 `127.0.0.1`**。
- **输入与构造**：先创建无引用 provider，再 DELETE：
  ```http
  POST /v1/providers HTTP/1.1   # kind=local, endpoint=LAN, secret_ref=null, enabled=true
  DELETE /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v1"
  ```
  构造点：`rid`/`ETag` 取自创建响应（**绝不硬编码版本**）；新建 provider 无 deployment 引用，删除必然可成功。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={…})`；断言 `201`，记 `rid`、`etag = headers["ETag"]`。
  3. `del_resp = admin_client_b.delete(f"/v1/providers/{rid}", headers={"If-Match": etag})`；断言 `status_code == 204` 且响应 body 为空。
  4. `get_resp = admin_client_b.get(f"/v1/providers/{rid}")`；断言 `status_code == 404`、`error.code == "not_found"`。
  5. 可选：`GET /v1/providers` 列表确认 `rid` 不再出现。
  6. （teardown）**无**——本 case 已在步骤 3 删除创建物；若步骤 3 未成功，则 `finally` 内以 `GET` 的 ETag 重试 `DELETE`。
- **重点关注步骤**：① **204 空 body**——删除成功为 `204 No Content`，不得返回 200 带 body；② **删除后不可见**——随后 `GET` 必须 404 `not_found`（软删/残留即 FAIL）；③ **If-Match 正确**——用创建响应的 ETag；若 412，先 `GET` 取新 ETag 再删；④ **不误删基线**——只删本 case 创建的 provider，绝不碰 `prov_b`；⑤ **幂等性边界**——第二次 DELETE 同 id 应为 404；⑥ **零残留**——teardown 后该 id 在列表/详情均不可见。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `deleteProvider` 204 + ETag 规则。
  - DELETE：`204`，无 body。
  - 随后 GET：`404` + `error.code=="not_found"`。
  - 列表：不含该 `rid`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`204` 且 body 空；随后 `GET 404 not_found`；列表不含该 id。
  - **FAIL**：status 非 204、删除后仍可读（残留）、或误删其它资源。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以替代路径/伪造 204 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存创建/DELETE/回读/列表的请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`；`manifest.json` 必含 `environment:"b"`、`inputs`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`、`reproduction_cmd`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**teardown 由本 case 的 DELETE 承担**；若删除失败，`finally` 内重试（必要时先取新 ETag）。不改 `prov_b`/`depl_b`、不写注入。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`deleteProvider` 机器契约；CAS/ETag 规则 `registry.delete_provider`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_prov_08.py`](../../../../tests/system/api_test_v03/at_adm_prov_08.py)。**不依赖**其它 Case；与 ADM-PROV-09（缺 If-Match 412）、ADM-PROV-10（被引用 409）互补但各自独立。
