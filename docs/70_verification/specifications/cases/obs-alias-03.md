# OBS-ALIAS-03 — 别名 trace

- **Case ID**：`OBS-ALIAS-03`
- **标题**：`/tier/admin/v1/trace/{request_id}` 与 `/v1/trace/{request_id}` 的 GET 由同一 handler 服务：status 与响应体逐字节等价（含未知 id 的 404 信封）。
- **目的（被测契约）**：验证单请求 trace 别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/trace/{request_id}` 是 `/v1/trace/{request_id}` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/trace/{request_id}": "/v1/trace/{request_id}"`），同一 handler、相同 `TraceView` 形状、相同 `admin` 鉴权与相同错误语义（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.trace`）；body 应逐字节等价（[测试设计 §4.10](../llmtier-api-test-specification.md)）；错误在扁平/别名上亦逐字节等价（[测试设计 §4.6](../llmtier-api-test-specification.md)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`TraceView`、`NotFound`）。**不证明什么**：不证明全生命周期内容（OBS-REQTRACE-01）、不证明未知 id 404 语义本身（OBS-REQTRACE-02）、不证明角色负向（OBS-REQTRACE-03、AUTH-08）、不证明其它别名（OBS-ALIAS-01/02/04/05/06）。**契约一致性警示（须登记）**：`_UnavailableDiagnostics.trace` 对任意 id 返回 `200` 空视图，等价比对在降级实例下仍可做但语义受限（判 BLOCKED/SKIP）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项**就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 tier。本 case 纯 GET，初态即终态。
- **输入与构造**：
  - **正向（若有数据）**：经 `GET /v1/diagnostics/traces?limit=1`（`admin_client`）取一个真实 `request_id`，分别 `GET /v1/trace/<id>` 与 `GET /tier/admin/v1/trace/<id>`。
  - **404 等价（确定性，无需数据）**：`GET /v1/trace/req_does_not_exist` 与 `GET /tier/admin/v1/trace/req_does_not_exist`。
  同凭据。边界点：两路径必须查**同一 id**；`X-Request-ID` 每次不同，**不参与**比较，也不列入 Oracle；404 路径用于保证即使 trace 列表为空也能完成等价判定。
- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics/traces?limit=1`（`admin_client`）→ 若 `items` 非空取 `request_id`；空则可选。
  2. **404 等价（必做）**：`GET /v1/trace/req_does_not_exist` 与别名同 id → 断言两 `status == 404` 且 `resp.content` **逐字节相等**，`code=="not_found"`。
  3. **正向等价（有 id 时）**：对 `request_id` 分别请求两路径 → 断言两 `status == 200` 且 `resp.content` **逐字节相等**；均为合法 `TraceView`（键集恰 `{request_id, correlation_id, stages, snapshot, usage}`）。
  4. 断言 `status` 与 body 在两路径上一致；仅 header 中的 `X-Request-ID` 不同（不参与断言）。
- **重点关注步骤**：① **同 id 比较**——两路径必须查同一 `request_id`，否则 body 本可不同。② **逐字节 body 等价**——比较 `resp.content`。③ **错误路径也等价**——404 信封在扁平/别名上应逐字节相同（本 case 用 404 作确定性锚点）。④ **只比 body**——`X-Request-ID` 不参与、不列入 Oracle。⑤ **鉴权等价**——都需 `admin`（本 case 正向；负向 AUTH-08）。⑥ **数据不足处理**——无真实 trace 时以 404 等价完成判定，不算 FAIL（但报告须说明未覆盖正向）。⑦ **降级/存储**——降级实例两路径同样返回 200 空视图（等价成立但语义受限，判 BLOCKED/SKIP）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_alias_03.py`。
- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `TraceView`/`NotFound` wire 形态。
  - 404 路径：两路径 `404`，`body_flat == body_alias`（逐字节），`code=="not_found"`。
  - 正向路径（有 id）：两路径 `200`，`body_flat == body_alias`（逐字节），均为合法 `TraceView`。
  - **fail-open**：降级实例两路径同样 200 空视图（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：同一 id 下两路径 status 相同且 body 逐字节相等（404 路径必做；有数据时 200 路径亦做）。
  - **FAIL**：status/body 不等价、别名 404（端点缺失）或错误 code 不同。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存两路径 404 响应与逐字节对比、正向对比（若有）、命令/exit code/`elapsed`、环境快照。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/trace/...` 分支）。自动化入口 `at_obs_alias_03.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-REQTRACE-01/02（内容/404）、AUTH-08 语义相邻，与其它别名并列但各自独立执行。
