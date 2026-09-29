# OBS-ALIAS-05 — 别名 diagnostics/stats

- **Case ID**：`OBS-ALIAS-05`
- **标题**：`/tier/admin/v1/diagnostics/stats` 与 `/v1/diagnostics/stats` 的 GET 由同一 handler 服务：status 与响应体逐字节等价（含缺参 400 信封）。
- **目的（被测契约）**：验证诊断统计别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/diagnostics/stats` 是 `/v1/diagnostics/stats` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/diagnostics/stats": "/v1/diagnostics/stats"`），同一 handler、相同 `StatsView` 形状、相同 `admin` 鉴权与相同必填参数校验（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.stats`）；body 应逐字节等价（[测试设计 §4.10](../llmtier-api-test-specification.md)）；错误在扁平/别名上亦逐字节等价（[测试设计 §4.6](../llmtier-api-test-specification.md)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-STATS`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`StatsView`、`BadRequest`）。**不证明什么**：不证明聚合窗口内容（OBS-STATS-01）、不证明缺参 400 本身（OBS-STATS-02）、不证明其它别名、不证明别名鉴权负向（AUTH-08）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线；本 case 纯 GET，初态即终态。
- **输入与构造**：
  - **正向**：同一宽窗 `?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z` 分别请求两路径。
  - **缺参（确定性 400 锚点）**：`GET /v1/diagnostics/stats` 与 `GET /tier/admin/v1/diagnostics/stats`（都不带 `since`/`until`）。
  同凭据、同参数。边界点：两请求参数必须逐一相同；`X-Request-ID` 每次不同，**不参与**比较，也不列入 Oracle。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/stats?since=...&until=...`（`admin_client`）→ 记录 status/`Content-Type`/body。
  3. `GET /tier/admin/v1/diagnostics/stats?<同参>` → 断言两 `200` 且 `resp.content` **逐字节相等**；均为合法 `StatsView`（顶层键集恰 `{windows}`）。
  4. **缺参等价**：两路径都不带 `since`/`until` → 断言两 `400` 且 `resp.content` **逐字节相等**，`code=="invalid_request"`。
  5. 断言两路径 status 与 body 一致；仅 `X-Request-ID` 不同（不参与断言）。
- **重点关注步骤**：① **参数严格对齐**——同 query 才可逐字节比较。② **逐字节 body 等价**——比较 `resp.content`。③ **错误路径也等价**——缺参 400 信封在两路径逐字节相同（确定性锚点，且不依赖是否已有统计数据）。④ **只比 body**——`X-Request-ID` 不参与、不列入 Oracle。⑤ **鉴权等价**——都需 `admin`（正向；负向 AUTH-08）。⑥ **无数据也等价**——`windows=[]` 时两路径仍完全一致。⑦ **降级/存储**——降级实例两路径同样 `{"windows":[]}`（等价成立，判 BLOCKED/SKIP 说明语义）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_alias_05.py`。
- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `StatsView`/`BadRequest` wire 形态。
  - 正向：两路径 `200`，`body_flat == body_alias`（逐字节），均为合法 `StatsView`。
  - 缺参：两路径 `400`，`body_flat == body_alias`（逐字节），`code=="invalid_request"`。
  - **fail-open**：降级实例两路径同样空 `windows`（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：同一参数下两路径 status 相同且 body 逐字节相等（正向与缺参 400 两锚点均成立）。
  - **FAIL**：status/body 不等价、别名 404 或错误 code 不同。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存两路径正向响应、两路径缺参 400、逐字节对比结果、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/diagnostics/stats` 分支）。自动化入口 `at_obs_alias_05.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-STATS-01/02（内容/缺参）、AUTH-08 语义相邻，与其它别名并列但各自独立执行。
