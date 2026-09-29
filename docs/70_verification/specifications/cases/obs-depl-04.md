# OBS-DEPL-04 — 非法注入项

- **Case ID**：`OBS-DEPL-04`
- **标题**：`PATCH /v1/deployments/{id}/diagnostics` 提交非法注入项：HTTP 400 `invalid_injection`（`param` 指向被拒字段），不写入任何注入行。
- **目的（被测契约）**：验证注入写路径的**项校验负向契约**。被测端点/规则：`_validate` 要求 `type ∈ _TYPES`（否则 `param="type"`）、`config` 为对象（否则 `param="config"`）、每类型必填 `config` 字段（缺失 → `param=<field>`）、`error_body` 为非空字符串（>512B 按 UTF-8 截断）、`malformed_event_type ∈ {invalid_json, unknown_event_type}`、数值字段范围 `delay_ms∈[0,60000]`、`retry_after_sec∈[0,300]`、`stream_terminate_after_events∈[1,10000]`、`malformed_after_events∈[0,10000]` 且必须是 `int`（`bool` 被拒）（[`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)）；任何非法项 → `ApiError(400, "invalid_injection", ..., param=...)`，**零写入**。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.2 `D-OBS-INJECTION-CONFIG`、§5.1 "类型/字段/范围非法 → `ERR-INJECTION`（400）；校验失败不写、副作用无"）；错误目录 `ERR-INJECTION` → `invalid_injection`（[测试设计 §11.1](../llmtier-api-test-specification.md) `ERR-INJECTION → OBS-DEPL-04`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`InjectionList`/`InjectionWrite`，400 → `BadRequest`）。**不证明什么**：不证明正向写入（OBS-DEPL-02）、不证明未知 deployment 的 404（OBS-DEPL-03，且存在性优先于本校验）、不证明注入命中（DP-RESP-11/22）、不证明别名等价（OBS-ALIAS-04）。**契约偏差已登记**：openapi `InjectionWrite.enabled` 为必填 `boolean`，实现 `bool(item.get("enabled"))` 接受任意 truthy——见输入与构造"契约一致性登记"，本 case 不以 truthy 接受为契约通过。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；`depl_b` 存在且 healthy；fixture：`llmtier_b` + `admin_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态=基线，`diagnostic_injections` 为空；本 case 期望零写入，结束再次确认库中 `depl_b` 仍为空。
- **输入与构造**：对**已存在**的 `depl_b` 发起（每个非法项独立 `PATCH`）：
  - 未知 type：`{"items":[{"type":"bogus","config":{},"enabled":true}]}` → 400 `param="type"`
  - `config` 非对象：`{"items":[{"type":"delay","config":"x","enabled":true}]}` → 400 `param="config"`
  - 缺必填字段：`{"items":[{"type":"fault_502","config":{},"enabled":true}]}`（缺 `error_body`）→ 400 `param="error_body"`
  - `error_body` 空串/非串：`{"items":[{"type":"fault_502","config":{"error_body":""},"enabled":true}]}`、`{"error_body":123}` → 400 `param="error_body"`
  - 范围越界：`{"items":[{"type":"delay","config":{"delay_ms":60001},"enabled":true}]}`、`delay_ms:-1`、`{"type":"rate_limit","config":{"retry_after_sec":301}}`、`{"type":"stream_terminate","config":{"stream_terminate_after_events":0}}`、`{"type":"malformed_event","config":{"malformed_after_events":10001,"malformed_event_type":"invalid_json"}}` → 400 `param=<field>`
  - 非 int / bool：`{"items":[{"type":"delay","config":{"delay_ms":"1000"},"enabled":true}]}`、`{"delay_ms":true}` → 400 `param="delay_ms"`
  - 非法枚举：`{"items":[{"type":"malformed_event","config":{"malformed_after_events":1,"malformed_event_type":"bogus"},"enabled":true}]}` → 400 `param="malformed_event_type"`
  - 非数组 items：`{"items":"x"}` → 400 `invalid_injection`（`set_injections` 的列表检查）
  - 数组含一个合法 + 一个非法项：整体 400、**不得部分写入**

  边界点：`enabled` 可为任意 truthy（`bool(item.get("enabled"))`，`injections.py:34/55`），不参与 400 校验；`delay_ms=0`/`retry_after_sec=0`/`malformed_after_events=0` 是合法端点值（不得误判非法）。

  > **契约一致性登记（实现 vs openapi）**：openapi `InjectionWrite.enabled` 为**必填 `boolean`**（`required:["type","config","enabled"]`），故机器契约要求 `enabled` 为 JSON 布尔且必填；实现 `bool(item.get("enabled"))`（`injections.py:34/55`）把任意 truthy（字符串 `"yes"`、整数 `1`、缺省 `None`→`False`）**静默强制**为布尔。本 case 把该 truthy 接受登记为实现偏离 openapi 的**已知偏差**，**不**把"任意 truthy 被接受"当作契约通过；这亦**不**构成本 case 的 400 判据（非法样例集中在 `type`/`config`/范围/枚举，不含 `enabled`）。
- **执行过程（逐步调用）**：
  1. `GET /v1/deployments/depl_b/diagnostics` → 记录 `orig_raw`（应为 `[]`）。
  2. 对每个非法项独立 `PATCH` → 断言 `resp.status_code == 400`。
  3. 每次取 `err`：断言键集恰 5、`err["code"]=="invalid_injection"`、`err["type"]=="request_error"`、`err["retryable"] is False`；对被拒字段，断言 `err["param"]` 等于期望字段名（`type`/`config`/`error_body`/`delay_ms`/`retry_after_sec`/`stream_terminate_after_events`/`malformed_after_events`/`malformed_event_type`）。
  4. 混合项（合法+非法）→ 断言 400 且随后 `GET` 仍为 `orig_raw`（**无部分写入**）。
  5. 全部非法样例后 `GET /v1/deployments/depl_b/diagnostics` → 断言字节等于 `orig_raw`。
  6. （边界对照）合法端点值 `delay_ms=0` / `retry_after_sec=0` → 断言 `200`；随即 `PATCH {"items":[]}` 清空。（可选交叉证据）`GET /v1/audit` 见 `result=="failed"` 行。
- **重点关注步骤**：① **存在性优先**——`depl_b` 存在，故进入项校验并返回 400 `invalid_injection`（不是 404）。② **`param` 精确**——指向被拒字段名，而非笼统。③ **无部分写入**——混合项中即使一项合法也整体 400 且不落库（validate 在 txn 之前全量执行）。④ **范围边界**——`0` 是合法端点值；上限+1 非法；`bool` 是 `int` 子类但必须被拒（`isinstance(value, bool)` 显式排除）。⑤ **`error_body` 512B**——>512B 是**静默截断**（合法），空串/非串才 400；本 case 不把长串当非法。⑥ **错误信封 identity**——恰 5 键、`type=request_error`。⑦ **`enabled` 契约偏差**——openapi `InjectionWrite` 要求 `enabled` 为必填 `boolean`，实现接受任意 truthy；此为实现/openapi 偏差，单独登记（见输入与构造"契约一致性登记"），**不**作为契约通过、也不混入 400 判据。⑧ **零副作用**——非法序列后注入表逐字节不变。⑨ **降级/存储**——`_UnavailableDiagnostics.set_injections` 不校验、返回 `[]` 属降级实例 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_depl_04.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `BadRequest`（`ErrorEnvelope`）+ 机制 §4.3.2 `D-OBS-INJECTION-CONFIG` 白名单/范围 + `ERR-INJECTION`。
  - 每个非法项：HTTP `400`；`Content-Type: application/json`；body `{"error":{"message":<str>,"type":"request_error","code":"invalid_injection","param":"<field>","retryable":false}}`（恰 5 键）。
  - 不变量：非法序列后 `GET /v1/deployments/depl_b/diagnostics` 与 `orig_raw` 逐字节相同；混合项无部分写入。
  - 对照：合法端点值 `0` → 200。
  - **fail-open**：降级实例不校验（无法证明契约）→ **BLOCKED/SKIP**；健康实例返回 200/非 `invalid_injection` → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有非法项均 `400 + invalid_injection + type=request_error + retryable=false + param=字段名`；无部分写入；合法边界 `0` 为 200。
  - **FAIL**：任一非法项返回非 400、`code`/`param` 错、接受 `bool`/字符串数值/越界值，或出现部分写入。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交非法项却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存每个非法请求 body 与原始 400 信封、混合项无部分写入对比、`orig_raw` 前后、合法边界对照、可选失败审计、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需数据 teardown**——非法输入零写入；仍须 `GET` 复核 `depl_b` 注入为空，并清空边界对照产生的合法注入（`PATCH {"items":[]}`）。离开前确认无未清空注入项、`/readyz` 7 tier。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ERR-INJECTION`；`InjectionList`/`InjectionWrite` 机器契约（`enabled` 必填 `boolean` — 见"契约一致性登记"）；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)（`_validate`/`_TYPES`/`_RANGES`/`_CONFIG_FIELDS`）、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_depl_04.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-DEPL-02（正向写）、OBS-DEPL-03（未知 404，存在性优先）互补但各自独立执行。
