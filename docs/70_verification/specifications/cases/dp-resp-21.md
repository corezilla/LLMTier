# DP-RESP-21 — 客户端中途断开

- **Case ID**：`DP-RESP-21`
- **标题**：`POST /v1/responses` 客户端在 SSE 发送阶段断开：出口记 `aborted`、无成功终态、许可释放（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**客户端断开契约**：SSE 发送阶段 `BrokenPipeError`/`ConnectionResetError` 被 M001 捕获，记录 trace `aborted`（reason `client disconnected`），不产生"半个成功"，且准入许可被释放。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-DISCONNECT`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；实现 `src/http_api/app.py`（`except (BrokenPipeError, ConnectionResetError): diagnostics.record_trace(request_id, "aborted", {"reason":"client disconnected"}); return`）。**不证明什么**：不证明 `stream_terminate`/`malformed_event` 注入路径（§6，分别属流阶段注入）；不证明账本在 `create()` 返回前已收敛的细节（本 case 只要求无"半个成功"）；不证明答案。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。建议专属实例以避免与其它 case 抢占许可。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier；`depl_b` 已 probe `healthy`。fixture `LLMTierInstance`、`api_client_b`（[§4.4](../llmtier-api-test-specification.md)）。
- **输入与构造**：被测请求（`stream=true`，请求足够长的输出以留出中途断开窗口）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "Count from 1 to 1000."}], "stream": true, "store": false, "max_output_tokens": 2000}
  ```

  断开构造：以 `httpx` 流式读取，读满 **>=1** 个事件（至少 `response.created`）后立即关闭响应/连接（`resp.close()` 或退出 `with` 且中途 break），不读完整流。
- **执行过程（逐步调用）**：
  1. （fixture 前置）启动实例并 probe `depl_b` → `healthy`。
  2. `with api_client_b.stream("POST", "/v1/responses", json=...) as resp:` 断言 `status_code == 200` 与 `text/event-stream`。
  3. 读取至少一个事件后**主动关闭连接**（不读到 terminal）。
  4. 记录本次 `X-Request-ID`（响应头 `X-Request-ID`）。
  5. 以 `admin` 调 `GET /v1/trace/{request_id}`：断言 trace 含 `aborted` 阶段且 `reason=="client disconnected"`（服务端观测；若 trace 视图字段名以实现为准）。
  6. 校验无"半个成功"：本次流中**不出现** terminal（`response.completed`/`response.incomplete`/`response.failed`）与 `[DONE]`（客户端主动截断）。
  7. 紧随其后发一个正常 `POST /v1/responses`，断言可正常准入（许可已释放）并返回 `200` + terminal。
- **重点关注步骤**：① **服务端捕获断开**——必须记录 trace `aborted`（`reason=client disconnected`），而非静默或崩溃；② **无半个成功**——断开后不得把已发事件当完成成功；③ **许可释放**——后续请求可准入（验证 `finally` 释放）；④ **账本已在 `create()` 返回前收敛**——`usage.finish` 早于流发送；⑤ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_21.py`。
- **期望结果与独立 Oracle**：独立 Oracle = 机制 `T-DISCONNECT`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）+ 系统设计 §6（`aborted`、无 terminal、许可释放）。
  - 首响：`200` + `text/event-stream`（在断开前）。
  - 断开后：客户端未收到 terminal/`[DONE]`；服务端 `GET /v1/trace/{request_id}` 记 `aborted`（reason `client disconnected`）。
  - 后续请求：`200` + 唯一 terminal + `[DONE]`（许可未泄漏）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：首响 200 SSE；断开被服务端记为 `aborted`；无半个成功；后续请求正常准入。
  - **FAIL**：服务端未记 `aborted`（静默/崩溃）、把断开当成功、许可未释放致后续请求阻塞/失败。
  - **BLOCKED**：无法稳定在不读满流的情况下断开、trace 视图不可读——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求、首响 status/headers（含 `X-Request-ID`）、已读事件与断开位置、`GET /v1/trace/{request_id}` 的 `aborted`、后续请求响应、发出命令、exit code、环境快照。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。**当前无脚本/artifact**。
- **清理与复位**：无注入/无持久写；断开只影响本连接。专属实例由 fixture `stop()` + `rm -rf` 销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `LLMTierInstance` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`GET /v1/trace/{request_id}`（OBS-REQTRACE-01）；实现 `src/http_api/app.py`；机制 `T-DISCONNECT`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）。**自动化入口 `at_dp_resp_21.py` MISSING（§3.2）**；**不依赖**其它 Case。
