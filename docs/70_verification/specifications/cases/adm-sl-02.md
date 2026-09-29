# ADM-SL-02 — 创建非 fixed tier

- **Case ID**：`ADM-SL-02`（与 §3.2 权威清单一致；本文件名 `adm-sl-02.md`，唯一对应）。
- **标题**：`POST /v1/service-levels` 用非固定 Tier 的 `id` 创建：HTTP 400 `invalid_request`，`param="id"`。
- **目的（被测契约）**：验证 Service Level 创建的 **固定 Tier 白名单校验**。被测端点/规则：`POST /v1/service-levels`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createServiceLevel`，body `ServiceLevelWrite`={`id`,`deployment_ids`,`enabled`}，`security=AdminBearerAuth`）；[`registry.create_service_level`](../../../../src/management/registry.py) 先做 body 键集校验，再做固定 Tier 白名单校验（非 `FIXED_TIERS` id → 400 `invalid_request`，[测试设计 §4.10](../llmtier-api-test-specification.md)）。设计验证项 `VRC-MGMT-002`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明已存在固定 Tier 的重复创建 409（ADM-SL-02b）、不证明成员能力/向量空间校验（ADM-SL-06/07）、不证明成功创建（无正向 Case；固定 Tier 由 bootstrap/`ensure_fixed_tiers` 预置）、不证明认证负向（AUTH-03/09）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=7 fixed tier 已存在、`diagnostic_injections` 为空。
- **输入与构造**：固定请求：
  ```http
  POST /v1/service-levels HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"id": "CustomTier", "deployment_ids": ["depl_b"], "enabled": true}
  ```
  构造点：`id="CustomTier"` 不在 `FIXED_TIERS`；`deployment_ids` 引用真实 `depl_b`（保证失败点确为 id 校验而非后续引用错误）；`enabled=true`。不注入故障；不构造其它非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `resp = admin_client_b.post("/v1/service-levels", json={"id":"CustomTier","deployment_ids":["depl_b"],"enabled":True})`。
  3. 断言 `resp.status_code == 400`。
  4. `err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["param"]=="id"`、`"not a fixed Tier" in err["message"]`；核对 `err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels` 断言 `CustomTier` 不存在，且 7 fixed tier 仍在。
- **重点关注步骤**：① **拒绝位置**——必须在写库前拒绝（`require` 在 `txn` 之前），`CustomTier` **不得**出现在资源表；② **错误信封 identity**——恰 5 键 `{message,type,code,param,retryable}`（无 `category`），`param=="id"`，`type` 由 400 导出为 `request_error`；③ **区分 400 与 409**——本 case 是非白名单 id（400），不同于已存在固定 Tier 的 409 `resource_conflict`（ADM-SL-02b）；④ **审计副作用**——经 `AdminService.mutate` 的失败会在 `audit_events` 记 `action="service_level.create"`、`result="failed"`、`request_id`，这是允许的审计记录、不是资源创建；不得误判为零写入；⑤ **不硬编码 message 全文**，断言稳定子串 `"not a fixed Tier"`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `FIXED_TIERS` 白名单规则。
  - HTTP：`400`；`Content-Type: application/json`；body `{"error":{"message":"Service Level ID is not a fixed Tier","type":"request_error","code":"invalid_request","param":"id","retryable":false}}`。
  - 资源表：`GET /v1/service-levels` 无 `CustomTier`。
  - 审计：`audit_events` 出现一条 `result="failed"` 的 `service_level.create`（可选交叉核对）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `param=="id"` + `type=="request_error"`，且 `CustomTier` 未被创建。
  - **FAIL**：status 非 400（含 409/500）、`code`/`param` 错、`CustomTier` 被写入。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充被测服务，或未真正发往 B 实例——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存POST 请求/原始响应（错误信封，脱敏后）、teardown 前 `GET /v1/service-levels` 快照、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——失败未创建资源。退出前确认 `GET /v1/service-levels` 仅 7 fixed tier、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ServiceLevelWrite` 机器契约；`registry.create_service_level`/`FIXED_TIERS`。自动化入口 [`at_adm_sl_02.py`](../../../../tests/system/api_test_v03/at_adm_sl_02.py)。**不依赖**其它 Case；与 ADM-SL-02b（已存在固定 Tier→409）互补但各自独立执行。
