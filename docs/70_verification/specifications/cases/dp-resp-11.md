# DP-RESP-11 — 注入上游 502 → provider_failure

- **Case ID**：`DP-RESP-11`
- **标题**：`POST /v1/responses` 注入 `fault_502`：下一次命中 `depl_b` 的推理在 dispatch 上游前被拒，返回 `502 provider_failure`（`retryable=true`、`message` 含注入 `error_body`）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 在 **M006 故障注入（`fault_502`）命中**时的**上游故障传播契约**。被测端点/规则：先 `PATCH /v1/deployments/{deployment_id}/diagnostics` 写入 `fault_502`；随后命中该 deployment 的 `POST /v1/responses`（`stream=true`）在 dispatch 上游**之前**由 M003 抛出 `ApiError(status=502, code="provider_failure", retryable=True)`，入口以**普通 JSON 错误信封**返回（不是 `text/event-stream`）。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（见[observability 机制](../../../20_system_design/mechanisms/observability.md)）；错误目录 `ERR-PROVIDER-INJECTED` → wire `code=provider_failure`（系统设计 §7.8，见[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；实现见 `src/inference/responses.py` 的 dispatch 前注入分支与 `src/libdiag/injections.py` 的注入校验/优先级。**不证明什么**：不证明真实上游 5xx 的归一（DP-RESP-23 / `ERR-PROVIDER-FAIL`）与 `fault_503`→`provider_unavailable` 路径（DP-RESP-22 / `ERR-PROVIDER-UNAVAIL`）；不证明 SSE 事件序列/terminal/`[DONE]`（注入在流开始前抛出，响应不是 SSE，见 DP-RESP-01）；不证明重试或 exactly-once（标准 client 重试语义见[测试设计 §6](../llmtier-api-test-specification.md)）；不证明模型答案或上游真实调用——本 case 的 502 由注入产生，**不是"模型失败"**。
- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。前置 = §2.1 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier，`llmtier_b` probe `depl_b` 为 `healthy`（否则 BLOCKED/SKIP）。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003，见[测试设计 §2.7](../llmtier-api-test-specification.md)）。fixture = `llmtier_b`、`admin_client_b`（注入写/读）、`api_client_b`（Data Plane），见[测试设计 §4.4](../llmtier-api-test-specification.md)。初始状态 = 1 provider（`prov_b`）/ 1 deployment（`depl_b`）/ 7 fixed tier，且 **`diagnostic_injections` 为空（无任何启用注入）**；7 个 fixed tier 的 `deployment_ids` 均指向 `depl_b`，故 `model="Senior"` 必然路由到 `depl_b`。
- **输入与构造**：先写注入（admin 面），再发被测请求（data 面）。注入写请求：

  ```http
  PATCH /v1/deployments/depl_b/diagnostics HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

  ```json
  {
    "items": [
      {"type": "fault_502", "config": {"error_body": "injected upstream failure"}, "enabled": true}
    ]
  }
  ```

  被测请求：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

  ```json
  {
    "model": "Senior",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "store": false
  }
  ```

  边界/构造点：`type` 必须为白名单枚举 `fault_502`（`_TYPES`）；`config.error_body` 必须为非空字符串（>512B 按 UTF-8 静默截断到 512B；空串/非字符串 → 400 `invalid_injection`）；`enabled=true` 才生效；`stream=true` 且 `store=false` 是唯一受理形态（DP-RESP-06/07）；`model="Senior"` 指向唯一 deployment `depl_b`。注入按 `(deployment_id, injection_type)` upsert，仅作用于 `depl_b`；本 case 只写 `fault_502` 一项，不并发写其它类型。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200，`_probe_deployment(depl_b)` 断言 `healthy`；确认初始 `GET /v1/deployments/depl_b/diagnostics` 为空。
  2. `PATCH /v1/deployments/depl_b/diagnostics`（注入 body，`admin_client_b`）→ 断言 `status_code == 200`；解析 JSON 数组，断言存在 `type == "fault_502"` 且 `enabled` 为真的项（写入并生效）。
  3. 以 `Bearer dev-data` 建 client（`base_url=llmtier_b.base_url`，`timeout=httpx.Timeout(30.0, connect=5.0)`），`POST /v1/responses`（上表 body）。因注入在 dispatch 之前抛出，响应是**普通 JSON 错误信封**而非 SSE 流；**不按 SSE 解析**。
  4. 断言 `resp.status_code == 502`。
  5. `err = resp.json()["error"]`：断言 `err["code"] == "provider_failure"`、`err["retryable"] is True`、`err["message"]` 含注入的 `error_body`（`"injected upstream failure"`）；并核对 `err["type"] == "server_error"`、`err["param"] is None`。
  6. （teardown，`finally` 内）`PATCH /v1/deployments/depl_b/diagnostics` body `{"items": []}` → 断言 200；再 `GET` 同路径 → 断言 200 且所有项 `enabled` 均为假（数组为空）；确认 `prov_b.endpoint` 未被改动。
- **重点关注步骤**：① **注入命中证明（cause）**——不是"模型失败"也不是"恰好返回 502"。步骤 2 的 `200 + fault_502 enabled=true` 是**因**，步骤 4–5 的 `502 + provider_failure + message 含注入 error_body` 是**果**；两者同 deployment（`depl_b`）闭环。按[测试设计 §6/§8.2](../llmtier-api-test-specification.md)，注入 Case 必须**证明命中**（响应状态/错误码，或 trace `source=injected`）——脚本当前以"status+code+retryable+message"证明，未显式抓 `request_id` 查 `GET /v1/trace/{request_id}` 的 `usage.source=="injected"`（INV-3），加强证据时须补此项，否则仅以响应证据成立。② **502 vs 503 的区分**——本 case 严格锁定 `fault_502` 臂，必须观测到 **502 + `provider_failure`**；若观测到 **503 + `provider_unavailable`**，说明生效的是 `fault_503`（串了 DP-RESP-22 的注入），判 FAIL。注入类型→错误码/状态的映射与前置优先级见[测试设计 §4](../llmtier-api-test-specification.md) 与 [observability 机制](../../../20_system_design/mechanisms/observability.md)，本文不重复实现细节。③ **错误信封 identity**——恰 5 键 `{message,type,code,param,retryable}`（无 `category`），`type` 由状态导出（502≥500 ⇒ `server_error`），`retryable=true`；缺键/多键或 `type` 错即 FAIL。④ **非 SSE**——入口在 `create()` 抛 `ApiError` 时返回 `_json(status, envelope)`（`src/http_api/app.py`），不得把响应当 `text/event-stream` 吞掉或解析。⑤ **message 携带注入体**——`"injected upstream failure"` 与写入的 `error_body` 一致，是把响应与注入配置绑定的强证据。⑥ **teardown 完整性**——`finally` 中 `items:[]` 清空并二次 `GET` 校验为空；**绝不残留** `prov_b.endpoint` 被指向死端口（本设计走真实注入 API，不再 monkeypatch endpoint）；清空失败必须报错，不能把启用注入留给同 session 的后续 Case。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` 契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）+ 系统设计 §7.8 `ERR-PROVIDER-INJECTED`（**不依赖实现的"答案内容"**）。
  - 注入写：`PATCH` → `200`，body 为 `InjectionView[]`，含 `{type:"fault_502", enabled:true, deployment_id:"depl_b"}`。
  - 被测响应：HTTP `502`；`Content-Type: application/json`（错误信封，非 SSE）；body `{"error":{"message":"injected upstream failure","type":"server_error","code":"provider_failure","param":null,"retryable":true}}`。
  - teardown：`PATCH {"items":[]}` → `200`；随后 `GET` → `200` 且 `InjectionView[]` 中无 `enabled=true` 项（数组为空）。
  - 可选独立交叉核对（非脚本 oracle 的充分条件）：`GET /v1/trace/{request_id}` 的 `usage.source == "injected"`（机制 INV-3），用于证明账本标注命中。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：注入写 `200` 且 `fault_502` 生效；被测响应 `502` + `error.code=="provider_failure"` + `type=="server_error"` + `retryable is True` + `message` 含 `error_body`；teardown `items:[]` 生效且 `GET` 校验为空。
  - **FAIL**：任一断言不符——status 非 502（含 503 `provider_unavailable`）、`code`/`type`/`retryable`/`message` 错、注入写未生效、或 teardown 未清空（注入已命中但行为不符时按 §9 判 FAIL）。
  - **BLOCKED**：无法执行/无法判定且可重试——注入写 API 不可用、校验逻辑/断言不可实现、注入无法命中（见[测试设计 §9](../llmtier-api-test-specification.md)）。
  - **SKIP**：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP 可用（TS-003）、依赖 fixture 未满足（见[测试设计 §9](../llmtier-api-test-specification.md)）。
  - **INVALID**：注入未命中却按行为判定、或以替代路径冒充真实路径——例如用 `127.0.0.1`/mock 当上游 endpoint、或 `monkeypatch` 把 `prov_b.endpoint` 指向死端口伪造 502，而非走真实 `PATCH` 注入（见[测试设计 §9](../llmtier-api-test-specification.md)；§8.2 要求命中证明）。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存注入写请求/响应（`PATCH` body + `200` + `InjectionView[]`）、被测请求与原始响应（HTTP status/headers/body 错误信封，脱敏后）、teardown 的 `PATCH items:[]` 与随后 `GET` 空数组、`elapsed`、发出命令、exit code、环境快照（`/healthz` + 注入前/后 `GET /deployments/depl_b/diagnostics`）；可选 trace 证据（`GET /v1/trace/{request_id}` 的 `usage.source=injected`）。注意：现有 [`at_dp_resp_11.py`](../../../../tests/system/api_test_v03/at_dp_resp_11.py) 未自建 artifact 目录/manifest，须由 runner/report 层按 §4.8 补齐后方可判本 Case PASS。manifest 与报告落位见 §4.8/§10（本 case `environment:"b"`）。
- **清理与复位**：**必须 teardown（`finally` 强制）**——`PATCH /v1/deployments/depl_b/diagnostics` body `{"items":[]}` 清空本 deployment 的全部注入，随后 `GET` 校验 `InjectionView[]` 无启用项；不修改 `prov_b`/`depl_b` 配置，**不重指 `prov_b.endpoint`**（本 case 只写注入，provider endpoint 始终指向 LAN fake provider）；不删除任何既有资源或用户 usage。B 类实例按 §4.7 整班销毁。离开前确认无未清空的注入项；若清空失败，保留证据并按 §9 处理，不得把启用注入留给后续 Case。
- **依赖**：`OBS-DEPL-02`（`PATCH /v1/deployments/{id}/diagnostics` 写入注入，本 case 的注入写即其机制；[测试设计 §3.2](../llmtier-api-test-specification.md)）；B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b` 与 `provider_endpoint_b`（LAN fake provider，TS-003）（[测试设计 §4.4](../llmtier-api-test-specification.md)）；自动化入口 [`at_dp_resp_11.py`](../../../../tests/system/api_test_v03/at_dp_resp_11.py)；错误目录 `ERR-PROVIDER-INJECTED`（系统设计 §7.8）与实现 `src/libdiag/injections.py` / `src/inference/responses.py`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）。**不依赖**其它 Case；与 DP-RESP-22（`fault_503`→`provider_unavailable`）互补但各自独立执行，与 DP-RESP-23（真实上游非成功 HTTP）区分注入/真实两类来源。
