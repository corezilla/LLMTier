# DP-RESP-05 — unknown model 路由失败

- **Case ID**：`DP-RESP-05`
- **标题**：`POST /v1/responses` 使用未知 `model`：`404 model_not_found`，无上游调用。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**模型解析失败契约**：请求的 `model` 不在可见 tier 集合内时，M003 在 dispatch 前以 `404 model_not_found` 拒绝。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001/004`；错误目录 `ERR-MODEL-NOTFOUND` → wire `code=model_not_found`（系统设计 §7.8）；实现 `src/inference/responses.py`（捕获 `registry.get_service_level` 的 404 后 `raise ApiError(404, "model_not_found", "Model not found")`；`Router.admit` 在无候选时也抛 `404 model_not_found`）。**不证明什么**：不证明大小写/URL 编码的模型清单语义（DP-MODELS-03/04/05）；不证明合法模型的流式成功（DP-RESP-01/03/06）；不证明 `model` 字段缺失的校验（DP-RESP-08，属 `invalid_request`）；不证明上游答案。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端，见[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`model="NonExistentModel"` 不属于其中任一。
- **输入与构造**：固定请求（未知 model；其余字段合法齐备）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "NonExistentModel",
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": false
  }
  ```

  边界/构造点：`model` 语法合法（非空字符串）但不在 7 fixed tier；保持 `stream=true`/`store=false` 通过跨字段校验，使失败唯一归因于模型解析；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 404`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="model_not_found"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
  5. 交叉核对零副作用：无上游调用、无账本义务（可选 `GET /v1/usage`，[§4.6](../llmtier-api-test-specification.md)）。
- **重点关注步骤**：① **`model_not_found` 而非 `not_found`**——m5air 上 7 tier 由 bootstrap 建立，未知 tier 的 `get_service_level` 抛 `404 not_found` 后被 M003 统一改写为 `model_not_found`；无候选的 tier 亦走 `model_not_found`；② **拒绝在 dispatch 前**（`INV-5`）；③ **信封 identity**（5 键、无 `category`）；④ **非 SSE**。脚本 [`at_dp_resp_05.py`](../../../../tests/system/api_test_v03/at_dp_resp_05.py) 第 36 行已断言 `code=="model_not_found"`，与当前实现及 §3.2 权威清单一致。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-MODEL-NOTFOUND`（不依赖实现答案）。
  - HTTP：`404`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Model not found","type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；无 SSE 帧/`[DONE]`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 404 + `code=model_not_found` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE。
  - **FAIL**：status/code 不符（含返回 `not_found` 或 200）、信封键集错、被当 SSE 吞掉。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照。manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——环境 A 无状态，未创建/修改资源；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；自动化入口 [`at_dp_resp_05.py`](../../../../tests/system/api_test_v03/at_dp_resp_05.py)（已断言 `model_not_found`）；错误目录 `ERR-MODEL-NOTFOUND`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**不依赖**其它 Case；与 DP-RESP-08（缺 `model`）区分：本 case 有 `model` 但未知。
