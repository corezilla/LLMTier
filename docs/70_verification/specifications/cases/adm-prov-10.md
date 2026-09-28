# ADM-PROV-10 — 删除被引用 provider

- **Case ID**：`ADM-PROV-10`（与 §3.2 权威清单一致；本文件名 `adm-prov-10.md`，唯一对应）。
- **标题**：`DELETE /v1/providers/{id}` 删除被活动 deployment 引用的 provider：HTTP 409 + `error.code=="resource_in_use"`，provider 保留。
- **目的（被测契约）**：验证 Management Provider CRUD 的**引用完整性（删除引用保护）契约**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；当该 provider 被任一 deployment 引用时，[`registry.delete_provider`](../../../../src/management/registry.py) 抛 `ApiError(409, "resource_in_use", "Provider is referenced by a deployment")`；前提是 `If-Match` 已匹配（否则先 412）。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-INUSE` → `resource_in_use`；机制 `T-CFG-DELREF`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功删除（ADM-PROV-08）、不证明缺/过期 If-Match 412（ADM-PROV-09）、不证明 deployment 侧删除被 service-level 引用的 409；本 case 依赖 baseline `prov_b → depl_b` 的引用关系，不删除任何资源（删除必然被拒）。
  > 规范注记：§3.2 行与 §11.1 均记本 case 错误码为 `resource_in_use`（`ERR-INUSE`）；实现与 [`at_adm_prov_10.py`](../../../../tests/system/api_test_v03/at_adm_prov_10.py) 一致。若外部简报把它写作 `resource_conflict`，以 `openapi` enum + 源码为准（`resource_conflict` 是**重名/已存在**语义，见 ADM-PROV-02 重名分支，非引用保护）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足 §2.1 **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 **1 provider `prov_b` + 1 deployment `depl_b` + 7 fixed tier**，且 `depl_b.provider_id == "prov_b"`、7 tier 的 `deployment_ids` 均指向 `depl_b`；`_probe_deployment(depl_b)` 断言 `healthy`。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b` / `admin_client_b`（`Bearer dev-admin`）。**本 case 不新建资源，直接对 baseline `prov_b` 发删除**（预期被拒，故不破坏基线）。
- **输入与构造**：固定两步（先取真实 ETag，再删除）：
  ```http
  GET /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin

  DELETE /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<GET 返回的 ETag，形如 prov_b.v1>"
  ```
  构造点：`prov_b` 被 `depl_b` 引用（baseline 固定）；`If-Match` **取自 `GET` 的响应头**（绝不硬编码，version 会随前序 B 类写 case 变化）；本 case 不附带 body。不注入故障；不构造非法输入（缺/错 If-Match 会先得 412，属 ADM-PROV-09，不是本 case 的目标码）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `current = admin_client_b.get("/v1/providers/prov_b")`；断言 `200`，记 `etag = current.headers.get("ETag")`（必须存在）。
  3. `del_resp = admin_client_b.delete("/v1/providers/prov_b", headers={"If-Match": etag})`。
  4. 断言 `del_resp.status_code == 409`；`err = del_resp.json()["error"]`：`err["code"] == "resource_in_use"`、`err["type"] == "request_error"`、`err["retryable"] is False`；`"referenced" in err["message"].lower()`。
  5. 交叉核对：`GET /v1/providers/prov_b` 仍 `200`、`version`/ETag 未变（资源保留）。
  6. （teardown）**无 teardown**——删除被拒，基线未被触碰；不删除 `prov_b`/`depl_b`。
- **重点关注步骤**：① **409 而非 412/404**——`If-Match` 正确后必须先过 CAS，再因引用被拒 409；若得 412，说明 ETag 取错（版本已变）；② **码必须是 `resource_in_use`**——引用保护语义，不是 `resource_conflict`（重名）也不是 `version_conflict`（CAS）；③ **资源保留**——第 5 步确认 `prov_b` 与引用关系未变；④ **不得真删基线**——本 case 绝不能在拒绝前删除 `prov_b`（否则破坏整个 B 类 session）；⑤ **ETag 必须实取**——B 类前序写 case 会推进 `prov_b` 版本（如 ADM-PROV-13 usage），硬编码会 412。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-INUSE` 语义（不依赖 message 文案）。
  - GET：`200` + ETag。
  - DELETE：`409`；body `error.code=="resource_in_use"`、`type=="request_error"`、`retryable is False`、`message` 含 `referenced`（语义旁证）。
  - 资源保留：`GET` 仍 `200`，版本未推进。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`DELETE 409` + `error.code=="resource_in_use"`；`GET` 仍 `200` 且版本不变。
  - **FAIL**：status 非 409（如 204 误删/412）、`code` 不符（如 `resource_conflict`/`version_conflict`）、或基线被破坏。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture 缺 `prov_b`/`depl_b` 引用、断言逻辑问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用，或 `prov_b`/`depl_b` 基线未建立——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造 409、或真正删除基线后以 mock 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 `GET prov_b`（含 ETag）、`DELETE` 请求与 409 原始响应（脱敏后）、拒绝后回读、发出命令、exit code、`elapsed`、`GET /v1/deployments/depl_b` 引用快照；`manifest.json` 必含 `environment:"b"`、`inputs`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`、`reproduction_cmd`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——删除被拒，`prov_b`/`depl_b` 与 7 tier 均未变；不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[测试设计 §4.7](../llmtier-api-test-specification.md)）。离开前确认 `prov_b` 仍在、`/readyz` 7 tier。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b` 与 baseline `prov_b`+`depl_b`（[§4.4](../llmtier-api-test-specification.md)）；`deleteProvider`/`ErrorEnvelope` 机器契约；`registry.delete_provider` 引用检查；机制 `T-CFG-DELREF`；错误目录 `ERR-INUSE`；自动化入口 [`at_adm_prov_10.py`](../../../../tests/system/api_test_v03/at_adm_prov_10.py)。**不依赖**其它 Case（依赖 baseline 引用关系，而非某 case 先跑）；与 ADM-PROV-08/09 互补但各自独立。
