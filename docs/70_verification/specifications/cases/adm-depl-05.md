# ADM-DEPL-05 — 删除 deployment

- **Case ID**：`ADM-DEPL-05`（与 §3.2 权威清单一致；本文件名 `adm-depl-05.md`，唯一对应）。
- **标题**：`DELETE /v1/deployments/{id}` 携带正确 `If-Match` 删除 deployment：HTTP 204，随后 `GET` 返回 404。
- **目的（被测契约）**：验证 Management Deployment CRUD 的**删除契约**。被测端点/规则：`DELETE /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteDeployment`，`security=AdminBearerAuth`），`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；成功 `204` 无 body（[`registry.delete_deployment`](../../../../src/management/registry.py)）；失败 404 `not_found` / 409 `resource_in_use`（被 service level 引用）/ 412 `version_conflict`（缺/过期 If-Match）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明缺 `If-Match` 的 412（ADM-PROV-09 同机制；本 case 走正确 ETag 路径）、不证明被引用删除的 409 `resource_in_use`（基线 `depl_b` 被 7 tier 引用；本 case **不**删它）、不证明列表/详情（ADM-DEPL-01/03）、不证明更新（ADM-DEPL-04）；本 case 只删本次自建 deployment，不触上游。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（实例可启动 + `/healthz` 200；`_BASELINE_SETTINGS` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier；`depl_b` probe `healthy`）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b`、`admin_client_b`（`Bearer dev-admin`）。**TS-003**：`prov_b.endpoint` 必须是 LAN IP 上的 fake provider。
- **输入与构造**：先创建独立 deployment，再删除（避免删基线 `depl_b`——它被 7 tier 引用，删除会 409）：
  ```http
  POST /v1/deployments HTTP/1.1          # 创建：provider_id=prov_b, capabilities 12 键, enabled=true
  DELETE /v1/deployments/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v1"
  ```
  构造点：`If-Match` **取自创建响应（或先 `GET`）的 `ETag`**（绝不硬编码）；删除目标必须是**本 case 自建**、未被 service level 引用的 deployment；不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/deployments", json=<DeploymentWrite, provider_id="prov_b">)`；断言 `201`，记 `rid`、`etag = create.headers["ETag"]`。
  3. `del = admin_client_b.delete(f"/v1/deployments/{rid}", headers={"If-Match": etag})`。
  4. 断言 `del.status_code == 204`；断言响应体为空（204 无 body）。
  5. `get = admin_client_b.get(f"/v1/deployments/{rid}")`；断言 `404` 且 `error.code == "not_found"`（信封 5 键、`type=="request_error"`）。
  6. 交叉核对：`GET /v1/deployments`（或按 id 过滤）确认 `rid` 不再出现，且基线 `depl_b` 仍在。
- **重点关注步骤**：① **204 无 body**——不得把删除响应当 JSON 解析；② **If-Match 必需且正确**——用创建响应的真实 ETag；缺/过期属 412（ADM-PROV-09 同机制，本 case 不重测）；③ **删除自己创建物**——**绝不**删基线 `depl_b`（被 7 tier 引用，会 409 `resource_in_use`），否则破坏 B 类基线并威胁整班；④ **二次核验 404**——删除后 `GET` 必须 404 且 `code=not_found`，证明真删；⑤ **不触上游**——删除只写注册表；⑥ **幂等语义**——重复 DELETE 同一 id 期望 404（本 case 只发一次，不重测幂等）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `deleteDeployment` 204 + ETag/CAS 规则。
  - 创建：`201`，ETag `"<rid>.v1"`。
  - DELETE：`204`，无 body。
  - 随后 GET：`404`，`error.code=="not_found"`（恰 5 键、`type=="request_error"`）。
  - 基线 `depl_b` 仍在 `GET /v1/deployments` 中。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`DELETE` → `204`（无 body），随后 `GET` → `404 not_found`，且基线未被破坏。
  - **FAIL**：DELETE status 非 204、随后 GET 非 404、错误信封不符，或误删基线/引用资源。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 204/404、硬编码 ETag，或用 `127.0.0.1` 作上游 endpoint——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存创建/DELETE/随后 GET 的请求与原始响应（含 `If-Match`，脱敏后）、删除前后 deployment 列表、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必含 `{…,environment:"b",inputs(ETag 字面值),oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**teardown 即删除动作本身**——本 case 的 DELETE 已完成清理，无剩余创建物（若 DELETE 失败或中途异常，须在 `finally` 中重取最新 ETag 后重试删除，或记录并保留证据）。不改基线 `depl_b`/`prov_b`/7 tier、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。离开前确认本 case 创建物已删净、基线仍在。
- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；基线 provider `prov_b`；`DeploymentWrite`/`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` `delete_deployment`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_depl_05.py`](../../../../tests/system/api_test_v03/at_adm_depl_05.py)。**不依赖**其它 Case（自建被测 deployment）；与 ADM-DEPL-02/04 共享创建前置但各自独立执行。
