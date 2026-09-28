# DP-RESP-07 — store=true 被拒

- **Case ID**：`DP-RESP-07`
- **标题**：`POST /v1/responses` 传 `store=true`：在 dispatch 前返回 `400 unsupported_request`，零副作用。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的 **`store` 跨字段硬约束**——本版本不保存 provider conversation 状态，仅受理 `store=false`（OpenAPI `ResponsesRequest.store.const=false`；[piko-data-plane-control.md](../../../60_interfaces/piko-data-plane-control.md) §"LLMTier 只透传/规范化，不保存 Agent conversation"）。被测端点/规则：`POST /v1/responses`；需求 `LT-INT-006`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-UNSUPPORTED` → wire `code=unsupported_request`；实现 `src/inference/responses.py`（同一 `require(stream is True and store is False, 400, "unsupported_request", ...)`）。**不证明什么**：不证明 `stream=false` 被拒（DP-RESP-02）；不证明合法流式成功（DP-RESP-01/06）；不证明任何持久化/会话恢复语义（本版本不存在）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- **输入与构造**：固定请求（只翻转 `store=true`，保持 `stream=true` 以隔离 store 约束）：

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
    "store": true
  }
  ```

  边界/构造点：`stream=true` 通过第一条跨字段要求，使失败唯一归因于 `store`；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言键集恰 5 键、`code=="unsupported_request"`、`type=="request_error"`、`param is None`、`retryable is False`。
  5. 交叉核对零副作用：`GET /v1/usage` 无新增 obligation（可选，[§4.6](../llmtier-api-test-specification.md)）。
- **重点关注步骤**：① **零副作用是重点**——`store=true` 的拒绝必须**不落任何 provider conversation 状态**，且无上游调用（`INV-5`）；② **信封 identity**（5 键、`type=request_error`、无 `category`）；③ **非 SSE**；④ **只翻转 store**，与 DP-RESP-02 形成配对；⑤ message 与 `stream=false` 共用同一条 `require`，均为 `"Only stream=true and store=false are supported"`。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `store.const=false` + `ErrorEnvelope`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）+ 系统设计 §7.8 `ERR-REQ-UNSUPPORTED`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Only stream=true and store=false are supported","type":"request_error","code":"unsupported_request","param":null,"retryable":false}}`。
  - 无 SSE 帧；无 `[DONE]`；无 provider conversation 持久化副作用。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=unsupported_request` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE + 零副作用 match。
  - **FAIL**：任一断言不符（含返回 200/SSE）。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。
- **清理与复位**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；需求 `LT-INT-006`（[llmtier-requirements.md](../../../10_requirements/llmtier-requirements.md)）；自动化入口 [`at_dp_resp_07.py`](../../../../tests/system/api_test_v03/at_dp_resp_07.py)。**不依赖**其它 Case；与 DP-RESP-02 互补。
