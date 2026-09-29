# OBS-ALIAS-02 — 别名 diagnostics/snapshots

- **Case ID**：`OBS-ALIAS-02`
- **标题**：`/tier/admin/v1/diagnostics/snapshots` 与 `/v1/diagnostics/snapshots` 的 GET 由同一 handler 服务：status 与响应体逐字节等价。
- **目的（被测契约）**：验证快照查询别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/diagnostics/snapshots` 是 `/v1/diagnostics/snapshots` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/diagnostics/snapshots": "/v1/diagnostics/snapshots"`），同一 handler、相同 `SnapshotPage` 形状、相同 `admin` 鉴权（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.snapshots_page`）；body 应逐字节等价（[测试设计 §4.10](../llmtier-api-test-specification.md)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-SNAP`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-API-QUERY`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`SnapshotPage`）。**不证明什么**：不证明快照内容/脱敏（OBS-SNAP-01）、不证明无效 cursor 负向（OBS-SNAP-02）、不证明 diagnostics/stats、traces 或 trace 别名（OBS-ALIAS-05/06/03）、不证明别名鉴权负向（AUTH-08）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线；本 case 纯 GET，初态即终态。
- **输入与构造**：固定请求（无 body）：
  - `GET /v1/diagnostics/snapshots?limit=50`
  - `GET /tier/admin/v1/diagnostics/snapshots?limit=50`
  同凭据、同参数（可加相同 `since`/`until` 固定窗）。边界点：两请求参数必须**逐一相同**（否则 body 本可不同）；`X-Request-ID` 每次不同，**不参与** body 比较，也不列入 Oracle。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/snapshots?limit=50`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. `GET /tier/admin/v1/diagnostics/snapshots?limit=50`（同 client、同参数）→ 记录同样字段。
  4. 断言两 `status == 200`、`Content-Type` 相同、`resp.content` **逐字节相等**。
  5. 断言两者均为合法 `SnapshotPage`（顶层键集恰 `{items, next_cursor, has_more}`）；本 case 仅判等价，形状细节归 OBS-SNAP-01。
- **重点关注步骤**：① **参数严格对齐**——两请求 query 完全一致才可逐字节比较。② **逐字节 body 等价**——比较 `resp.content`，不是解析后对象。③ **只比 body**——`X-Request-ID` 不参与，也不列入 Oracle。④ **鉴权等价**——都需 `admin`（本 case 正向；负向 AUTH-08）。⑤ **空页也须等价**——`items=[]` 时两路径仍应完全一致。⑥ **降级/存储**——降级实例两路径同样返回空页（等价仍成立，判 BLOCKED/SKIP 说明语义）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_alias_02.py`。
- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `SnapshotPage` wire 形态。
  - 两路径均 `200`，`Content-Type: application/json`，`body_flat == body_alias`（逐字节）。
  - 均为合法 `SnapshotPage`。
  - **fail-open**：降级实例两路径同样空页（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：两路径 status 相同且 body 逐字节相等（含空页）。
  - **FAIL**：status/body 不等价或别名 404。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存两路径响应与逐字节对比、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/diagnostics/snapshots` 分支）。自动化入口 `at_obs_alias_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-SNAP-01（内容/脱敏）、AUTH-08（别名鉴权）语义相邻，与其它别名并列但各自独立执行。
