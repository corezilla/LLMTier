# DP-RESP-18 — body 超 2 MB

- **Case ID**：`DP-RESP-18`
- **标题**：`POST /v1/responses` body 超过 2 MB：`413 request_too_large`，读取前拒绝（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**请求体上限制**：`Content-Length > 2 MiB` 时在解析业务体前返回 `413 request_too_large`。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-TOO-LARGE` → wire `code=request_too_large`；实现 `src/http_api/app.py` `_body()`（`if int(Content-Length) > 2 * 1024 * 1024: raise ApiError(413, "request_too_large", "Request body is too large")`，系统设计 §11.1）。**不证明什么**：不证明非法 `Content-Length`（`400 invalid_request`）或非法 JSON（DP-RESP-16）；不证明上游调用。恰好 2 MiB 的边界（`== 2097152` 应受理）作为本 case 的边界子测（见"输入与构造"与"执行过程"）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：`llmtier_b` 可启动且 `GET /healthz` 200。fixture `llmtier_b`、`api_client_b`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 1 provider / 1 deployment / 7 tier。**不需要上游**（在上限检查阶段拒绝）。
- **输入与构造**：构造 `Content-Length` 略超 2 MiB 的请求体（关键：必须设置 `Content-Length`）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  Content-Length: 2097153
  ```

  body 为合法 JSON，但总字节数 **严格大于 `2097152`**（2 MiB）——例如 `2097153` 字节（约 2 MiB + 1 B，用一段 `'a'` 串填充 `input`）；用 `httpx` 的 `content=`（bytes）发送以自动带 `Content-Length`。**边界语义（显式）**：上限判定为 `Content-Length > 2 * 1024 * 1024`，故 `Content-Length == 2097152`（恰好 2 MiB）**不**因本上限被拒、应进入 JSON 解析；`2097153` 起才触发 `413`。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200。
  2. 构造 >2 MiB 的 bytes body，`api_client_b.post("/v1/responses", content=body, headers={"Content-Type":"application/json"})`。
  3. 断言 `status_code == 413`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `error`，断言 `code=="request_too_large"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
  5. 边界子测：构造恰好 2 MiB 的**合法** body，断言不走 413（可为 200 SSE 或业务校验错误，但**不得**是 `request_too_large`）。
- **重点关注步骤**：① **上限在读取前检查**——>2 MiB 直接 413，不解析 JSON；② **必须有 `Content-Length`**——若缺（chunked/未设），`_body()` 读 0 字节，会偏离 413 路径；③ **边界语义**——`>` 2 MiB 拒绝、`==` 2 MiB 允许（`> 2 * 1024 * 1024`）；④ **信封 identity**（5 键、无 `category`）；⑤ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_18.py`。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 / §11.1 `ERR-REQ-TOO-LARGE`。
  - HTTP：`413`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Request body is too large","type":"request_error","code":"request_too_large","param":null,"retryable":false}}`。
  - 无 SSE 帧/`[DONE]`；恰好 2 MiB 时不出现该 code。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：>2 MiB → 413 + `request_too_large` + 非 SSE；边界 2 MiB 不被本上限拒绝。
  - **FAIL**：status/code 错、超限未被拒、边界误拒。
  - **BLOCKED**：测试代码/契约问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 `Content-Length` 与字节数、HTTP status/headers、原始错误信封、边界子测结果、发出命令、exit code、环境快照。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。**当前无脚本/artifact**。
- **清理与复位**：**无需 teardown**——只在上限检查层拒绝；B 类实例整班 `stop()` + `rm -rf`（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；实现 `src/http_api/app.py` `_body()`；错误目录 `ERR-REQ-TOO-LARGE`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8/§11.1）。**自动化入口 `at_dp_resp_18.py` MISSING（§3.2）**；**不依赖**其它 Case。
