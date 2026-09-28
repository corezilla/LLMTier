# DP-RESP-10 — max_output_tokens 截断

- **Case ID**：`DP-RESP-10`
- **标题**：`POST /v1/responses` 传 `max_output_tokens=10`：SSE 以 `response.incomplete` 终止，`incomplete_details.reason=="max_output_tokens"`。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**截断终止契约**：当输出达到 `max_output_tokens` 上限时，终态为 `incomplete`（非 `completed`）且 `incomplete_details.reason=="max_output_tokens"`，SSE 仍以唯一 terminal + `[DONE]` 收尾。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；实现 `src/http_api/sse.py`（terminal 类型 `f"response.{response['status']}"`）与 provider 归一（`src/inference/providers/openai.py` 透传 upstream `status`/`incomplete_details`）。**不证明什么**：不证明 `context_window` 硬上限边界（§5 注：Qwen 实测 API 层未触发，本 case 只覆盖可测的 `max_output_tokens` 截断）；不证明超时/断开异常（DP-RESP-11/21）；不证明模型内容。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；所选 tier `Worker` 的 `capabilities.max_output_tokens` 必须 `>=10`，否则请求会先被字段范围校验拒为 `400 invalid_request`（`param="max_output_tokens"`）。
- **输入与构造**：固定请求（长输出 prompt 迫使达到 10 token 上限）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "Count from 1 to 1000. Output only numbers separated by commas."}],
    "stream": true,
    "store": false,
    "max_output_tokens": 10
  }
  ```

  边界/构造点：`max_output_tokens=10` 必须在能力上界内（`responses.py` 校验 `1 <= max_output_tokens <= caps.max_output_tokens`，否则 `400 invalid_request`）；固定长输出 prompt 保证触发截断；`store=false` 无副作用。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses` 以流式读取；断言 `status_code == 200` 且 `Content-Type` 含 `text/event-stream`。
  3. 逐帧解析 `text/event-stream`（[§4.5](../llmtier-api-test-specification.md)）。
  4. 断言事件序列含 `response.created`；断言**恰好一个** terminal，且为 `response.incomplete`（不是 `response.completed`）。
  5. 断言 `response.incomplete.response.status == "incomplete"`，且 `response.incomplete_details.reason == "max_output_tokens"`。
  6. 断言 `sequence_number` 自 0 严格递增；`data: [DONE]` 收尾。
- **重点关注步骤**：① **terminal identity**——必须是 `response.incomplete`，出现 `response.completed` 即 FAIL（截断被误报为成功）；② **唯一 terminal**——`response.completed` 与 `response.incomplete` 不得并存；③ **reason 精确匹配** `"max_output_tokens"`；④ **`[DONE]` 仍收尾**——截断不是异常，仍是正常流终止；⑤ **字段范围前置校验**——若 `max_output_tokens` 超过能力上界，先被 `400 invalid_request` 拒绝，本 case 不得把该路径当截断。
- **期望结果与独立 Oracle**：独立 Oracle = 标准 Responses terminal 形态 + OpenAPI `ResponsesResponse.incomplete_details`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件：`response.created` 首帧；唯一 terminal `response.incomplete`，`response.status=="incomplete"`，`response.incomplete_details.reason=="max_output_tokens"`；`data: [DONE]` 收尾；`sequence_number` 自 0 递增。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 200 + 唯一 terminal `response.incomplete` + `status=incomplete` + `reason=max_output_tokens` + `[DONE]` + 递增 match。
  - **FAIL**：terminal 为 `completed`、terminal 缺失/重复、`reason` 错、`[DONE]` 缺失。
  - **BLOCKED**：测试代码/断言不可实现——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始 SSE 逐帧（含 terminal 与 `incomplete_details`）、发出命令、exit code、`elapsed`、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。
- **清理与复位**：**无需 teardown**——`store=false`、环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；上游 tier `Worker`（`capabilities.max_output_tokens >= 10`）；自动化入口 [`at_dp_resp_10.py`](../../../../tests/system/api_test_v03/at_dp_resp_10.py)。**不依赖**其它 Case；与 DP-RESP-01（`completed`）互为 terminal 类型对照。
