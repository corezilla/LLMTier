# OBS-DEPL-02 — 写入故障注入

- **Case ID**：`OBS-DEPL-02`
- **标题**：`PATCH /v1/deployments/{id}/diagnostics` 写入故障注入：HTTP 200 + 返回更新后的 `InjectionView[]`，按 `(deployment_id, type)` upsert 生效，副作用 = **同事务审计**。
- **目的（被测契约）**：验证 `PATCH /v1/deployments/{deployment_id}/diagnostics` 的**注入写契约**。被测端点/规则：request body `InjectionList`（键集必须含 `items`，每项 `InjectionWrite = {type, config, enabled}`）；成功返回全量 `InjectionView[]`；按 `(deployment_id, injection_type)` upsert（幂等）；`enabled=true` 才生效；写在同一事务写审计（`action=diagnostics.injection.update`，`target=<deployment_id>`）；未知 deployment → 404 `not_found`（OBS-DEPL-03）；非法项 → 400 `invalid_injection`（OBS-DEPL-04）；认证 `admin`；统一信封 5 键。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.2 `D-OBS-INJECTION-CONFIG`、§5.1 `IF-OBS-INJECT` "PATCH partial upsert；副作用=注入配置写 + 审计"）；错误目录 `ERR-INJECTION`/`ERR-NOTFOUND`/`ERR-STORE`；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`InjectionList`/`InjectionWrite`/`InjectionView`）。**不证明什么**：不证明注入对推理的**命中效果**（DP-RESP-11/22 在 B 类以真实 `POST /v1/responses` 证明 `fault_502`/`fault_503` 命中；本 case 只证明"配置写入并可由 GET 读回"）、不证明非法项 400（OBS-DEPL-04）、不证明未知 deployment 404（OBS-DEPL-03）、不证明别名等价（OBS-ALIAS-04）。**契约一致性警示（须登记）**：`InjectionList` openapi `required:["items"]`、`additionalProperties:false`，但 handler 用 `body.get("items", [])`——缺 `items` 会**静默按空列表清空注入**（等价 revoke），多余键被忽略；本 case 用规范 body，另在报告登记该不一致。
- **前置与环境**：**环境 B**（临时实例 `127.0.0.1:<端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4）。执行前满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（实例可用、`prov_b`+`depl_b`+7 tier、`depl_b` healthy、LAN fake provider）。fixture：`llmtier_b` + `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 基线，`diagnostic_injections` **为空**（无启用注入）。**写 case：必须 teardown 清空**（[测试设计 §2.8](../llmtier-api-test-specification.md)）。
- **输入与构造**：`PATCH /v1/deployments/depl_b/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`。
  - 写入：`{"items": [{"type": "delay", "config": {"delay_ms": 2000}, "enabled": true}]}`
  - upsert 复核：再次 `PATCH` 同 `type` 改配置 `{"items": [{"type": "delay", "config": {"delay_ms": 500}, "enabled": true}]}` → 断言该 `type` 仅 1 项且 `delay_ms` 更新为 500（不新增重复项）。
  - 多类型：`{"items": [{"type":"fault_502","config":{"error_body":"boom"},"enabled":true},{"type":"rate_limit","config":{"retry_after_sec":2},"enabled":false}]}` → 断言两项、`enabled` 各自正确。
  - revoke：`{"items": []}` → 断言返回 `[]`（清空）。
  边界点：`delay_ms` 合法范围 `[0,60000]`；`enabled=false` 项被持久但不应生效（生效判定属 DP-RESP-11/22）；不构造非法项（OBS-DEPL-04）。
- **执行过程（逐步调用）**：
  1. `GET /v1/deployments/depl_b/diagnostics` → 断言初始 `[]`。
  2. `PATCH` 写入 `delay/delay_ms=2000/enabled=true` → 断言 `200`、body 数组含 `{type:"delay", config.delay_ms==2000, enabled:true, deployment_id:"depl_b"}`、恰 6 键、有 `id`/`updated_at`。
  3. `GET` 同路径 → 断言与步骤 2 一致（已持久化）。
  4. `PATCH` 同 `type` 改 `delay_ms=500` → 断言数组仍只 1 个 `delay` 项且 `delay_ms==500`（upsert 非新增）。
  5. `PATCH` 多类型（`fault_502` enabled=true、`rate_limit` enabled=false）→ 断言 2 项且各自 `enabled` 正确。
  6. （可选交叉证据）`GET /v1/audit` → 断言存在 `action=="diagnostics.injection.update"`、`target=="depl_b"`、`result=="success"` 的行。
  7. （teardown，`finally` 内）`PATCH` body `{"items": []}` → 断言 `200` 且 `[]`；`GET` 复核为空。
