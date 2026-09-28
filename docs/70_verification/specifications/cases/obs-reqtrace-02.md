# OBS-REQTRACE-02 — 未知 request_id

- **Case ID**：`OBS-REQTRACE-02`
- **标题**：`GET /v1/trace/{request_id}` 查询不存在的 `request_id`：HTTP 404 `not_found`，不返回空 `TraceView` 的 200。
- **目的（被测契约）**：验证单请求 trace 的**资源存在性负向契约**。被测端点/规则：`GET /v1/trace/{request_id}`，`TraceDiagnostics.trace` 在 `_trace_view` 无任何 `trace_events` 阶段时抛 `ApiError(404, "not_found", "No trace for this request_id")`（[`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)）；不存在 id 必须 404，**不得**以 `200 + {stages:[]}` 冒充；认证 `admin`；统一信封 5 键（`type="request_error"`，`retryable=false`）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-TRACE-QUERY` "`trace` 无记录 → `ERR-NOTFOUND`（404）"）；错误目录 `ERR-NOTFOUND` → `not_found`（[测试设计 §11.1](../llmtier-api-test-specification.md) `ERR-NOTFOUND → ...、OBS-REQTRACE-02`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`NotFound`，`TraceView.request_id maxLength:128`）。**不证明什么**：不证明已知 id 的全生命周期（OBS-REQTRACE-01）、不证明 data token 403（OBS-REQTRACE-03）、不证明注入命中、不证明别名等价（OBS-ALIAS-03）。**契约一致性警示（须登记）**：`_UnavailableDiagnostics.trace` 对**任意** id 返回 `200 + {stages:[]}`（fail-open），与健康实现的 404 语义不同；本 case 的 Oracle 以**健康诊断服务**为准。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项**就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 tier；本 case 纯 GET、零写入，初态即终态。为避免与真实 id 冲突，使用带唯一后缀的 id。
- **输入与构造**：固定请求（无 body）：
  - `GET /v1/trace/req_does_not_exist_<uuid>`、`Authorization: Bearer dev-admin`
  - 形态合法的 `GET /v1/trace/req_deadbeef0000000000000000000000`
  - 边界：`GET /v1/trace/x`（短 id）；`GET /v1/trace/<129 字符>`（超 openapi `maxLength:128`，观察是否 404/400，作为边界记录）

  边界点：这些 id **在库中无任何 `trace_events`**；不制造该 id 的任何请求；不构造非法 body（GET 无 body）。
- **执行过程（逐步调用）**：
  1. `GET /v1/trace/req_does_not_exist_<uuid>`（`admin_client`）→ 记录 status/body。
  2. 断言 `resp.status_code == 404`；`err["code"]=="not_found"`、`err["type"]=="request_error"`、`err["retryable"] is False`、键集恰 5。
  3. 断言 **不得** 返回 `200 + {stages:[]}`（空 trace 冒充存在）。
  4. 对另外两个边界 id 重复步骤 1–3（超长 id 的 400/404 记录并说明，不作为 FAIL 依据）。
  5. （对照，可选）取一条真实 `request_id`（经 `GET /v1/diagnostics/traces?limit=1`）→ 断言 `200`，证明端点本体可用（排除"端点整体坏"被误判为 404）。
- **重点关注步骤**：① **不得空 stages 冒充**——最危险的误判是把 `200 + {stages:[]}` 当"存在但无阶段"；404 才是契约。② **code 精确**——`not_found`（非 `model_not_found`/`invalid_request`）。③ **错误信封 identity**——恰 5 键、`type=request_error`。④ **id 唯一性**——使用不会在库中出现的 id，避免与真实请求冲突造成假 200。⑤ **超长 id 边界**——openapi `maxLength:128`；若实现返回 404（未校验长度）记录为边界说明，不判 FAIL（除非契约要求 400，当前未声明）。⑥ **降级差异**——`_UnavailableDiagnostics` 对任意 id 返回 200 空视图；执行时须确认诊断服务健康（`GET /v1/diagnostics` 200 且非降级默认特征），降级下判 BLOCKED/SKIP。⑦ **零副作用**——404 不写库。⑧ **存储**——`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_reqtrace_02.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `NotFound`（`ErrorEnvelope`）+ 机制 §5.1 `IF-OBS-TRACE-QUERY` 404 语义。
  - 每个未知 id：HTTP `404`；`Content-Type: application/json`；body `{"error":{"message":"No trace for this request_id","type":"request_error","code":"not_found","param":<string|null>,"retryable":false}}`（恰 5 键；`message` 措辞以实现为准，仅断言 code/type）。
  - 对照：真实 id → `200 TraceView`。
  - **fail-open**：降级实例 `200 + {stages:[]}` 与健康 404 语义不同；无法证明契约时判 **BLOCKED/SKIP**；健康实例返回 200 空视图或非 `not_found` → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：未知 id 均 `404 + not_found + type=request_error + retryable=false`；无空 stages 冒充；对照 200 正确。
  - **FAIL**：未知 id 返回 `200`（含空视图）或其他 code。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正提交未知 id 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存每个未知 id 的原始 404 信封、超长 id 边界、正相对照、命令/exit code/`elapsed`、环境快照。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需 teardown**——纯 GET，零副作用。退出前确认 `/readyz` 仍 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ERR-NOTFOUND`；实现 [`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)（`trace` 抛 404）、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_reqtrace_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-REQTRACE-01（正向）、OBS-REQTRACE-03（角色负向）互补但各自独立执行。
