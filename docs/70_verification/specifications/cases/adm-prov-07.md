# ADM-PROV-07 — 过期 ETag

- **Case ID**：`ADM-PROV-07`（与 §3.2 权威清单一致；本文件名 `adm-prov-07.md`，唯一对应）。
- **标题**：`PATCH /v1/providers/{id}` 携带**过期/错误** `If-Match`：HTTP 412 + `error.code=="version_conflict"` + `error.current_version`，无写入。
- **目的（被测契约）**：验证 Management Provider CRUD 的**乐观并发前置校验（过期前置条件）**。被测端点/规则：`PATCH /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateProvider`，`security=AdminBearerAuth`）；当 `If-Match` 形态合法但**不等于**当前 ETag 时，[`registry.update_provider`](../../../../src/management/registry.py) 抛 `ApiError(412, "version_conflict", extra={"current_version": <N>})`；wire 信封含额外键 `current_version`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-STALE` → `version_conflict`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功更新（ADM-PROV-05）、不证明**缺头** 412（ADM-PROV-06）、不证明 DELETE 的过期 ETag（本 case 只发 PATCH）、不证明并发两写者（§5）；本 case 只锁定"头存在但值过期"。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**TS-003**：请求中的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1`**。
- **输入与构造**：先创建独立 provider，再发带**错误** `If-Match` 的 PATCH：
  ```http
  POST /v1/providers HTTP/1.1   # kind=local, endpoint=LAN, secret_ref=null, enabled=true
  PATCH /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v99"
  Content-Type: application/json
  ```
  ```json
  {"name": "Stale Update"}
  ```
  构造点：`rid` 取自创建响应；`If-Match` 构造为 `"<rid>.v99"`——**形态合法**（`"<id>.v<N>"` 含双引号）但版本值远超当前（过期/不存在），确保 412 由**值不匹配**触发而非格式错；body 仅含合法字段。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={…})`；断言 `201`，记 `rid`、`version_before`、`name_before`。
  3. `bad_etag = '"' + rid + '.v99"'`；`patch = admin_client_b.patch(f"/v1/providers/{rid}", json={"name":"Stale Update"}, headers={"If-Match": bad_etag})`。
  4. 断言 `patch.status_code == 412`；`err = patch.json()["error"]`：`err["code"] == "version_conflict"`、`err["type"] == "request_error"`、`err["retryable"] is False`、`err["current_version"] == version_before`（≠ 99）。
  5. 交叉核对：`GET` 断言 `name==name_before`、`version==version_before`、ETag 未变（零副作用）。
  6. （teardown，`finally` 内）以当前 ETag `DELETE`，断言 `204`；`GET` 断言 `404`。
- **重点关注步骤**：① **形态合法但值错**——`"<rid>.v99"` 是刻意构造的过期 ETag；若实现把格式错也当 412 会掩盖真实问题，故 body 保持合法、只让版本值错；② **`current_version` 揭示真实版本**——断言它等于创建后的版本（证明实现知道当前值），而非回显请求值；③ **零副作用**——拒绝不得推进 `version`/改 `name`；④ **与 ADM-PROV-06 的区分**——06 缺头（`None`），07 值不等；⑤ **teardown** 用当前版本删除。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-STALE` + ETag 严格匹配规则。
  - HTTP：`412`；`Content-Type: application/json`。
  - body：`{"error":{"code":"version_conflict","type":"request_error","param":null,"retryable":false,"current_version":<version_before>, "message":"<nonempty>"}}`。
  - 无资源变化。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==412` 且 `error.code=="version_conflict"` 且 `error.current_version==version_before`、`type=="request_error"`、`retryable is False`；回读无变化；teardown 成功。
  - **FAIL**：status 非 412（含成功写入）、`code` 不符、`current_version` 缺失或错误、或出现副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 412 或绕过真实 CAS——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建/PATCH（含过期 `If-Match` 字面值）/回读/teardown 的请求与响应、`current_version`。
- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 创建的 provider；不改 `prov_b`/`depl_b`、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ErrorEnvelope` 机器契约；CAS/ETag 规则 `registry.update_provider`/`_etag`；机制 `T-CFG-CAS`；错误目录 `ERR-STALE`；自动化入口 [`at_adm_prov_07.py`](../../../../tests/system/api_test_v03/at_adm_prov_07.py)。**不依赖**其它 Case；与 ADM-PROV-05/06 互补但各自独立。
