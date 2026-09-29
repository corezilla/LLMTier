# DP-RESP-06 — stream=true 唯一受理形态

- **Case ID**：`DP-RESP-06`
- **标题**：`POST /v1/responses` 显式 `stream=true`：受理并返回合法 SSE（唯一受理形态的正向基线）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**唯一受理形态**：`stream=true` + `store=false` 被接受并返回标准 SSE。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；OpenAPI `ResponsesRequest.stream.const=true`。**不证明什么**：不证明事件序列的完整逐帧 identity（DP-RESP-01 承担）、不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）、不证明截断（DP-RESP-10）或异常路径；不证明模型答案。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端，见[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`model="Worker"` 由三选一调度。
- **输入与构造**：固定请求（最小受理形态）：

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
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "store": false,
    "max_output_tokens": 30
  }
  ```

  边界/构造点：显式 `stream=true`；`store=false`；`max_output_tokens=30` 限制流长；不注入故障；其余字段构造与 DP-RESP-01 一致，本 case 只保留 `stream=true` 受理这一 delta。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `status_code == 200` 且 `content-type` 含 `text/event-stream`（受理形态 delta；事件序列完整断言见 DP-RESP-01）。
  4. 同步读取 body，断言含 `event: response.completed`（terminal 存在性）。
  5. 断言出现 `data: [DONE]`（[§4.5](../llmtier-api-test-specification.md)）。
- **重点关注步骤**：① **正向与负向配对**——本 case 与 DP-RESP-02（`stream=false`）/DP-RESP-07（`store=true`）构成受理边界的三联，各自独立执行；② **受理即返回 SSE**——`Content-Type: text/event-stream` 而非错误信封；③ **terminal 存在**——本 case 只断 `response.completed` 存在，逐帧 identity/唯一性/顺序由 DP-RESP-01 承担（不重复其断言）；④ **不把答案文本当 Oracle**。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `stream.const=true` 受理（[§4.5](../llmtier-api-test-specification.md)），不依赖实现答案。事件序列/唯一 terminal/`[DONE]`/usage 的完整判定见 DP-RESP-01；本 case 只断"受理形态"这一前沿。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件：含 `response.created` 与 terminal `response.completed`；`data: [DONE]` 收尾。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 200 + `text/event-stream` + `response.completed` + `[DONE]` match。
  - **FAIL**：status 非 200、无 SSE、`response.completed` 缺失、`[DONE]` 缺失。
  - **BLOCKED**：测试代码/断言不可实现——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 body、HTTP status/headers、原始 SSE、发出命令、exit code、环境快照。manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——`store=false`、环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；上游 tier `Worker`；自动化入口 [`at_dp_resp_06.py`](../../../../tests/system/api_test_v03/at_dp_resp_06.py)。**不依赖**其它 Case；与 DP-RESP-01 共享 SSE 机制但断言范围更窄（受理 + terminal 存在）。
