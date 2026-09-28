# DP-RESP-13 — truncation 未知字段被拒

- **Case ID**：`DP-RESP-13`
- **标题**：`POST /v1/responses` 携带 `truncation`（未知顶层字段）：`400 invalid_request`（"Request body contains unknown fields"），dispatch 前拒绝、零副作用。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**非请求字段 `truncation`** 的处理契约。契约由 OpenAPI `ResponsesRequest.additionalProperties:false` + 实现 `src/inference/responses.py` 的 `ALLOWED_FIELDS`（不含 `truncation`）与 `require(set(body) <= ALLOWED_FIELDS, 400, "invalid_request", "Request body contains unknown fields")` 定义：未知顶层字段在 dispatch 前被拒。设计验证项 `VRC-INF-001`。**不证明什么**：不证明任何截断策略（`truncation` 不改变输入截断行为，本版本无该参数）；不证明 `max_output_tokens` 截断（DP-RESP-10）；不证明合法流式成功（DP-RESP-01/06）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- **输入与构造**：固定请求（合法四字段 + 非请求字段）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": false,
    "truncation": "auto"
  }
  ```

  边界/构造点：`stream=true`/`store=false` 先通过跨字段要求；`truncation` 不在 `ALLOWED_FIELDS`，触发未知字段拒绝。可选对照：去掉 `truncation` 重发应 200。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言观测形态，按**当前机器契约**判定：`status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="invalid_request"`、`message` 含 `"unknown fields"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
  5. 可选对照：去掉 `truncation` 重发，断言 `200` + SSE。
- **重点关注步骤**：① **未知字段路径**——`truncation` 既不在 OpenAPI `ResponsesRequest`，也不在 `ALLOWED_FIELDS`；② **错误码归因**——未知字段 → `invalid_request`（非 `unsupported_field`）；③ **拒绝在 dispatch 前、零副作用**；④ **§3.2 与脚本一致**——§3.2 该行为 `400 invalid_request`，[`at_dp_resp_13.py`](../../../../tests/system/api_test_v03/at_dp_resp_13.py) 第 32-33 行亦断言 `400` + `invalid_request`，契约已收敛于拒绝语义。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest.additionalProperties:false` + `ErrorEnvelope`/`ErrorDetail`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），不依赖实现答案。
  - HTTP `400`；`Content-Type: application/json`；`error.code=="invalid_request"`、`type=="request_error"`、`param=null`、`retryable=false`；无 SSE。
  - "静默忽略"（200 + SSE）不是候选真值：§3.2 与脚本均为拒绝语义。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `invalid_request` + 非 SSE + 零副作用。
  - **FAIL**：返回 `200`（未知字段被接受，违反 `additionalProperties:false`）；或 status/code 不符、返回 SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、可选对照、发出命令、exit code、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败/偏差现场不截断。
- **清理与复位**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；OpenAPI `ResponsesRequest`；实现 `src/inference/responses.py`（`ALLOWED_FIELDS`）；自动化入口 [`at_dp_resp_13.py`](../../../../tests/system/api_test_v03/at_dp_resp_13.py)（已断言 `400 invalid_request`）。**不依赖**其它 Case；与 DP-RESP-12/14 同类。
