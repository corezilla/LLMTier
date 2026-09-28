# ADM-SL-02b — 创建已存在 fixed tier

- **Case ID**：`ADM-SL-02b`（与 §3.2 权威清单一致；本文件名 `adm-sl-02b.md`，唯一对应）。
- **标题**：`POST /v1/service-levels` 用已存在的固定 Tier `id`（`Senior`）创建：HTTP 409 `resource_conflict`。
- **目的（被测契约）**：验证固定 Tier 的**唯一性冲突契约**。被测端点/规则：`POST /v1/service-levels`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createServiceLevel`）；[`registry.create_service_level`](../../../../src/management/registry.py) 通过白名单与能力校验后 `INSERT INTO service_levels`，主键冲突时捕获 `UNIQUE` 并抛 `ApiError(409, "resource_conflict", "Service level already exists")`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-CONFLICT` → wire `code=resource_conflict`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明非白名单 id 的 400（ADM-SL-02）、不证明成员能力/向量空间校验（ADM-SL-06/07）、不证明 PATCH/DELETE（ADM-SL-04/05）。本 case **只**锁 409 `resource_conflict`。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（实例 `/healthz` 200；`_baseline_settings` = `prov_b`+`depl_b`+7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`。初始状态 = `Senior` 已由 bootstrap 预创建（`_baseline_settings` 的 7 tier 各含 `["depl_b"]`、`enabled=true`）。
- **输入与构造**：固定请求：
  ```http
  POST /v1/service-levels HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"id": "Senior", "deployment_ids": ["depl_b"], "enabled": true}
  ```
  构造点：`id="Senior"` 是合法固定 Tier 且已存在；`deployment_ids=["depl_b"]` 使 `_capability_intersection` 得 12 键、`_validate_level("Senior", …)` 通过（`depl_b.responses=True`），从而失败点落在**唯一性 INSERT**而非 400/409 能力校验。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`；`GET /v1/service-levels/Senior` 断言 200（存在）。
  2. `resp = admin_client_b.post("/v1/service-levels", json={"id":"Senior","deployment_ids":["depl_b"],"enabled":True})`。
  3. 断言 `resp.status_code == 409`。
  4. `err = resp.json()["error"]`：断言 `err["code"]=="resource_conflict"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels/Senior` 仍 200，`version` 与步骤 1 相同（未被本次 POST 改动）。
- **重点关注步骤**：① **区分 400 vs 409**——`Senior` 是合法白名单 id、能力交集合法，因此必须走唯一性冲突 409；若得 400 说明在更早的校验被拦（输入构造错误）；② **失败点在写库**——本 case 的 409 由 `INSERT` 的 `UNIQUE` 触发（`registry.py` 异常分支），与 ADM-SL-02 的 dispatch 前 400 不同；③ **零副作用**——已存在的 `Senior` 行及其 `version` 不得因冲突 POST 改变；④ **审计**——失败经 `mutate` 记 `result="failed"` 审计行、不创建资源；⑤ **错误信封 identity**——恰 5 键、`type=request_error`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 固定 Tier 唯一性约束。
  - HTTP：`409`；body `{"error":{"message":"Service level already exists","type":"request_error","code":"resource_conflict","param":null,"retryable":false}}`。
  - 资源：`GET /v1/service-levels/Senior` 200 且 `version` 不变。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`409` + `code=="resource_conflict"` + `type=="request_error"`，且 `Senior` 未被改动。
  - **FAIL**：status 非 409、`code` 错、或 `Senior` 被修改/新增第二条。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实唯一性约束——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 POST 请求/原始 409 响应（脱敏后）、POST 前后 `GET /v1/service-levels/Senior`（含 ETag/version）、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——冲突未改库。退出前确认 7 fixed tier 与其 `version` 未被本次 POST 改动、无注入残留。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ServiceLevelWrite` 机器契约；`registry.create_service_level` 的 UNIQUE 分支；错误目录 `ERR-CONFLICT`。自动化入口 [`at_adm_sl_02b.py`](../../../../tests/system/api_test_v03/at_adm_sl_02b.py)。**不依赖**其它 Case；与 ADM-SL-02（非白名单→400）互补但各自独立执行。
