# OBS-SNAP-01 — 快照页（脱敏）

- **Case ID**：`OBS-SNAP-01`
- **标题**：`GET /v1/diagnostics/snapshots` 返回 `SnapshotPage`：`{items[], next_cursor, has_more}` 键集精确、每项为恰好 11 键的 `SnapshotView`，且内容**已脱敏**（`upstream_url` 去 query、`error_summary` ≤256B、不含 Secret/凭据/正文）。
- **目的（被测契约）**：验证 Observability `GET /v1/diagnostics/snapshots` 的**只读分页 + 脱敏契约**。被测端点/规则：`GET /v1/diagnostics/snapshots`（可选 `since`/`until`/`deployment_id`/`model`/`limit`/`cursor`），返回 `SnapshotPage`（`items`/`next_cursor`/`has_more` 三键必填）；每项 `SnapshotView` 必填 11 键（`id, request_id, captured_at, upstream_url, backend_model, http_status, latency_ms, error_summary, model, deployment_id, snapshot_type`），`snapshot_type ∈ {upstream,error}`；`upstream_url` "去 query"、`error_summary` ≤256B、`http_status ∈ [100,599]|null`、`latency_ms ≥0|null`；认证角色 `admin`；失败走统一信封 `{error:{message,type,code,param,retryable}}`（401/403/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-SNAP`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-SNAPSHOT`、§4.9 `D-OBS-SNAPSHOT` 映射、§4.10、`CON-OBS-003` 不记录 Secret/credential/完整正文）；错误目录 `ERR-STORE` → `usage_store_unavailable`（503）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`/`CT-LOG-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`SnapshotPage`/`SnapshotView`，`security=AdminBearerAuth`）。**不证明什么**：不证明非法 cursor 的 400（OBS-SNAP-02）、不证明快照**写入**开关门控（`capture_snapshot` 受 `snapshots_enabled` 控制，属机制 `INV-4`/`CON-OBS-001` 与 OBS-DIAG-02 的开关写入，本 case 只读现有页）、不证明统计/trace（OBS-STATS-01、OBS-TRACE-01）、不证明别名等价（OBS-ALIAS-02）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线；`diagnostic_settings` 默认 `snapshots_enabled=false`，故若从未开启过快照，`items` 可能为空——**本 case 为形状/脱敏断言，不以非空为 PASS 前提**。本 case 纯读，初态即终态。
- **输入与构造**：固定请求（无 body，可选时间窗）：
  `GET /v1/diagnostics/snapshots?limit=50`（如需限定数据可加 `?since=<RFC3339>&until=<RFC3339>`；`limit∈[1,500]`），`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：**无请求体**；`limit` 取默认 50（不触 `limit=1` 分页，属 OBS-SNAP-02）；不构造非法 cursor（OBS-SNAP-02）；不写入、不注入；`items` 是否非空不固定，只断言页与项形状及脱敏不变量。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `GET /v1/diagnostics/snapshots?limit=50`（`admin_client`）→ 记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层键集**恰为** `{items, next_cursor, has_more}`；`items` 为数组、`has_more` 为 JSON 布尔、`next_cursor` 为字符串或 `null`。
  5. 对每个 `item`：断言键集**恰为** `SnapshotView` 11 键；`id`/`request_id`/`captured_at`/`upstream_url` 为字符串；`backend_model`/`model`/`deployment_id` 为字符串或 `null`；`http_status` 为 `null` 或在 `[100,599]`；`latency_ms` 为 `null` 或 ≥0；`error_summary` 为 `null` 或字符串且 UTF-8 长度 ≤256；`snapshot_type ∈ {"upstream","error"}`。
  6. **脱敏断言**：逐项扫描 `upstream_url`（不得含 `?` 后 query 串）、`error_summary`、以及整段原始 body：不得出现上游凭据字面 `9832`、`Authorization`、`Bearer `、key 文件内容或任何 secret 值。
  7. （交叉核对，不改变判定）若 `items` 非空，取末条 `id` 作为 `cursor` 重放 `GET ...&cursor=<id>`，确认只读分页可用；本 case 不承担 cursor 负向判定。
- **重点关注步骤**：① **页键集精确**——恰 3 键（`items`/`next_cursor`/`has_more`），多/少即违反；② **项键集精确**——每项恰 11 键，`additionalProperties:false`；③ **`snapshot_type` 枚举**——只允许 `upstream`/`error`（`upstream⇒http_status` 非空、`error⇒http_status` 空是机制 §4.2 不变量，可作交叉核对）；④ **`upstream_url` 去 query**——必须已剥离 `?` 后部分，这是 `D-OBS-SNAPSHOT` 的明确映射约束；⑤ **`error_summary` ≤256B**——按 UTF-8 截断，不得 >256；⑥ **脱敏不变量**——整段 body 不得含 `9832`/`Authorization`/secret；⑦ **空页合法**——`snapshots_enabled=false` 时 `items=[]` 仍是合法 `SnapshotPage`（形状 PASS），**不得**因空而判 FAIL；⑧ **降级/存储**——`_UnavailableDiagnostics.snapshots_page` 恒返回 `{items:[],next_cursor:null,has_more:false}` 的 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_snap_01.py`；落位按 §4.9/§8.5。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `SnapshotPage`/`SnapshotView` wire 形态 + 机制 §4.2/§4.9 脱敏映射（不依赖实现内部）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：`{"items":[...], "next_cursor": <string|null>, "has_more": <bool>}`，键集恰 3。
  - 项：键集恰为 11 键；类型/范围/枚举如上；`upstream_url` 无 query；`error_summary` ≤256B。
  - 脱敏：任何字段与整段响应均不含 Secret/凭据/上游 Bearer/完整正文。
  - **fail-open**：降级实例返回 `200` + 空 `SnapshotPage`，形状仍满足 Oracle → **PASS**（观测降级不得制造新失败面，且本 case 不要求非空）；若健康实例返回非 200、或页/项键集不符、或出现未脱敏内容 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 页键集恰 3 + 每项恰 11 键且类型/范围/枚举正确 + `upstream_url` 去 query + `error_summary` ≤256B + 无未脱敏内容（含降级空页 fail-open）。
  - **FAIL**：非 200（存储健康时）、页/项键集不符、`snapshot_type` 越枚举、`upstream_url` 含 query、`error_summary` >256B、或响应含 Secret/凭据。
  - **BLOCKED**：测试代码/契约问题（解析器/断言逻辑错、openapi 语义不清）或存储不可达 `503 usage_store_unavailable`——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air/双 OMLX 离线、tier 或资源缺失）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照、`redactions`（确认 `Authorization` 与任何上游 Bearer 已脱敏）；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读，不写 `diagnostic_snapshots`、不改开关、不创建/修改资源、不写注入、不新增 trace。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；M007 `diagnostic_snapshots`（`002_observability.sql`）；`SnapshotPage`/`SnapshotView` 机器契约；实现 [`src/libdiag/snapshots.py`](../../../../src/libdiag/snapshots.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_snap_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-SNAP-02（无效 cursor 负向）、OBS-DIAG-02（开关写）语义相邻但各自独立执行。
