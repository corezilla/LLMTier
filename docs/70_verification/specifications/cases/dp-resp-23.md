# DP-RESP-23 — 上游非成功 HTTP → provider_error

- **Case ID**：`DP-RESP-23`
- **标题**：`POST /v1/responses` 上游返回非成功 HTTP（4xx）：沿用非 5xx 状态并归一为 `provider_error`（**MISSING** 自动化；5xx 分支为 `provider_unavailable`，见偏差）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**真实上游非成功 HTTP** 的错误归一契约。被测端点/规则：`POST /v1/responses`；需求 `R-INF-05`；错误目录 `ERR-PROVIDER-FAIL` → wire `code=provider_error`；实现 `src/inference/providers/openai.py`（`except urllib.error.HTTPError as exc:` — `if exc.code >= 500: raise ApiError(503, "provider_unavailable", ..., retryable=True)`；否则 `raise ApiError(exc.code, "provider_error", f"Provider returned HTTP {exc.code}", retryable=exc.code in {408,429})`）。**不证明什么**：不证明注入类故障（DP-RESP-11/22，`fault_502`/`fault_503` 是 M006 注入，非真实上游 HTTP）；不证明上游不可达/超时（亦归一 `provider_unavailable`）；不证明上游契约异常（DP-RESP-25，`provider_contract_error`）；不证明答案。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。需一个**专属**上游 stub（扩展 `tests/fixtures/v03_fake_provider.py` 或等价 fixture），使其对 `POST /v1/responses` 返回预置的 **4xx**（如 `422` 或 `404`）且 body 非 SSE。`prov_b.endpoint` 必须是该 stub 的 LAN IP 地址（TS-003，[§2.7](../llmtier-api-test-specification.md)）。fixture `LLMTierInstance`、`api_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 1 provider / 1 deployment / 7 tier，`depl_b` 已 probe `healthy`（probe 打 stub 的 `/models`，需返回合法目录）。
- **输入与构造**：stub 配置为对 `/v1/responses` 返回 `422`（不创建 provider conversation 状态）。被测请求：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
  ```

  边界/构造点：必须区分"真实上游 4xx"与"注入 4xx"——本 case **不写任何 `diagnostic_injections`**；stub 通过 `prov_b.endpoint` 指向的独立进程返回 4xx；`422` 的 `type` 应为 `request_error`（<500），`retryable` 仅当 `exc.code in {408,429}` 才为真（422 ⇒ false）。可加子测：stub 返回 `429` → status 429 + `provider_error` + `retryable=true`。
- **执行过程（逐步调用）**：
  1. （fixture 前置）启动专属 stub 与实例，probe `depl_b` → `healthy`；确认无启用注入。
  2. 配置 stub 使其 `/v1/responses` 返回 `422`。
  3. `POST /v1/responses`（上表 body）→ 断言响应为**普通 JSON 错误信封**（非 SSE）。
  4. 断言 `status_code == 422`（**沿用**上游非 5xx 状态）。
  5. 解析 `error`：`code=="provider_error"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
  6. 子测（可选）：stub 改返回 `429`，断言 `status==429` + `provider_error` + `retryable is True`。
  7. 子测（对照）：stub 改返回 `503`，断言归一为 `503 provider_unavailable` + `retryable=true`（证明 5xx 分支：本条为**真实上游** 5xx；DP-RESP-22 是 M006 **注入** 503，两者来源不同）。
- **重点关注步骤**：① **4xx 沿用原状态**——非 5xx 的 `exc.code` 作为 HTTP status，`code=provider_error`；② **5xx 分支不同**——真实上游 5xx 归一为 `503 provider_unavailable`（**偏差**：§3.2 标题写"上游 4xx/5xx → provider_error"，而实现 `openai.py` 对 5xx 返回 `provider_unavailable`；以代码为准并登记）；③ **`retryable` 规则**——仅 `{408,429}` 为真；④ **信封 identity**（5 键、无 `category`）；⑤ **无注入**——不得用 `PATCH .../diagnostics` 伪造（注入是 DP-RESP-11/22 的来源）；⑥ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_23.py` 与 4xx stub。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-FAIL`（不依赖实现答案）。
  - 4xx 子测：HTTP `422`（或所配 4xx）；`Content-Type: application/json`；`{"error":{"message":"Provider returned HTTP 422","type":"request_error","code":"provider_error","param":null,"retryable":false}}`；无 SSE。
  - 429 子测：`429` + `provider_error` + `retryable=true`。
  - 5xx 对照：`503` + `provider_unavailable` + `retryable=true`（与 §3.2 标题的偏差按代码登记）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：4xx → 沿用状态 + `provider_error` + `type=request_error` + `retryable` 符合 `{408,429}` 规则；无 SSE。
  - **FAIL**：status/code 错（如把 4xx 未保留或写成 `provider_unavailable`）、`retryable` 错、返回 SSE、信封键集错。
  - **BLOCKED**：无法稳定让 stub 返回目标 4xx/5xx、4xx stub 不可实现——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用、无 LAN IP 部署 stub（TS-003）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 `127.0.0.1`/mock 冒充真实上游 endpoint、或注入未命中却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 stub 配置（返回码）、被测请求与原始错误信封、5xx 对照、发出命令、exit code、环境快照。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。**当前无脚本/artifact**。
- **清理与复位**：无注入/无持久写；专属 stub 与实例由 fixture 销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `LLMTierInstance` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；4xx/5xx stub（扩展 `tests/fixtures/v03_fake_provider.py`）；TS-003 LAN endpoint（[§2.7](../llmtier-api-test-specification.md)）；实现 `src/inference/providers/openai.py`；错误目录 `ERR-PROVIDER-FAIL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_23.py` MISSING（§3.2）**；与 DP-RESP-22（注入 5xx）/DP-RESP-25（契约错误）区分。
