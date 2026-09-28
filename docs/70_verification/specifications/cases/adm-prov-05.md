# ADM-PROV-05 — 更新 provider

- **Case ID**：`ADM-PROV-05`（与 §3.2 权威清单一致；本文件名 `adm-prov-05.md`，唯一对应）。
- **标题**：`PATCH /v1/providers/{id}` 携带正确 `If-Match` 更新 provider：HTTP 200 + 字段生效 + `version`/`ETag` 推进。
- **目的（被测契约）**：验证 Management Provider CRUD 的**乐观并发更新契约**。被测端点/规则：`PATCH /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateProvider`，`security=AdminBearerAuth`），请求体 `ProviderPatch`（`minProperties:1`，`additionalProperties:false`，可含 `name/kind/endpoint/secret_ref/enabled/usage`）；`If-Match` 头必须等于当前 ETag `"<id>.v<N>"`；成功 `200` + 新 `ProviderView` + 响应头 `ETag: "<id>.v<N+1>"`（`version` 单调 +1，[`registry.update_provider`](../../../../src/management/registry.py)）；失败 400 `invalid_request` / 404 `not_found` / 412 `version_conflict`。设计验证项 `VRC-MGMT-002`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明缺/过期 `If-Match` 的 412（ADM-PROV-06/07）、不证明删除（ADM-PROV-08/09/10）、不证明 `kind`/`secret_ref` 校验（ADM-PROV-11/12）、不证明 `usage` 子对象更新（ADM-PROV-13）、不证明并发两写者竞争（[测试设计 §5](../llmtier-api-test-specification.md) 归并发布前不单独构 case）；本 case 更新 `name`/`enabled` 两个标量，不触上游。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<端口>` + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（实例可启动 + `/healthz` 200；`_baseline_settings` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`Bearer dev-admin`）。**TS-003**：本 case 新建 provider 的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（默认 `http://192.168.1.9:9000/v1`），**禁止 `127.0.0.1`**。
- **输入与构造**：先创建独立 provider（避免污染 `prov_b`），再 PATCH：
  ```http
  POST /v1/providers HTTP/1.1   # 创建：kind=cloud, endpoint=LAN, secret_ref=null, enabled=true
  PATCH /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v1"
  Content-Type: application/json
  ```
  ```json
  {"name": "Provider Updated Name", "enabled": false}
  ```
  构造点：`If-Match` **必须取自创建响应的 `ETag`**（绝不硬编码版本）；`name` 改为固定新名、`enabled` 置 `false`；PATCH 体键集 ⊆ `{name,kind,endpoint,secret_ref,enabled,usage}` 且非空。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={name,kind:"cloud",endpoint:LAN,secret_ref:null,enabled:true})`；断言 `201`，记 `rid = body["id"]`、`original_version = body["version"]`、`original_etag = headers["ETag"]`。
  3. `patch = admin_client_b.patch(f"/v1/providers/{rid}", json={"name":"Provider Updated Name","enabled":False}, headers={"If-Match": original_etag})`。
  4. 断言 `patch.status_code == 200`；解析 `updated`：`name=="Provider Updated Name"`、`enabled is False`、`version > original_version`（期望 `original_version+1`）。
  5. 断言 `patch.headers` 含 `ETag` 且等于 `"<rid>.v<updated version>"`（推进后的版本）；`GET` 回读断言新值持久化且 ETag 一致。
  6. （teardown，`finally` 内）以最新 `GET` 的 `ETag` `DELETE` 本 provider，断言 `204`；`GET` 断言 `404`。
- **重点关注步骤**：① **CAS 语义**——`If-Match` 必须与当前版本严格相等才允许写入；本 case 用**从创建响应读取的真实 ETag**（绝不硬编码 `v1`，若创建时外部并发则可能不是 v1）；② **版本推进**——`version` 必 +1 且新 ETag 与之一致，`patch` 后旧 ETag 立即失效；③ **字段生效**——`name`/`enabled` 回显更新值，未提交字段保持原值；④ **412 后必须重取**——若因并发得 412，不得覆盖式重发旧 ETag，须重新 `GET` 取新 ETag（本 case 正常路径不触发）；⑤ **拒绝零副作用**——若 400/404，确认 provider 未被改；⑥ **teardown 到位**——更新后版本已推进，`DELETE` 必须用**最新** ETag。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderPatch`/`ProviderView` + ETag/CAS 规则。
  - 创建：`201`，ETag `"<rid>.v1"`。
  - PATCH：`200`；body `name` 与 `enabled` 为更新值；`version == original+1`；响应头 `ETag == "<rid>.v<original+1>"`。
  - 回读：`GET` → `200`，新值持久化、ETag 一致。
  - teardown：`DELETE`（最新 If-Match）→ `204`；随后 `GET` → `404`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `200` + 字段生效 + `version` 推进 + ETag 新值一致；回读一致；teardown `204` 且随后 `404`。
  - **FAIL**：任一断言不符（status 错、版本未推进、ETag 不符、字段未生效、teardown 未删净）。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：硬编码/伪造 ETag 绕过真实 `GET` 语义，或用 `127.0.0.1` 作上游 endpoint——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存创建/PATCH/回读/teardown 的请求与原始响应（含 `If-Match` 与 `ETag` 头、脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必含 `{…,environment:"b",inputs(ETag 字面值),oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 创建的 provider（用最新 ETag；412 则重取）；不改 `prov_b`/`depl_b`、不写注入。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。离开前确认无本次创建物残留。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ProviderPatch`/`ProviderView` 机器契约；ETag/CAS 规则 `registry.update_provider`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_prov_05.py`](../../../../tests/system/api_test_v03/at_adm_prov_05.py)。**不依赖**其它 Case（自建被测 provider）；与 ADM-PROV-06/07 互补（它们分别构造缺/过期 `If-Match`）但各自独立执行。
