# ADM-PROBE-01 — 探测缺确认

- **Case ID**：`ADM-PROBE-01`（与 §3.2 权威清单一致；本文件名 `adm-probe-01.md`，唯一对应）。
- **标题**：`POST /v1/probes` 缺显式确认：HTTP 400 `confirmation_required`。
- **目的（被测契约）**：验证外部探测的**显式确认门**。被测端点/规则：`POST /v1/probes`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `probeDeployment`，body `ProbeRequest`=`{deployment_id,confirm_external_call}`，`security=AdminBearerAuth`）；[`AdminService.probe`](../../../../src/management/admin.py) 首行按 `confirm_external_call` 确认门规则校验（[测试设计 §4.10](../llmtier-api-test-specification.md)）。设计验证项 `VRC-DIAG-004`；错误目录 `ERR-CONFIRM` → wire `code=confirmation_required`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-OBS-01`、`CT-ADMIN-001`、`CT-OPS-001`。**不证明什么**：不证明带确认的成功探测（ADM-PROBE-02）、不证明未知 deployment 的 404（ADM-PROBE-03）、不证明探测对 deployment health 的写入（ADM-PROBE-02/`apply_probe_result`）、不证明认证负向（AUTH-03/09）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`（`Bearer dev-admin`）。初始状态 = m5air 3 provider / 4 deployment / 7 fixed tier。本 case 为**拒绝路径**，不触上游、不产生费用。
- **输入与构造**：
  ```http
  POST /v1/probes HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {}
  ```
  构造点：空对象使 `body.get("confirm_external_call") is True` 为假且键集不符；**不**提供 `deployment_id`（拒绝发生在 deployment 解析之前）。不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.post("/v1/probes", json={})`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="confirmation_required"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （可选交叉核对）`POST /v1/probes` body `{"deployment_id":"dep_local_gemma"}`（有 deployment 但无 confirm）→ 仍 400 `confirmation_required`（确认门先于资源解析）。
- **重点关注步骤**：① **确认门优先**——缺 `confirm_external_call` 必须在**任何上游调用/deployment 解析前**返回 400，不得先 404/502；② **错误码正确性**——是 `confirmation_required`（`ERR-CONFIRM`），不是 `invalid_request`（键集/确认联合 `require` 统一抛 `confirmation_required`）；③ **零副作用**——拒绝不触上游、不写 `probe_results`、不改 `deployments.health`、不产生费用；④ **错误信封 identity**——恰 5 键、`type=request_error`；⑤ **审计**——本路径直接用 `app.admin.probe`（非 `mutate`），故**不**写审计；不得期望审计行。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 探测确认规则。
  - HTTP：`400`；body `{"error":{"message":"Probe requires explicit confirmation","type":"request_error","code":"confirmation_required","param":null,"retryable":false}}`。
  - 无上游调用、无 health 变化。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="confirmation_required"` + `type=="request_error"`，且无上游/health 副作用。
  - **FAIL**：status 非 400、`code` 错、或观察到上游调用/health 变更。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 POST 请求与原始 400 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + `GET /v1/deployments/dep_local_gemma` 前后 health 对比以证无副作用）。`manifest.json` 必含 `{…,environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍显示 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ProbeRequest` 机器契约；`AdminService.probe` 的 `require`；错误目录 `ERR-CONFIRM`。自动化入口 [`at_adm_probe_01.py`](../../../../tests/system/api_test_v03/at_adm_probe_01.py)。**不依赖**其它 Case；与 ADM-PROBE-02（带确认→200）互补。
