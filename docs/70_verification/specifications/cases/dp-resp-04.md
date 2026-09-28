# DP-RESP-04 — tools 透传

- **Case ID**：`DP-RESP-04`
- **标题**：`POST /v1/responses` 携带合法 `tools`：被受理并透传，SSE 结构完整。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**合法 `tools` 数组**的受理与透传契约：当所选 model 的能力声明 `tools=true` 时，`tools` 作为可选字段被接受并转发给上游，不因出现 `tools` 而拒绝。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-TOOLS`；字段约束来自 OpenAPI `ResponsesRequest.tools`（`FunctionTool[]`）与实现 `src/inference/responses.py`（`ALLOWED_FIELDS` 含 `tools`；`require(caps.get("tools") ...)` 仅在能力为 `false` 时拒绝）。**不证明什么**：不证明上游是否真正调用工具（`function_call_arguments.*` 事件属上游行为，非 LLMTier 契约）；不证明工具执行结果；不证明 `tools` 语义正确性；不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；所选 tier 的 `capabilities.tools` 必须为真，否则按 DP-RESP-04 的负向变体观测 `400 unsupported_request`。
- **输入与构造**：固定请求（`tools` 含单个合法 `function` 工具）：

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
    "input": [{"role": "user", "content": "What's the weather in SF?"}],
    "stream": true,
    "store": false,
    "tools": [
      {
        "type": "function",
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
      }
    ],
    "max_output_tokens": 100
  }
  ```

  边界/构造点：`tools[].type` 为 `function`；能力门（`caps.tools`）必须为真；`max_output_tokens=100` 限制流长；`store=false` 无副作用。**不构造** `function_call` 预期——上游是否调用工具不进入 Oracle。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body），同步读取完整 SSE（`resp = api_client.post(...)`）。
  3. 断言 `status_code == 200` 且 `Content-Type` 含 `text/event-stream`。
  4. 断言 body 文本含 `event: response.created` 与 `event: response.completed`（终止事件存在）。
  5. 逐帧解析确认恰好一个 terminal（`response.completed`），`sequence_number` 自 0 递增；`data: [DONE]` 出现。
  6. （可选交叉核对）若上游返回 `function_call`，仅记录 `response.output_item.done.item.type=="function_call"`，**不**作为 PASS/FAIL 依据。
- **重点关注步骤**：① **受理而非拒绝**——`tools` 出现在 `ALLOWED_FIELDS`，只有 `caps.tools is False` 才 `400 unsupported_request`（`param="tools"`）；本 case 的前提是该 tier 能力为真；② **透传不解释**——LLMTier 只转发 `tools`，不对工具语义/调用结果负责；③ **terminal 唯一 + `[DONE]`**（[§4.5](../llmtier-api-test-specification.md)）；④ **不把上游工具调用当契约**——禁止以"出现了 `function_call_arguments` 事件"作为 PASS 条件。
- **期望结果与独立 Oracle**：独立 Oracle = Responses 请求受理 + 标准 SSE 外壳（[§4.5](../llmtier-api-test-specification.md)），与上游是否调用工具无关。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件序列含 `response.created`、唯一 terminal `response.completed`；`data: [DONE]` 收尾；`sequence_number` 自 0 递增。
  - 反向负向（同 case 可选观测）：若所选 tier `caps.tools is False`，则期望 `400` + `error.code=="unsupported_request"` + `error.param=="tools"`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 200 + SSE 外壳（created/completed/唯一 terminal/`[DONE]`/递增）match；不要求出现工具调用事件。
  - **FAIL**：status 非 200（能力为真时应受理）、SSE 序列断裂、terminal 缺失/重复、`[DONE]` 缺失。
  - **BLOCKED**：测试代码/断言不可实现——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body（含 `tools`）、HTTP status/headers、原始 SSE 逐帧、发出命令、exit code、环境快照。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。
- **清理与复位**：**无需 teardown**——`store=false`、环境 A 无状态，不创建/修改资源；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；`tools=true` 的 responses-capable tier；自动化入口 [`at_dp_resp_04.py`](../../../../tests/system/api_test_v03/at_dp_resp_04.py)。**不依赖**其它 Case；能力门负向由 DP-RESP-04 的可选观测记录，不并入 PASS 条件。
