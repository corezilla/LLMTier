# DP-RESP-25 — 上游契约错误

- **Case ID**：`DP-RESP-25`
- **标题**：`POST /v1/responses` 上游响应无法归一：`502 provider_contract_error`（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**上游响应违反 Responses SSE 契约**的归一：无法从上游响应提取合法 terminal 时，适配层以 `502 provider_contract_error` 拒绝。被测端点/规则：`POST /v1/responses`；需求 `R-INF-05`；设计验证项 `VRC-INF-001`；错误目录 `ERR-PROVIDER-CONTRACT` → wire `code=provider_contract_error`；实现 `src/inference/providers/openai.py`（非 `text/event-stream` → "Provider did not return Responses SSE"；多个 terminal → "more than one terminal"；无合法 terminal → "no valid terminal response"；`status` 与 terminal 类型不一致 → "terminal event and response status disagree"）。**不证明什么**：不证明上游非成功 HTTP（DP-RESP-23）；不证明真实 5xx/不可达（`provider_unavailable`）；不证明 SSE `malformed_event` 注入路径（§6 流阶段注入）；不证明答案。
- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。需一个**专属**上游 stub（扩展 `tests/fixtures/v03_fake_provider.py` 或等价 fixture），对 `POST /v1/responses` 返回**违反契约**的响应之一。`prov_b.endpoint` 必须是该 stub 的 LAN IP 地址（TS-003，见[§2.7](../llmtier-api-test-specification.md)）。fixture = `LLMTierInstance`、`api_client_b`（[§4.4](../llmtier-api-test-specification.md)）。`depl_b` 已 probe `healthy`（probe 打 `/models`，需返回合法目录）。
- **输入与构造**：被测请求（stub 需被配置为下述任一种契约违规）：

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

  契约违规构造（各子测，逐一独立）：① 上游 `Content-Type: application/json`（非 SSE）；② SSE 含**两个** terminal（`response.completed` ×2）；③ SSE **无任何** terminal（只有 `response.created`）；④ terminal 事件类型为 `response.completed` 但 `response.status=="failed"`（类型与状态不一致）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）启动专属 stub 与实例，probe `depl_b` → `healthy`；确认无启用注入。
  2. 对每个子测配置 stub 使其返回对应契约违规响应。
  3. `POST /v1/responses`（上表 body）→ 断言响应为**普通 JSON 错误信封**（非 SSE）。
  4. 断言 `status_code == 502`；解析 `error`：`code=="provider_contract_error"`、`type=="server_error"`、`retryable is False`、`param is None`，键集恰 5 键。
  5. 断言 `message` 与子测语义一致（如非 SSE / 多 terminal / 无 terminal / status 不一致）。
- **重点关注步骤**：① **契约归一在适配层完成**——不把非法上游响应当成功流出给客户端；② **502 而非 503**——契约错误是 `provider_contract_error`，与 `provider_unavailable`（5xx/不可达）区分；③ **`retryable=false`**（实现默认）；④ **信封 identity**（5 键、`type=server_error`）；⑤ **四个子测各自独立**，不得以一个子测的 PASS 覆盖其它；⑥ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_25.py` 与违规 stub。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-CONTRACT`（不依赖实现答案）。
  - HTTP：`502`；`Content-Type: application/json`；`error.code=="provider_contract_error"`、`type=="server_error"`、`param=null`、`retryable=false`；无 SSE 帧/`[DONE]`。
  - `message` 反映具体违规（非 SSE / 多 terminal / 无 terminal / status 不一致）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：每个子测均 `502` + `provider_contract_error` + `type=server_error` + `retryable=false` + 非 SSE，且 `message` 与违规对应。
  - **FAIL**：status/code 错、把非法上游响应当成功、信封键集错、retryable 错。
  - **BLOCKED**：无法稳定让 stub 产出四类违规之一——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用、无 LAN IP 部署 stub（TS-003）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 `127.0.0.1`/mock 冒充真实上游 endpoint——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 stub 配置（违规形态）、被测请求与原始 502 信封、四个子测结果、发出命令、exit code、环境快照。manifest 与报告落位见 §4.8/§10（本 case `environment:"b"`）。
- **清理与复位**：无注入/无持久写；专属 stub 与实例按 §4.7 整班销毁。
- **依赖**：B 类 fixture `LLMTierInstance` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；违规 stub（扩展 `tests/fixtures/v03_fake_provider.py`）；TS-003 LAN endpoint（[§2.7](../llmtier-api-test-specification.md)）；实现 `src/inference/providers/openai.py`（`complete` 的契约归一）；错误目录 `ERR-PROVIDER-CONTRACT`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_25.py` MISSING（§3.2）**；与 DP-RESP-23（非成功 HTTP）区分。
