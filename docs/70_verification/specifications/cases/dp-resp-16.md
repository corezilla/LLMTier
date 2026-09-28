# DP-RESP-16 — 非法 JSON body

- **Case ID**：`DP-RESP-16`
- **标题**：`POST /v1/responses` 发送非法 JSON body：`400 invalid_json`，dispatch 前拒绝（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**请求体解析契约**：body 不是合法 JSON（或不是 JSON 对象）时，M001 在业务校验/dispatch 前返回 `400 invalid_json`。被测端点/规则：`POST /v1/responses`；需求 `LT-FUN-001`；错误目录 `ERR-REQ-JSON` → wire `code=invalid_json`；实现 `src/http_api/app.py` `_body()`（`json.loads` 失败 → `ApiError(400, "invalid_json", "Request body is not valid JSON")`；解析成功但非对象 → `ApiError(400, "invalid_json", "Request body must be a JSON object")`）。**不证明什么**：不证明 schema 级字段校验（缺 `model` 见 DP-RESP-08；未知字段见 DP-RESP-12..15）；不证明 `Content-Length` 非法（`400 invalid_request`）或超限（DP-RESP-18）；不证明上游调用。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。执行前必须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：`llmtier_b` 可启动且 `GET /healthz` 200（`_baseline_settings`：`prov_b` + `depl_b` + 7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b`、`api_client_b`（Bearer `dev-data`）。初始状态 = 1 provider / 1 deployment / 7 tier。**不需要上游**（在解析阶段拒绝，早于路由）。
- **输入与构造**：固定请求（原始 body 为非法 JSON 字节）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```
  {"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false,
  ```

  （末行截断，缺右花括号，非法 JSON）。边界构造：另测 `[1,2,3]`（合法 JSON 但非对象）→ 同样 `invalid_json`。请求必须带 `Content-Length`（`httpx` 以 `content=` 发送时自动设置），否则 `_body()` 按 0 字节读成 `{}`。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200。
  2. 以 `api_client_b` 发送原始非法 JSON：`client.post("/v1/responses", content=b'{...', headers={"Content-Type":"application/json"})`。
  3. 断言 `status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `error`，断言 `code=="invalid_json"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键（[§4.6](../llmtier-api-test-specification.md)）。
  5. 边界：以 `content=b'[1,2,3]'` 重发，断言同样 `400 invalid_json`（"must be a JSON object"）。
- **重点关注步骤**：① **解析先于业务校验**——非法 JSON 不得报 `invalid_request`/`unsupported_request`；② **`Content-Length` 必须存在**——否则 `_body()` 读 0 字节变 `{}`，会错误地走到字段齐备性校验；③ **信封 identity**（5 键、无 `category`）；④ **非 SSE**；⑤ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_16.py` 才能执行。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-REQ-JSON`（不依赖实现答案）。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Request body is not valid JSON","type":"request_error","code":"invalid_json","param":null,"retryable":false}}`；`[1,2,3]` 时 `message="Request body must be a JSON object"`。
  - 无 SSE 帧/`[DONE]`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=invalid_json` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE。
  - **FAIL**：status/code 错、报业务校验错误、返回 200/SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；须先实现入口，未执行按 §9 记 `NOT_RUN`（MISSING ≠ 跳过，是缺口）。
- **证据与 Run**：保存原始请求字节、`Content-Length`、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。**当前无脚本/artifact**，实现入口后按 §4.8/§10 补齐。
- **清理与复位**：**无需 teardown**——只在解析层拒绝，不创建/修改资源；B 类实例整班结束由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `rm -rf` 临时目录销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；实现 `src/http_api/app.py` `_body()`；错误目录 `ERR-REQ-JSON`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）；需求 `LT-FUN-001`。**自动化入口 `at_dp_resp_16.py` MISSING（§3.2）**，本 case 不声称已实现。**不依赖**其它 Case。
