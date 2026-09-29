# DP-RESP-17 — embedding-only 等级发 Responses

- **Case ID**：`DP-RESP-17`
- **标题**：`POST /v1/responses` 使用 embedding-only 等级：`400 unsupported_model`（`param=model`）（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**能力门契约**：所选 model 的能力声明必须 `capabilities.responses == true`，否则在 dispatch 前拒绝。被测端点/规则：`POST /v1/responses`；错误目录 `ERR-REQ-MODEL` → wire `code=unsupported_model`；实现 `src/inference/responses.py`（`require(caps.get("responses") is True, 400, "unsupported_model", "Selected model does not support Responses", "model")`）；需求链 `LT-FUN-001`/`LT-INT-001`、`R-INF-01`、设计验证项 `VRC-INF-001`、机制 `T-STREAM`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明缺少 `model`（DP-RESP-08）或未知 model（DP-RESP-05）；不证明 `tools`/`max_output_tokens` 的次级能力门；不证明上游调用（在能力门拒绝）。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP），且 `/readyz` 含 7 fixed tier（含 `Embedding-v1`）。fixture `api_client`（Data 角色客户端，见[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`Embedding-v1` 为 embedding-only（`capabilities.responses == false`）。**不需要上游可用**（能力门在 dispatch 前）。
- **输入与构造**：固定请求（embedding-only 等级 + responses 形态 body）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "Embedding-v1",
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": false
  }
  ```

  边界/构造点：`model="Embedding-v1"` 必须是 7 fixed tier 之一（否则先命中 DP-RESP-05 的 `model_not_found`）；`stream=true`/`store=false` 通过跨字段要求，使失败唯一归因于能力门。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线及 `Embedding-v1` 存在（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `error`，断言 `code=="unsupported_model"`、`param=="model"`、`type=="request_error"`、`retryable is False`，键集恰 5 键。
- **重点关注步骤**：① **能力门先于路由**——在 `get_service_level` 成功后、`admit` 前拒绝；不得为 embedding-only 等级尝试路由；② **`param="model"`**——本错误码实现显式带 `param`（与 DP-RESP-08 的 `null` 不同）；③ **信封 identity**（5 键、无 `category`）；④ **非 SSE**；⑤ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_17.py`。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest.model` + 等级能力声明 + `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-REQ-MODEL`（不依赖实现答案）。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Selected model does not support Responses","type":"request_error","code":"unsupported_model","param":"model","retryable":false}}`。
  - 无 SSE 帧/`[DONE]`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=unsupported_model` + `param="model"` + `type=request_error` + `retryable=false` + 非 SSE。
  - **FAIL**：status/code/param 错、返回 200/SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（`Embedding-v1` 缺失等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；须先实现入口，未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照（`/readyz` 含 `Embedding-v1`）。manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；fixed tier `Embedding-v1` 的 `capabilities.responses=false`；错误目录 `ERR-REQ-MODEL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_17.py` MISSING（§3.2）**；**不依赖**其它 Case。
