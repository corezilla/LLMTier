# DP-RESP-22 — 注入上游 503 → provider_unavailable

- **Case ID**：`DP-RESP-22`
- **标题**：`POST /v1/responses` 注入 `fault_503`：下一次命中 `depl_b` 的推理在 dispatch 上游前被拒，返回 `503 provider_unavailable`（`retryable=true`、`message` 含注入 `error_body`）（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 在 **M006 故障注入（`fault_503`）命中**时的**上游不可用传播契约**。被测端点/规则：先 `PATCH /v1/deployments/{deployment_id}/diagnostics` 写入 `fault_503`；随后命中该 deployment 的 `POST /v1/responses`（`stream=true`）在 dispatch 上游**之前**由 M003 抛出 `ApiError(status=503, code="provider_unavailable", retryable=True)`，入口以**普通 JSON 错误信封**返回（非 `text/event-stream`）。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）；需求 `R-INF-05`；错误目录 `ERR-PROVIDER-UNAVAIL` → wire `code=provider_unavailable`；实现 `src/inference/responses.py`（`kind in ("fault_502","fault_503")` 分支：`code = "provider_failure" if kind=="fault_502" else "provider_unavailable"`）与 `src/libdiag/injections.py`。**不证明什么**：不证明 `fault_502`→`provider_failure`（DP-RESP-11）；不证明真实上游 5xx 的归一（DP-RESP-23）；不证明 SSE 序列（注入在流开始前抛出）；不证明重试/exactly-once（§6）；本 case 的 503 由注入产生，**不是"上游真的不可用"**。
- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。前置 = §2.1 附加（B 类）就绪检查（`llmtier_b` 可启动且 `/healthz` 200）；`_baseline_settings`：`prov_b` + `depl_b` + 7 tier，`llmtier_b` probe `depl_b` 为 `healthy`。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003，见[§2.7](../llmtier-api-test-specification.md)）。fixture = `llmtier_b`、`admin_client_b`、`api_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 1 provider / 1 deployment / 7 tier，且 **`diagnostic_injections` 为空**；7 tier 的 `deployment_ids` 均指向 `depl_b`，故 `model="Senior"` 必然路由到 `depl_b`。
- **输入与构造**：先写注入（admin），再发被测请求（data）。注入写：

  ```http
  PATCH /v1/deployments/depl_b/diagnostics HTTP/1.1
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

  ```json
  {"items": [{"type": "fault_503", "config": {"error_body": "injected upstream unavailable"}, "enabled": true}]}
  ```

  被测请求：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "Hello"}], "stream": true, "store": false}
  ```

  边界/构造点：`type` 必须为白名单枚举 `fault_503`；`config.error_body` 必须为非空字符串（>512B 静默截断）；`enabled=true` 生效；注入按 `(deployment_id, injection_type)` upsert，仅作用 `depl_b`；只写 `fault_503` 一项，不并发写其它类型（尤其不得残留 `fault_502`，否则前置优先级 `fault_502→fault_503` 会命中 502 臂）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200；确认初始 `GET /v1/deployments/depl_b/diagnostics` 为空。
  2. `PATCH /v1/deployments/depl_b/diagnostics`（注入 body）→ 断言 200，解析 JSON 数组存在 `type=="fault_503"` 且 `enabled` 为真。
  3. `POST /v1/responses`（上表 body，`data`）：因注入在 dispatch 前抛出，响应是普通 JSON 错误信封，**不按 SSE 解析**。
  4. 断言 `status_code == 503`。
  5. `err = resp.json()["error"]`：断言 `code=="provider_unavailable"`、`type=="server_error"`（503≥500）、`retryable is True`、`message` 含 `"injected upstream unavailable"`、`param is None`。
  6. （teardown，`finally`）`PATCH .../diagnostics` body `{"items": []}` → 200；再 `GET` 校验无 `enabled=true` 项。
- **重点关注步骤**：① **注入命中证明（cause→effect）**——步骤 2 的 `200 + fault_503 enabled=true` 是因，步骤 4–5 的 `503 + provider_unavailable + message 含注入体` 是果，同 `depl_b` 闭环；② **503 臂锁定**——不得观测到 `fault_502` 的 `502 provider_failure`（若出现说明串了 DP-RESP-11 注入，判 FAIL）；③ **信封 identity**（恰 5 键、无 `category`、`type=server_error`、`retryable=true`）；④ **非 SSE**；⑤ **teardown 完整性**——`finally` 清空并二次校验。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-UNAVAIL`（不依赖实现答案）。
  - 注入写：`PATCH` → `200`，`InjectionView[]` 含 `{type:"fault_503", enabled:true, deployment_id:"depl_b"}`。
  - 被测：HTTP `503`；`Content-Type: application/json`；`{"error":{"message":"injected upstream unavailable","type":"server_error","code":"provider_unavailable","param":null,"retryable":true}}`。
  - teardown：`PATCH {"items":[]}` → 200，随后 `GET` 无启用项。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：注入写 200 且 `fault_503` 生效；被测 `503` + `provider_unavailable` + `type=server_error` + `retryable=true` + `message` 含 `error_body`；teardown 清空。
  - **FAIL**：status 非 503（含 502 `provider_failure`）、`code`/`type`/`retryable`/`message` 错、注入写未生效、teardown 未清空。
  - **BLOCKED**：注入写 API 不可用、注入无法命中——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP（TS-003）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：注入未命中却按行为判定、或 `monkeypatch` 端点伪造 503——见[测试设计 §9](../llmtier-api-test-specification.md)（§8.2 要求命中证明）。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存注入写/清空（`PATCH` body + `200` + 空数组）、被测请求与原始 503 信封、teardown 二次 `GET`、发出命令、exit code、环境快照（`/healthz` + 注入前/后 `GET .../diagnostics`）；可选 trace（`usage.source=="injected"`）。manifest 与报告落位见 §4.8/§10（本 case `environment:"b"`）。
- **清理与复位**：**必须 teardown（`finally`）**——`PATCH /v1/deployments/depl_b/diagnostics {"items":[]}` 清空注入后 `GET` 校验；不修改 `prov_b`/`depl_b`；不删除既有资源。B 类实例按 §4.7 整班销毁。清空失败须报错，不得把启用注入留给后续 Case。
- **依赖**：`OBS-DEPL-02`（注入写机制，[§3.2](../llmtier-api-test-specification.md)）；B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；实现 `src/libdiag/injections.py`、`src/inference/responses.py`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）；错误目录 `ERR-PROVIDER-UNAVAIL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_22.py` MISSING（§3.2）**；与 DP-RESP-11 互补。
