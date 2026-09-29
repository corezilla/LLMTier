# ADM-PROV-08 — 删除 provider

- **Case ID**：`ADM-PROV-08`（与 §3.2 权威清单一致；本文件名 `adm-prov-08.md`，唯一对应）。
- **标题**：`DELETE /v1/providers/{id}` 携带正确 `If-Match` 删除无引用 provider：HTTP 204，随后 `GET` 404。
- **目的（被测契约）**：验证 Management Provider CRUD 的**删除契约**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；被删除前须确认无 deployment 引用；成功 `204 No Content`（空 body）；失败 404 `not_found` / 409 `resource_in_use`（被引用，ADM-PROV-10）/ 412 `version_conflict`（ADM-PROV-09）。设计验证项 `VRC-MGMT-001`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明缺/过期 `If-Match` 的 412（ADM-PROV-09）、不证明被引用 409（ADM-PROV-10）、不证明删除 deployment/service-level；本 case 删除**本 case 新建且无引用**的 provider。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。**TS-003**：请求中的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1`**。
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
  5. 可选：`GET /v1/providers` 列表确认 `rid` 不再出现。**注**：该列表 GET（[`admin.page()`](../../../../src/management/admin.py)）会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`），属服务端读路径副作用、非用户资源，报告须登记，**不得笼统声称"零写入"**。
  6. （teardown）**无**——本 case 已在步骤 3 删除创建物；若步骤 3 未成功，则 `finally` 内以 `GET` 的 ETag 重试 `DELETE`。
- **重点关注步骤**：① **204 空 body**——删除成功为 `204 No Content`，不得返回 200 带 body；② **删除后不可见**——随后 `GET` 必须 404 `not_found`（软删/残留即 FAIL）；③ **If-Match 正确**——用创建响应的 ETag；若 412，先 `GET` 取新 ETag 再删；④ **不误删基线**——只删本 case 创建的 provider，绝不碰 `prov_b`；⑤ **幂等性边界**——第二次 DELETE 同 id 应为 404；⑥ **零残留**——teardown 后该 id 在列表/详情均不可见；⑦ **列表读路径副作用**——第 5 步可选列表 GET 会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照（`admin.page()`），报告须登记，**不得声称"零写入"**。
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
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建/DELETE/回读/列表的请求与原始响应。
- **清理与复位**：**teardown 由本 case 的 DELETE 承担**；若删除失败，`finally` 内重试（必要时先取新 ETag）。不改 `prov_b`/`depl_b`、不写注入。第 5 步可选列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`deleteProvider` 机器契约；CAS/ETag 规则 `registry.delete_provider`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_prov_08.py`](../../../../tests/system/api_test_v03/at_adm_prov_08.py)。**不依赖**其它 Case；与 ADM-PROV-09（缺 If-Match 412）、ADM-PROV-10（被引用 409）互补但各自独立。
