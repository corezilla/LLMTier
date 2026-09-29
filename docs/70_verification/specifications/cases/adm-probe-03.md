# ADM-PROBE-03 — 探测未知 deployment

- **Case ID**：`ADM-PROBE-03`（与 §3.2 权威清单一致；本文件名 `adm-probe-03.md`，唯一对应）。
- **标题**：`POST /v1/probes` 带确认探测未知 deployment：HTTP 404 `not_found`。
- **目的（被测契约）**：验证探测对**不存在 deployment** 的资源解析契约。被测端点/规则：`POST /v1/probes`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `probeDeployment`，`security=AdminBearerAuth`）；[`AdminService.probe`](../../../../src/management/admin.py) 通过确认门后 `self.registry.get_deployment(body["deployment_id"])`，[`registry.get_deployment`](../../../../src/management/registry.py) 对未知 id 抛 404 `not_found`。设计验证项 `VRC-DIAG-004`；错误目录 `ERR-NOTFOUND` → wire `code=not_found`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-OBS-01`、`CT-ADMIN-001`。**不证明什么**：不证明缺确认的 400（ADM-PROBE-01）、不证明成功探测（ADM-PROBE-02）、不证明 provider 未知（无独立 case）、不证明认证负向（AUTH-03/09）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=仅有 `depl_b`，无其它 deployment。本 case 为 **MISSING**（§3.2 无 `at_adm_probe_03.py`），设计已写、实现待补。
- **输入与构造**：
  ```http
  POST /v1/probes HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"deployment_id": "does_not_exist", "confirm_external_call": true}
  ```
  构造点：`confirm_external_call=true` 使请求先通过确认门（否则被 400 拦，无法到达资源解析）；`deployment_id="does_not_exist"` 为不存在的 id。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. （负向前置）`GET /v1/deployments/does_not_exist` 断言 404（确认 id 确实不存在）。
  3. `resp = admin_client_b.post("/v1/probes", json={"deployment_id":"does_not_exist","confirm_external_call":True})`。
  4. 断言 `resp.status_code == 404`；`err = resp.json()["error"]`：断言 `err["code"]=="not_found"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/deployments` 断言列表未变、无新建 deployment。
- **重点关注步骤**：① **先确认后解析**——必须先通过确认门（`confirm_external_call=true`），否则得 `confirmation_required` 而非 `not_found`；本 case 锁定 `not_found`；② **404 而非 400**——未知 deployment 是资源不存在（404 `not_found`），不是输入校验 400（`invalid_request`）；③ **零副作用**——不触上游、不写 `probe_results`、不改任何 health；④ **错误信封 identity**——恰 5 键、`type=request_error`；⑤ **审计**——`AdminService.probe` 直接调用（非 `mutate`），本路径**不**写审计；不得期望审计行。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `registry.get_deployment` 的 not_found 语义。
  - HTTP：`404`；body `{"error":{"message":"Deployment not found","type":"request_error","code":"not_found","param":null,"retryable":false}}`。
  - 资源：无新增/变更 deployment。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`404` + `code=="not_found"` + `type=="request_error"`，且无资源/上游副作用。
  - **FAIL**：status 非 404（含 400/200）、`code` 错、或产生副作用。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 **`MISSING`**（§3.2），本轮未执行；缺口引用 §3.2/§9（MISSING ≠ NOT_RUN）。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实资源解析——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存GET/POST 请求与原始 404 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照（`/healthz` + deployment 列表前后）；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——未产生资源/health 变更。退出前确认 deployment 列表仍为 `{depl_b}`、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`registry.get_deployment`；错误目录 `ERR-NOTFOUND`；机制 `R-OBS-01`。自动化入口 **`MISSING`**（待补 `at_adm_probe_03.py`，落位按 §4.9/§8.5）。**不依赖**其它 Case；与 ADM-PROBE-01/02 互补。
