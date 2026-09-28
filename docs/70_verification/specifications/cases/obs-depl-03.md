# OBS-DEPL-03 — 注入未知 deployment

- **Case ID**：`OBS-DEPL-03`
- **标题**：`PATCH /v1/deployments/{id}/diagnostics` 对未知 deployment：HTTP 404 `not_found`，不写入任何注入行。
- **目的（被测契约）**：验证注入写路径的**资源存在性负向契约**。被测端点/规则：`PATCH /v1/deployments/{deployment_id}/diagnostics`，`set_injections` 首先 `SELECT 1 FROM deployments WHERE id=?`，不存在则抛 `ApiError(404, "not_found", "Unknown deployment: <id>")`（[`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)），**先于**对 `items` 的校验；因此即使 body 为 `{"items":[]}` 或含非法项，未知 deployment 也应是 404（存在性优先）；**零副作用**（不写注入、不写成功审计；`mutate` 失败路径记 `result="failed"`）。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-INJECT` "未知 deployment（读）→ `ERR-NOTFOUND`（404）；校验失败不写、副作用无"）；错误目录 `ERR-NOTFOUND` → `not_found`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)，见[测试设计 §11.1](../llmtier-api-test-specification.md) `ERR-NOTFOUND → ...、OBS-DEPL-03、...`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正向写入（OBS-DEPL-02）、不证明非法注入项的 400（OBS-DEPL-04）、不证明 GET 读取侧未知 404（虽同实现检查，本 case 聚焦 PATCH；可将 GET 作为交叉核对）、不证明别名等价（OBS-ALIAS-04）。
- **前置与环境**：**环境 B**（临时实例 `127.0.0.1:<端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4）。执行前满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**。fixture：`llmtier_b` + `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 基线；本 case 期望零写入、**不存在**该 deployment；结束再次确认库中无该 id 的注入。
- **输入与构造**：固定请求：
  `PATCH /v1/deployments/does_not_exist/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`，body 逐项独立发起：
  - `{"items": [{"type": "delay", "config": {"delay_ms": 1000}, "enabled": true}]}`（合法注入项但未知 deployment）
  - `{"items": []}`（revoke 形态但未知 deployment——验证存在性优先于"空列表清空"）
  - `{"items": [{"type": "bogus", "config": {}, "enabled": true}]}`（非法 type + 未知 deployment——验证 404 优先于 400）
  - `{"items": "not-a-list"}`（非数组 + 未知 deployment）

  边界点：`{id}` 为语法合法但库中不存在的字符串（如 `dep_deadbeef`）；不测已存在 deployment（OBS-DEPL-02）。
- **执行过程（逐步调用）**：
  1. `GET /v1/deployments/does_not_exist/diagnostics`（交叉核对）→ 断言 `404 not_found`（同存在性检查）。
  2. 对每个 PATCH body 变体 `PATCH` → 断言 `resp.status_code == 404`。
  3. 每次取 `err = resp.json()["error"]`：断言键集恰 5、`err["code"]=="not_found"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. 断言 body `{"items":[]}` 在该未知 id 上返回 **404 而非 200**（存在性优先于清空语义）。
  5. 断言 body 含非法 type 时返回 **404 而非 400**（存在性优先于项校验）——若返回 400 则存在性检查顺序错误，判 FAIL（与 `set_injections` 的顺序契约不符）。
  6. （可选交叉证据）`GET /v1/audit` → 断言存在 `result=="failed"` 的 `diagnostics.injection.update` 行，且无成功行。
- **重点关注步骤**：① **存在性优先顺序**——`set_injections` 先查 deployment 再校验 items；故未知 deployment + 非法项 → 404（不是 400），未知 deployment + `items:[]` → 404（不是 200 清空）。这是本 case 最易误判点。② **code 精确**——`not_found`（非 `invalid_injection`/`invalid_request`）。③ **零副作用**——404 不写注入行、不写成功审计。④ **错误信封 identity**——恰 5 键、`type=request_error`。⑤ **GET/PATCH 一致**——读与写都做存在性检查，404 语义一致。⑥ **失败审计**——`mutate` 失败路径记 `result="failed"`。⑦ **降级/存储**——`_UnavailableDiagnostics.set_injections` 返回 `[]`（不检查存在性）属降级实例 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_depl_03.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `NotFound`（`ErrorEnvelope`）+ 机制 §5.1 存在性检查顺序语义。
  - `PATCH` 未知 deployment（任意 body 变体）：HTTP `404`；`Content-Type: application/json`；body `{"error":{"message":"Unknown deployment: does_not_exist","type":"request_error","code":"not_found","param":<string|null>,"retryable":false}}`（恰 5 键；`message` 措辞以实现为准，仅断言 code/type）。
  - 交叉：`GET` 同未知 id → `404 not_found`。
  - 零副作用：库中无该 id 的注入行。
  - **fail-open**：降级实例不检查存在性、返回空（无法证明契约）→ **BLOCKED/SKIP**；健康实例返回 400/200 而非 404 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有未知 id PATCH（含 `items:[]`、非法项、非数组）均 `404 + not_found`，且 GET 一致、零副作用。
  - **FAIL**：返回 200/400 而非 404、`code` 不符，或出现注入写入。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交未知 id 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存每个 body 变体的原始 404 信封、GET 交叉 404、失败审计（可选）、命令/exit code/`elapsed`、环境快照。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需数据 teardown**——未知 id 零写入；确认库中无该 id 注入行。B 类整班 `stop()` + `rm -rf`（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。离开前确认无残留、`/readyz` 7 tier、无未清空注入项。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ERR-NOTFOUND`；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_depl_03.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-DEPL-02（正向写）、OBS-DEPL-04（非法项）互补且需注意判定顺序差异，各自独立执行。
