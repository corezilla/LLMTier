# OBS-DIAG-03 — 开关更新非法值

- **Case ID**：`OBS-DIAG-03`
- **标题**：`PATCH /v1/diagnostics` 提交非布尔开关值：HTTP 400 `invalid_request`（`param` 指向被拒键），开关状态不变、无部分写入。
- **目的（被测契约）**：验证 `PATCH /v1/diagnostics` 的**输入校验负向契约**。被测端点/规则：`PATCH /v1/diagnostics`，`set_switches` 对每个传入的非 `None` 值要求 `isinstance(value, bool)`，否则抛 `ApiError(400, "invalid_request", "<name> must be a boolean", param=<name>)`（[`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)）；错误走统一信封 `{error:{message,type,code,param,retryable}}`（`type="request_error"`，`retryable=false`）；校验发生在事务之前，**零副作用**（`diagnostic_settings` 不变、无成功审计；`app.admin.mutate` 失败路径会记一条 `result="failed"` 审计）。设计验证项 `VRC-DIAG-001`；机制 `T-OBS-SWITCH`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.1/§5.1，`IF-OBS-SWITCH` "校验=非 bool 且非 None → 拒绝；失败无副作用"）；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01`/`R-OBS-02`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`DiagnosticsSwitchPatch`，400 → `BadRequest`）。**不证明什么**：不证明合法更新的成功/审计（OBS-DIAG-02）、不证明 GET 读契约（OBS-DIAG-01）、不证明**未知键**被拒（openapi 虽声明 `additionalProperties:false`，当前 handler 不校验多余键——见重点关注，作为实现/openapi 不一致单独登记）、不证明认证负向（AUTH-08/OBS-REQTRACE-03 风格）。
- **前置与环境**：**环境 B**（临时实例 `127.0.0.1:<端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4）。执行前满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（实例可启动、`/healthz` 200、`prov_b`+`depl_b`+7 tier、`depl_b` healthy、LAN fake provider）。fixture：`llmtier_b` + `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 基线；`diagnostic_settings` 单行默认 `{false,false}`。本 case 期望零写入，故**不改变开头状态**；仍须在结尾核验状态未变。
- **输入与构造**：先 `GET /v1/diagnostics` 记录 `orig_raw`，再对每种非法输入独立发起（每次前确保开关仍是 `orig`）：
  - `{"snapshots_enabled": "yes"}`（字符串）
  - `{"snapshots_enabled": 1}`（整数——注意 Python `isinstance(1, bool) is False`，必须拒）
  - `{"stats_enabled": null}`（显式 `null`：`body.get` 得 `None`，**属合法"保持"语义**，不应 400——作为对照，列入边界观察而非非法样例）
  - `{"stats_enabled": "true"}` / `{"stats_enabled": 0}`（字符串/整数）
  - `{"snapshots_enabled": []}`（数组）、`{"stats_enabled": {}}`（对象）

  请求：`PATCH /v1/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`。边界点：每种非法值必须命中 400 且 `param` 等于该键名；`null` 是合法缺省语义（不得误判为非法）。
- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics` → 记录 `orig_raw`。
  2. 对每个非法 body（上述字符串/整数/数组/对象样例）逐个 `PATCH`；每个后立即 `GET` 复核开关未变。
  3. 每次断言 `resp.status_code == 400`；`err = resp.json()["error"]`：`err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`、`err["param"]` 等于被拒键名（`snapshots_enabled` 或 `stats_enabled`）。
  4. 全部非法样例后 `GET /v1/diagnostics` → 断言字节等于 `orig_raw`（无任何写入）。
  5. （对照）`PATCH` body `{"stats_enabled": null}` → 断言 `200` 且 `stats_enabled == orig`（`null` 保持，非错误）；随即恢复原值（无变化）。
  6. （可选交叉证据）`GET /v1/audit` → 断言非法尝试对应 `result=="failed"` 的 `diagnostics.switch.update` 行存在，且**不存在**由本 case 产生的成功行。
- **重点关注步骤**：① **bool vs int**——`1`/`0` 必须是非法（Python 中 `bool` 是 `int` 子类，但校验用的是 `isinstance(value, bool)`，故 `1` 被拒）；若观测到 `1` 被接受为 `true`，判 FAIL。② **`param` 精确性**——必须指向被拒字段名，而非笼统。③ **零副作用**——400 后 `diagnostic_settings` 逐字节不变，不得出现"一半写入"（例如先写 `snapshots_enabled` 再在 `stats_enabled` 校验失败）。④ **失败审计**——`mutate` 失败路径记 `result="failed"`；不得把失败审计当作契约成功。⑤ **`null` 不是非法**——`{"stats_enabled": null}` 表示保持，若被 400 拒绝判 FAIL（输入语义误判）。⑥ **未知键差异（登记）**——`DiagnosticsSwitchPatch` openapi `additionalProperties:false`，但实现忽略多余键；本 case 可在报告中作为**已知不一致**记录：`{"snapshots_enabled": true, "bogus": 1}` 当前预期 200（实现）而契约声明应 400——本 case 的 PASS 判据**不含**未知键，避免混淆。⑦ **降级/存储**——`_UnavailableDiagnostics.set_switches` 不校验直接返回默认，属降级实例（本 case 无法证明校验逻辑）→ BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_diag_03.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `BadRequest`（`ErrorEnvelope`）+ 机制 §5.1 `IF-OBS-SWITCH` 校验语义 + 错误目录 `ERR-REQ-VALIDATION`。
  - 每个非法输入：HTTP `400`；`Content-Type: application/json`；body `{"error":{"message":"<name> must be a boolean","type":"request_error","code":"invalid_request","param":"<name>","retryable":false}}`（恰 5 键；openapi 未为 200/400 声明响应头）。
  - 状态不变量：非法序列后 `GET /v1/diagnostics` 与 `orig_raw` 逐字节相同。
  - 对照：`null` → 200 且值保持（非错误）。
  - **fail-open**：降级实例（`_UnavailableDiagnostics`）不执行校验、恒返回默认——本 case 依赖真实校验，降级下判 BLOCKED/SKIP，**不**把默认值当 PASS。存储不可达 503 `usage_store_unavailable` 判 BLOCKED/SKIP。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有非法样例均 `400 + invalid_request + type=request_error + retryable=false + param=键名`，且状态逐字节不变；`null` 对照为 200 保持。
  - **FAIL**：任一非法值返回非 400、`code`/`type`/`param` 错、接受了 `1`/`0`/字符串，或出现部分写入/状态改变。
  - **BLOCKED**：测试代码/契约本身问题或降级实例无法证明校验、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9（MISSING ≠ NOT_RUN）。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交非法 body 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存每个非法请求 body 与原始 400 信封、`GET` 前后 `orig_raw` 对比、失败审计行（可选）、`null` 对照、命令/exit code/`elapsed`、环境快照。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需数据 teardown**——非法输入零写入，`diagnostic_settings` 保持初值；仍须 `GET` 复核并确认无残留。B 类整班 `stop()` + `rm -rf`（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。离开前确认开关初值、`/readyz` 7 tier、无未清空注入项。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[§4.4](../llmtier-api-test-specification.md)）；`diagnostic_settings`；`DiagnosticsSwitchPatch` 机器契约；实现 [`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_diag_03.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-DIAG-02（合法更新成功）互为正向/负向，各自独立执行。
