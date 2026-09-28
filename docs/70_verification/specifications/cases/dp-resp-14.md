# DP-RESP-14 — max_tokens 未知字段被拒（无别名）

- **Case ID**：`DP-RESP-14`
- **标题**：`POST /v1/responses` 携带 `max_tokens`（非 `max_output_tokens`）：不存在别名，`400 invalid_request`（"Request body contains unknown fields"）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对 **`max_tokens`** 的处理：本版本**无** `max_output_tokens` 别名。OpenAPI `ResponsesRequest` 仅声明 `max_output_tokens`，且实现 `src/inference/responses.py` 的 `ALLOWED_FIELDS` 不含 `max_tokens`，`require(set(body) <= ALLOWED_FIELDS, ...)` 将其作为未知顶层字段拒绝为 `400 invalid_request`。设计验证项 `VRC-INF-001`。**不证明什么**：不证明截断语义（DP-RESP-10 用 `max_output_tokens`）；不证明别名映射（本版本无映射）；不证明合法流式成功（DP-RESP-01/06）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- **输入与构造**：固定请求（用 `max_tokens` 取代 `max_output_tokens`）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "say hello"}],
    "stream": true,
    "store": false,
    "max_tokens": 50
  }
  ```

  边界/构造点：`stream=true`/`store=false` 先通过跨字段要求；`max_tokens` 不在 `ALLOWED_FIELDS`。对照（**必做，属 PASS 条件**）：改用 `max_output_tokens:50` 重发，断言 `200` + SSE（证明正名字段被受理，反证无别名）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言观测形态，按**当前机器契约**判定：`status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="invalid_request"`、`message` 含 `"unknown fields"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
  5. **对照（必做）**：以 `max_output_tokens:50` 重发，断言 `200` + SSE（证明正名字段受理、反证无别名）。
- **重点关注步骤**：① **无别名**——`max_tokens` 不映射到 `max_output_tokens`，直接拒绝；② **错误码归因**——未知字段 → `invalid_request`（非 `unsupported_field`）；③ **拒绝在 dispatch 前、零副作用**；④ **§3.2 与脚本一致**——§3.2 该行为 `400 invalid_request`，[`at_dp_resp_14.py`](../../../../tests/system/api_test_v03/at_dp_resp_14.py) 第 32-33 行亦断言 `400` + `invalid_request`，契约已收敛于拒绝语义。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest`（无 `max_tokens` 属性）+ `ErrorEnvelope`/`ErrorDetail`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）。
  - HTTP `400`；`Content-Type: application/json`；`error.code=="invalid_request"`、`type=="request_error"`、`param=null`、`retryable=false`；无 SSE。
  - 别名语义（`max_tokens` → 200 + SSE）不是候选真值：§3.2 与脚本均为拒绝语义。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `invalid_request` + 非 SSE + 零副作用；且对照（必做）中 `max_output_tokens:50` 重发得到 `200` + SSE。
  - **FAIL**：返回 `200`（`max_tokens` 被当别名接受）；或 status/code 不符；或对照的 `max_output_tokens` 重发未成功。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、正名字段对照（必做）、发出命令、exit code、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败/偏差现场不截断。
- **清理与复位**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；OpenAPI `ResponsesRequest`；实现 `src/inference/responses.py`（`ALLOWED_FIELDS`）；自动化入口 [`at_dp_resp_14.py`](../../../../tests/system/api_test_v03/at_dp_resp_14.py)（已断言 `400 invalid_request`）。**不依赖**其它 Case；与 DP-RESP-10（正名字段截断）对照。