- **重点关注步骤**：① **写入可读回**——步骤 3 的 `GET` 必须与 `PATCH` 返回一致，证明持久而非仅回显。② **upsert 幂等**——同 `type` 重复写只保留 1 项（`ON CONFLICT(deployment_id,injection_type) DO UPDATE`），不得追加重复。③ **`enabled` 语义**——`enabled=false` 项仍持久（GET 可见）但不应生效；本 case 只断言持久。④ **项键集/枚举**——`InjectionView` 恰 6 键、`type` 白名单；`InjectionWrite` 恰 3 键。⑤ **revoke 语义**——`{"items":[]}` 清空；**必须**在 `finally` 执行，绝不把启用注入留给同 session 的 DP-RESP-11/22 或后续 case。⑥ **缺 `items` 风险（登记）**——`body.get("items", [])` 使 `{}` 等价 revoke；本 case 不用缺键 body，作为已知不一致上报。⑦ **同事务审计**——成功写入应可在 `GET /v1/audit` 见到；审计缺失即 FAIL。⑧ **降级/存储**——`_UnavailableDiagnostics.set_injections` 返回 `[]`（fail-open）；健康实例断言以真实库为准；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2；§3.5 列为 P0 MISSING Gate 阻断项），无 `at_obs_depl_02.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `InjectionView[]`/`InjectionWrite` wire 形态 + 机制 §4.3.2/§5.1 upsert+审计保证。
  - `PATCH`：HTTP `200`；`Content-Type: application/json`；body 为 `InjectionView[]`（每项恰 6 键、`type` 枚举、`config` 对象、`enabled` 布尔、`deployment_id` 匹配）。
  - upsert：同 `(deployment_id,type)` 不产生重复项。
  - revoke：`{"items":[]}` → `200` + `[]`。
  - 审计（独立交叉证据）：`GET /v1/audit` 含 `diagnostics.injection.update` 成功行（`target=depl_b`）。
  - **fail-open**：降级实例 `set_injections` 返回 `[]` 且不写库——降级下无法证明写入契约，判 **BLOCKED/SKIP**，**不**把空数组当 PASS。`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：写入 `200` 且 GET 可读回；同 type upsert 不重复；多类型/`enabled` 正确；审计存在；`finally` revoke 成功清空。
  - **FAIL**：任一断言不符——status 错、GET 读不回、重复项、`enabled` 错、审计缺失、或 teardown 未清空。
  - **BLOCKED**：测试代码/断言不可实现、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足（含 `depl_b` 非 healthy）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2；P0 Gate 阻断项），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 mock/替代路径冒充真实实例，或注入未真正写入却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存初始 `GET`、每个 `PATCH` 请求/响应、upsert 前后对比、多类型项、`GET /v1/audit` 审计行、teardown `items:[]` 与最终 `GET`、命令/exit code/`elapsed`、环境快照（`/healthz` + 注入前/后 `GET /deployments/depl_b/diagnostics`）。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**必须 teardown（`finally` 强制）**——`PATCH {"items":[]}` 清空，随后 `GET` 复核无启用项；不改 `prov_b`/`depl_b`、不重指 endpoint、不删除既有资源。B 类整班 `stop()` + `rm -rf`（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。离开前确认无未清空注入项；清空失败必须报错，不得留给后续 Case。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[§4.4](../llmtier-api-test-specification.md)）；M007 `diagnostic_injections`；`InjectionList`/`InjectionWrite`/`InjectionView` 机器契约；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)（`app.admin.mutate` 同事务审计）。自动化入口 `at_obs_depl_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；是 DP-RESP-11/22 的注入写入机制；与 OBS-DEPL-01/03/04、OBS-ALIAS-04 语义相邻但各自独立执行。
