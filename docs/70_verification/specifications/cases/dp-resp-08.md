# DP-RESP-08 — 缺 model

- **Case ID**：`DP-RESP-08`
- **标题**：`POST /v1/responses` 缺 `model`：字段齐备性校验失败，`400 invalid_request`（§3.2 记为 `param=model`）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**必填字段齐备性**：`model`/`input`/`stream`/`store` 四者缺一即在 dispatch 前拒绝。被测端点/规则：`POST /v1/responses`；需求 `LT-FUN-001`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；实现 `src/inference/responses.py`（`require({"model","input","stream","store"} <= set(body), 400, "invalid_request", "model, input, stream, and store are required")`）。**不证明什么**：不证明未知 model 的解析失败（DP-RESP-05，属 `model_not_found`）；不证明 `stream=false`/`store=true` 的跨字段拒绝（DP-RESP-02/07）；不证明上游调用或答案。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- **输入与构造**：固定请求（省略 `model`，其余三字段齐备）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": false
  }
  ```

  边界/构造点：仅缺 `model`；`input`/`stream`/`store` 齐备，使失败唯一归因于缺失的 `model`；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="invalid_request"`、`type=="request_error"`、`retryable is False`；键集恰 5 键。
  5. **记录 `param` 实测值**并与 §3.2 声明比对（见下"已知偏差"）。
  6. 交叉核对零副作用：无上游调用、无账本义务（可选，[§4.6](../llmtier-api-test-specification.md)）。
- **重点关注步骤**：① **拒绝先于模型解析**——齐备性检查在 `get_service_level`/`admit` 之前，缺 `model` 不得报 `model_not_found`；② **信封 identity**（5 键、`type=request_error`、无 `category`）；③ **非 SSE**；④ **`param` 归因**见偏差；⑤ **零副作用**。
- **已知偏差（必须登记）**：§3.2 权威清单与本 case 标题把本项记为 `400 invalid_request,param=model`；但当前实现 `src/inference/responses.py` 的齐备性检查以 `require(...)` **未传 `param`** 调用，`ApiError.param` 默认为 `None`，故 wire `error.param` 实为 `null`。本设计的**硬 Oracle 为 status + code**（`400` + `invalid_request`）；`param` 按**实测**记录（当前应为 `null`），并作为偏差上报代码 owner（要么实现补 `param="model"`，要么修正 §3.2）。不得为迎合文档而伪造 `param=model`。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest.required`（`model` 必填）+ `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`error.code=="invalid_request"`、`type=="request_error"`、`retryable==false`；`message` 含 `"required"` 语义（实现为 `"model, input, stream, and store are required"`）。
  - `error.param`：实测记录（当前实现为 `null`；§3.2 声称 `model`，见偏差）。
  - 无 SSE 帧/`[DONE]`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=invalid_request` + `type=request_error` + `retryable=false` + 非 SSE + 零副作用；`param` 实测值与代码一致（当前 `null`），偏差已登记。
  - **FAIL**：status/code 错、报 `model_not_found`、返回 200/SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封（含 `param` 实测）、发出命令、exit code、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。
- **清理与复位**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；需求 `LT-FUN-001`；自动化入口 [`at_dp_resp_08.py`](../../../../tests/system/api_test_v03/at_dp_resp_08.py)（只断 status+code，未断 `param`）。**不依赖**其它 Case；与 DP-RESP-05 区分：本 case 无 `model` 字段，非未知值。
