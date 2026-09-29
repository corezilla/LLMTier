# DP-RESP-15 — temperature 受理 / top_p 未知字段被拒

- **Case ID**：`DP-RESP-15`
- **标题**：`POST /v1/responses` 携带 `temperature` 与 `top_p`：`temperature` 为合法字段被受理，`top_p` 不属请求字段、组合命中 `400 invalid_request`。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**采样参数**的处理：OpenAPI `ResponsesRequest` 声明 `temperature`（`number`，`[0,2]`）为合法可选字段，但**未声明 `top_p`**；实现 `src/inference/responses.py` 的 `ALLOWED_FIELDS` 同样只含 `temperature`。故 `temperature` 单独出现被受理（对上游为透传，不参与本文断言），而 `top_p` 出现触发未知字段拒绝。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`。**不证明什么**：不证明 `temperature` 对生成结果的数值影响（§5 LLM 判据明确 temperature/top_p 不参与断言）；不证明任何别名；不证明合法流式成功（DP-RESP-01/06）。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端，见[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。`temperature` 路径需要上游可用；`top_p` 拒绝路径不需要。
- **输入与构造**：两个子请求。

  （a）`temperature` 单独（期望受理）：

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "say hello"}],
    "stream": true,
    "store": false,
    "temperature": 0.7
  }
  ```

  （b）`temperature` + `top_p`（期望拒绝）：

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "say hello"}],
    "stream": true,
    "store": false,
    "temperature": 0.7,
    "top_p": 0.9
  }
  ```

  边界/构造点：`temperature ∈ [0,2]`；`top_p` 不在 `ALLOWED_FIELDS`；`stream=true`/`store=false` 先通过跨字段要求，使 (b) 的失败唯一归因于 `top_p`。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（子请求 a，仅 `temperature`）：断言 `status_code == 200`、`Content-Type` 含 `text/event-stream`、含 `response.completed`。
  3. `POST /v1/responses`（子请求 b，含 `top_p`）：断言 `status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 (b) 的 `error`，断言 `code=="invalid_request"`、`message` 含 `"unknown fields"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
- **重点关注步骤**：① **字段白名单**——只有 `temperature` 合法，`top_p` 是未知字段；② **错误码归因**——`invalid_request`（非 `unsupported_field`）；③ **temperature 不参与数值断言**（§5）；④ **§3.2 与脚本一致**——§3.2 该行已为"`temperature` 接受、`top_p` 未知字段被拒"，[`at_dp_resp_15.py`](../../../../tests/system/api_test_v03/at_dp_resp_15.py) 第 37-49 行亦断言 `temperature` 200 + `top_p` 400 `invalid_request`（`top_p` 不在 OpenAPI/`ALLOWED_FIELDS`）。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest`（含 `temperature`、不含 `top_p`）+ `ErrorEnvelope`/`ErrorDetail`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）。
  - (a)：HTTP `200` + `text/event-stream` + `response.completed`。
  - (b)：HTTP `400`；`Content-Type: application/json`；`error.code=="invalid_request"`、`type=="request_error"`、`param=null`、`retryable=false`；无 SSE。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：(a) 200 + SSE；(b) `400` + `invalid_request` + 非 SSE。
  - **FAIL**：(a) 非 200；或 (b) 被接受（200）/返回非 `invalid_request`。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 (a)/(b) 请求 body、HTTP status/headers、原始响应（SSE 与错误信封）、发出命令、exit code、环境快照。manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——`store=false`、环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；OpenAPI `ResponsesRequest`；实现 `src/inference/responses.py`（`ALLOWED_FIELDS`）；自动化入口 [`at_dp_resp_15.py`](../../../../tests/system/api_test_v03/at_dp_resp_15.py)（已断言 `temperature` 200 + `top_p` 400 `invalid_request`）。**不依赖**其它 Case。
