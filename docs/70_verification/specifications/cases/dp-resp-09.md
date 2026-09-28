# DP-RESP-09 — 禁字段 previous_response_id

- **Case ID**：`DP-RESP-09`
- **标题**：`POST /v1/responses` 携带禁字段 `previous_response_id`：`400 unsupported_field`，零副作用。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**禁用字段契约**：provider 续写/缓存类字段 `prompt_cache_key`/`prompt_cache_retention`/`previous_response_id` 出现即拒绝（本版本无 conversation 续写）。被测端点/规则：`POST /v1/responses`；需求 `LT-FUN-001`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-FIELD` → wire `code=unsupported_field`；实现 `src/inference/responses.py`（`FORBIDDEN_FIELDS`，`require(not (FORBIDDEN_FIELDS & set(body)), 400, "unsupported_field", "Unsupported provider continuation or cache field")`）。**不证明什么**：不证明未知/多余字段的拒绝（本 case 只覆盖显式禁字段清单；`additionalProperties:false` 路径见 DP-RESP-12..15 等）；不证明合法续写（本版本不存在）；不证明上游调用或答案。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- **输入与构造**：固定请求（合法四字段 + 一个禁字段）：

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
    "previous_response_id": "resp_xxx"
  }
  ```

  边界/构造点：`stream=true`/`store=false` 先通过跨字段要求，使失败唯一归因于禁字段；禁字段检查先于未知字段检查（`responses.py` 中 `FORBIDDEN_FIELDS` 的 `require` 在 `ALLOWED_FIELDS` 之前），故本 case 观测 `unsupported_field` 而非 `invalid_request`。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言键集恰 5 键、`code=="unsupported_field"`、`type=="request_error"`、`param is None`、`retryable is False`。
  5. 可选边界：分别以 `prompt_cache_key`、`prompt_cache_retention` 替换，断言同样 `unsupported_field`。
  6. 交叉核对零副作用（可选 `GET /v1/usage`，[§4.6](../llmtier-api-test-specification.md)）。
- **重点关注步骤**：① **`unsupported_field` 而非 `invalid_request`**——`previous_response_id` 在 `FORBIDDEN_FIELDS` 显式清单内，检查顺序决定错误码；② **拒绝在 dispatch 前**（`INV-5`）；③ **信封 identity**（5 键、`type=request_error`、无 `category`）；④ **非 SSE**；⑤ **零副作用**。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest`（不含续写字段）+ `ErrorEnvelope` + 系统设计 §7.8 `ERR-REQ-FIELD`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Unsupported provider continuation or cache field","type":"request_error","code":"unsupported_field","param":null,"retryable":false}}`。
  - 无 SSE 帧/`[DONE]`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=unsupported_field` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE。
  - **FAIL**：status/code 错（如返回 `invalid_request`）、返回 200/SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。
- **清理与复位**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；需求 `LT-FUN-001`；自动化入口 [`at_dp_resp_09.py`](../../../../tests/system/api_test_v03/at_dp_resp_09.py)。**不依赖**其它 Case；与 DP-RESP-12..15（未知字段路径）区分：本 case 命中显式禁字段清单，错误码为 `unsupported_field`。
