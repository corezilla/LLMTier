# OBS-DIAG-03 — 开关更新非法值

- **Case ID**：`OBS-DIAG-03`
- **标题**：`PATCH /v1/diagnostics` 提交非布尔开关值（含依 openapi 应被拒的 `null`）：HTTP 400 `invalid_request`（`param` 指向被拒键），开关状态不变、无部分写入；`null` 若实现按"保持"返回 200，登记为实现/openapi 偏差。
- **目的（被测契约）**：验证 `PATCH /v1/diagnostics` 的**输入校验负向契约**。被测端点/规则：`PATCH /v1/diagnostics`，`set_switches` 对每个传入的非 `None` 值要求 `isinstance(value, bool)`，否则抛 `ApiError(400, "invalid_request", "<name> must be a boolean", param=<name>)`（[`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)）；错误走统一信封 `{error:{message,type,code,param,retryable}}`（`type="request_error"`，`retryable=false`）；校验发生在事务之前，**零副作用**（`diagnostic_settings` 不变、无成功审计；`app.admin.mutate` 失败路径会记一条 `result="failed"` 审计）。设计验证项 `VRC-DIAG-001`；机制 `T-OBS-SWITCH`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.1/§5.1，`IF-OBS-SWITCH` "校验=非 bool 且非 None → 拒绝；失败无副作用"）；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01`/`R-OBS-02`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`DiagnosticsSwitchPatch`，400 → `BadRequest`）。**不证明什么**：不证明合法更新的成功/审计（OBS-DIAG-02）、不证明 GET 读契约（OBS-DIAG-01）、不证明**未知键**被拒（openapi 虽声明 `additionalProperties:false`，当前 handler 不校验多余键——见重点关注，作为实现/openapi 不一致单独登记）、不证明认证负向（AUTH-08/OBS-REQTRACE-03 风格）。**契约冲突已登记**：`null` 被 openapi `boolean` 拒绝（应 400），实现按"保持"返回 200——见输入与构造"契约一致性登记"。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；执行前附加（B 类）实例可启动、`/healthz` 200、`prov_b`+`depl_b`+7 tier、`depl_b` healthy、LAN fake provider；fixture：`llmtier_b` + `admin_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态=基线；`diagnostic_settings` 单行默认 `{false,false}`。本 case 期望零写入，故**不改变开头状态**；仍须在结尾核验状态未变。
- **输入与构造**：先 `GET /v1/diagnostics` 记录 `orig_raw`，再对每种非法输入独立发起（每次前确保开关仍是 `orig`）：
  - `{"snapshots_enabled": "yes"}`（字符串）
  - `{"snapshots_enabled": 1}`（整数——注意 Python `isinstance(1, bool) is False`，必须拒）
  - `{"stats_enabled": null}`（显式 `null`：实现 `body.get` 得 `None`，`set_switches` 对 `None` 跳过校验、**按"保持"处理**；但 openapi `DiagnosticsSwitchPatch` 把两键类型声明为 `boolean`（`additionalProperties:false`，无 `nullable`），**严格契约下 `null` 是类型违规 ⇒ 400**。此为实现/openapi 冲突，见下"契约一致性登记"；本 case 按 openapi 期望 **400**，不以"保持"为预期。）
  - `{"stats_enabled": "true"}` / `{"stats_enabled": 0}`（字符串/整数）
  - `{"snapshots_enabled": []}`（数组）、`{"stats_enabled": {}}`（对象）

  请求：`PATCH /v1/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`。  边界点：每种非法值必须命中 400 且 `param` 等于该键名；`null` 按 **openapi 契约**为类型违规（应 400），实现当前按"保持"处理——差异见下"契约一致性登记"。

  > **契约一致性登记（机制/实现 vs openapi）**：`DiagnosticsSwitchPatch` 将 `snapshots_enabled`/`stats_enabled` 声明为 `"type":"boolean"`（`additionalProperties:false`，**不可空**），故机器契约下 `{"stats_enabled": null}` ⇒ **400**；而机制 §5.1 `IF-OBS-SWITCH` 只拒绝"非 bool **且非 None**"，实现 `set_switches`（`settings.py:16-18`）对 `None` 跳过校验 ⇒ 返回 `200` 保持。二者冲突。本 case 的 Oracle 依 openapi 断言 **400**，并把实现的 `200 保持` 作为**已知偏差登记**（报告 `result="failed"`/不一致注记），**不**把 400 当 FAIL、也**不**把 200 当契约通过。
- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics` → 记录 `orig_raw`。
  2. 对每个非法 body（上述字符串/整数/数组/对象样例）逐个 `PATCH`；每个后立即 `GET` 复核开关未变。
  3. 每次断言 `resp.status_code == 400`；`err = resp.json()["error"]`：`err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`、`err["param"]` 等于被拒键名（`snapshots_enabled` 或 `stats_enabled`）。
  4. 全部非法样例后 `GET /v1/diagnostics` → 断言字节等于 `orig_raw`（无任何写入）。
  5. （契约一致性）`PATCH` body `{"stats_enabled": null}` → 依 openapi 断言 `400 invalid_request`（`null` 违反 `boolean`）；若实现返回 `200`（保持），**登记为实现偏离 openapi 的已知偏差**，不属于本 case 的契约 FAIL 判据之外（见"契约一致性登记"）；实现返回 200 时随即 `GET` 确认开关未变。
  6. （可选交叉证据）`GET /v1/audit` → 断言非法尝试对应 `result=="failed"` 的 `diagnostics.switch.update` 行存在，且**不存在**由本 case 产生的成功行。
- **重点关注步骤**：① **bool vs int**——`1`/`0` 必须是非法（Python 中 `bool` 是 `int` 子类，但校验用的是 `isinstance(value, bool)`，故 `1` 被拒）；若观测到 `1` 被接受为 `true`，判 FAIL。② **`param` 精确性**——必须指向被拒字段名，而非笼统。③ **零副作用**——400 后 `diagnostic_settings` 逐字节不变，不得出现"一半写入"（例如先写 `snapshots_enabled` 再在 `stats_enabled` 校验失败）。④ **失败审计**——`mutate` 失败路径记 `result="failed"`；不得把失败审计当作契约成功。⑤ **`null` 的契约处置**——openapi 把两键声明为 `boolean`（无 `nullable`），故 `{"stats_enabled": null}` 依**机器契约应 400**；而实现/机制按"保持"返回 200，此差异单独登记（见"契约一致性登记"），**不得**把实现的 200 保持当作契约通过、也**不得**把契约要求的 400 判为 FAIL。⑥ **未知键差异（登记）**——`DiagnosticsSwitchPatch` openapi `additionalProperties:false`，但实现忽略多余键；本 case 可在报告中作为**已知不一致**记录：`{"snapshots_enabled": true, "bogus": 1}` 当前预期 200（实现）而契约声明应 400——本 case 的 PASS 判据**不含**未知键，避免混淆。⑦ **降级/存储**——`_UnavailableDiagnostics.set_switches` 不校验直接返回默认，属降级实例（本 case 无法证明校验逻辑）→ BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_diag_03.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `BadRequest`（`ErrorEnvelope`）+ 机制 §5.1 `IF-OBS-SWITCH` 校验语义 + 错误目录 `ERR-REQ-VALIDATION`。
  - 每个非法输入：HTTP `400`；`Content-Type: application/json`；body `{"error":{"message":"<name> must be a boolean","type":"request_error","code":"invalid_request","param":"<name>","retryable":false}}`（恰 5 键；openapi 未为 200/400 声明响应头）。
  - 状态不变量：非法序列后 `GET /v1/diagnostics` 与 `orig_raw` 逐字节相同。
  - 契约一致性项：`{"stats_enabled": null}` 依 openapi `boolean` 类型 ⇒ `400`；实现返回 200 保持属**已登记偏差**，不计入 FAIL（见"契约一致性登记"）。
  - **fail-open**：降级实例（`_UnavailableDiagnostics`）不执行校验、恒返回默认——本 case 依赖真实校验，降级下判 BLOCKED/SKIP，**不**把默认值当 PASS。存储不可达 503 `usage_store_unavailable` 判 BLOCKED/SKIP。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有非法样例（含依 openapi 应 400 的 `null`）均 `400 + invalid_request + type=request_error + retryable=false + param=键名`，且状态逐字节不变；`null` 若实测 200 保持，按已登记偏差记录、不判 FAIL。
  - **FAIL**：任一**非 `null`** 非法值返回非 400、`code`/`type`/`param` 错、接受了 `1`/`0`/字符串，或出现部分写入/状态改变（`null` 的 400 vs 200 差异属已登记偏差，不计 FAIL）。
  - **BLOCKED**：测试代码/契约本身问题或降级实例无法证明校验、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9（MISSING ≠ NOT_RUN）。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交非法 body 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存每个非法请求 body 与原始 400 信封、`GET` 前后 `orig_raw` 对比、失败审计行（可选）、`null` 对照、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需数据 teardown**——非法输入零写入，`diagnostic_settings` 保持初值；仍须 `GET` 复核并确认无残留。离开前确认开关初值、`/readyz` 7 tier、无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[§4.4](../llmtier-api-test-specification.md)）；`diagnostic_settings`；`DiagnosticsSwitchPatch` 机器契约（`boolean`、`additionalProperties:false`，`null` 应 400 — 见"契约一致性登记"）；实现 [`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_diag_03.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-DIAG-02（合法更新成功）互为正向/负向，各自独立执行。
