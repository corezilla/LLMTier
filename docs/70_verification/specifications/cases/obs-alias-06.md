# OBS-ALIAS-06 — 别名 diagnostics/traces

- **Case ID**：`OBS-ALIAS-06`
- **标题**：`/tier/admin/v1/diagnostics/traces` 与 `/v1/diagnostics/traces` 的 GET 由同一 handler 服务：status 与响应体逐字节等价（含无效 cursor 路径的等价观察）。
- **目的（被测契约）**：验证 trace 列表别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/diagnostics/traces` 是 `/v1/diagnostics/traces` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/diagnostics/traces": "/v1/diagnostics/traces"`），同一 handler、相同 `TracePage` 形状、相同 `admin` 鉴权（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.traces`）；body 应逐字节等价（[测试设计 §4.10](../llmtier-api-test-specification.md)）；错误在扁平/别名上亦逐字节等价（[测试设计 §4.6](../llmtier-api-test-specification.md)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`TracePage`）。**不证明什么**：不证明去重/有序（OBS-TRACE-01）、不证明 `limit=1`/无效 cursor 负向（OBS-TRACE-02）、不证明其它别名、不证明别名鉴权负向（AUTH-08）。**契约一致性警示（须登记）**：traces cursor 当前无校验（OBS-TRACE-02 已记）；本 case 只判两路径彼此等价，不改变该缺陷判定。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项**就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 tier；本 case 纯 GET，初态即终态。
- **输入与构造**：
  - **正向**：同一参数 `?limit=50`（可加相同 `since`/`until`）分别请求两路径。
  - **边界等价观察**：同一无效 cursor `?limit=1&cursor=not-a-real-cursor` 分别请求两路径（当前实现会忽略/应用该 cursor；本 case 只断言两路径行为**相同**，不把 400/200 本身作为 Oracle——那属 OBS-TRACE-02）。
  同凭据、同参数。边界点：`X-Request-ID` 每次不同，**不参与**比较，也不列入 Oracle。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/traces?limit=50`（`admin_client`）→ 记录 status/`Content-Type`/body。
  3. `GET /tier/admin/v1/diagnostics/traces?limit=50`（同 client、同参数）→ 断言两 `200` 且 `resp.content` **逐字节相等**；均为合法 `TracePage`（顶层键集恰 `{items, next_cursor, has_more}`）。
  4. **边界等价**：两路径同带 `?limit=1&cursor=not-a-real-cursor` → 断言两路径 **status 与 body 逐字节相同**（不判该状态是否为 400；负向判定归 OBS-TRACE-02）。
  5. 断言两路径 status 与 body 一致；仅 `X-Request-ID` 不同（不参与断言）。
- **重点关注步骤**：① **参数严格对齐**——同 query 才可逐字节比较。② **逐字节 body 等价**——比较 `resp.content`。③ **边界路径只判等价**——无效 cursor 下只要求两路径**行为一致**，不在此判定 cursor 负向是否合规（避免与 OBS-TRACE-02 重复/冲突）。④ **只比 body**——`X-Request-ID` 不参与、不列入 Oracle。⑤ **鉴权等价**——都需 `admin`（正向；负向 AUTH-08）。⑥ **空页也须等价**——`items=[]` 时两路径仍完全一致。⑦ **降级/存储**——降级实例两路径同样空页（等价成立，判 BLOCKED/SKIP 说明语义）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_alias_06.py`。
- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `TracePage` wire 形态。
  - 正向：两路径 `200`，`body_flat == body_alias`（逐字节），均为合法 `TracePage`。
  - 边界：同一无效 cursor 下两路径 status 与 body **完全一致**（无论该状态是什么）。
  - **fail-open**：降级实例两路径同样空页（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：同一参数下两路径 status 相同且 body 逐字节相等（正向与无效 cursor 边界均成立）。
  - **FAIL**：status/body 不等价或别名 404。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存两路径正向响应与逐字节对比、无效 cursor 边界两路径响应、命令/exit code/`elapsed`、环境快照。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/diagnostics/traces` 分支）。自动化入口 `at_obs_alias_06.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-TRACE-01/02（内容/分页）、AUTH-08 语义相邻，与其它别名并列但各自独立执行。
