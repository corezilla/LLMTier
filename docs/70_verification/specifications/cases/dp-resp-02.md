# DP-RESP-02 — stream=false 被拒

- **Case ID**：`DP-RESP-02`
- **标题**：`POST /v1/responses` 传 `stream=false`：在 dispatch 前返回 `400 unsupported_request`，零副作用。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的 **`stream` 跨字段硬约束**——本版本仅受理 `stream=true`（OpenAPI `ResponsesRequest.stream` 为 `const:true`；ISD M003 `additionalProperties:false` + 跨字段硬约束）。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-UNSUPPORTED` → wire `code=unsupported_request`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）；实现 `src/inference/responses.py`（`require(body.get("stream") is True and body.get("store") is False, 400, "unsupported_request", "Only stream=true and store=false are supported")`）。**不证明什么**：不证明 `store=true` 被拒（DP-RESP-07，反向约束）；不证明合法流式成功与事件序列（DP-RESP-01/06）；不证明上游调用、模型答案或账本行为（本 case 在 dispatch 前拒绝）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`，`Authorization: Bearer dev-data`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在路由/dispatch 之前）。
- **输入与构造**：固定请求（固定 prompt，见[测试设计 §4.4](../llmtier-api-test-specification.md)）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": false,
    "store": false
  }
  ```

  边界/构造点：只翻转 `stream` 为 `false`，保持 `store=false`，以**隔离 stream 约束**（若同时 `store=true` 则先命中其它分支，无法区分违反哪一条）；`model` 取合法 responses-capable tier；其余字段齐备，避免先命中"缺字段"校验。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`；断言响应头 `Content-Type` 含 `application/json`（**不是** `text/event-stream`）。
  4. 解析 `resp.json()["error"]`，断言键集恰为 `{message,type,code,param,retryable}`（[测试设计 §4.6](../llmtier-api-test-specification.md)，无 `category`）。
  5. 断言 `code=="unsupported_request"`、`type=="request_error"`、`param is None`、`retryable is False`。
  6. 交叉核对零副作用：本响应非 SSE；如需强证据，`GET /v1/usage`（同 principal + 当前时间窗）确认**无新增已完成 obligation**（拒绝即无副作用，[测试设计 §4.6](../llmtier-api-test-specification.md)）。
- **重点关注步骤**：① **拒绝位置**——必须在 `router.admit`/上游调用**之前**（`INV-5`），不得先发上游再报错；② **信封 identity**——恰 5 键、`type` 由状态导出（400 < 500 ⇒ `request_error`）、无 `category`；③ **非 SSE**——错误走 `_json(exc.status, exc.envelope(), ...)`，不得以 `text/event-stream` 返回被当成功流吞掉；④ **只翻转 stream**——`store=false` 保持，保证失败归因唯一；⑤ **零副作用**——不产生账本义务/上游调用。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` 契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）+ 系统设计 §7.8 `ERR-REQ-UNSUPPORTED`（不依赖实现答案）。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Only stream=true and store=false are supported","type":"request_error","code":"unsupported_request","param":null,"retryable":false}}`。
  - 无 SSE 帧；无 `[DONE]`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=unsupported_request` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE 全部 match。
  - **FAIL**：任一断言不符（status 非 400、code 错、返回 200/SSE 被吞、信封键集错）。
  - **BLOCKED**：测试代码/契约问题（解析器逻辑错、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 mock/替代路径冒充真实 m5air 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封（脱敏后）、发出命令、exit code、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（字段见[测试设计 §4.8](../llmtier-api-test-specification.md)）与原始证据文件；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——环境 A 只读/无状态，未创建/修改/删除任何资源；退出前确认 `/readyz` 仍显示 7 tier（见[测试设计 §2.8](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；responses-capable tier `Worker`；自动化入口 [`at_dp_resp_02.py`](../../../../tests/system/api_test_v03/at_dp_resp_02.py)。**不依赖**其它 Case；与 DP-RESP-07（`store=true`）互补但各自独立执行。
