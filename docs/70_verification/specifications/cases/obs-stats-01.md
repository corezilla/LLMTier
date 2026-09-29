# OBS-STATS-01 — 诊断统计窗口

- **Case ID**：`OBS-STATS-01`
- **标题**：`GET /v1/diagnostics/stats` 返回按小时桶聚合的 `StatsView`：顶层恰 `{windows}`，每窗口为恰好 13 键的 `StatsWindow`（状态分布、请求/错误计数、4xx/5xx、延迟分位）。
- **目的（被测契约）**：验证 Observability `GET /v1/diagnostics/stats` 的**只读聚合契约**。被测端点/规则：`GET /v1/diagnostics/stats?since=<RFC3339>&until=<RFC3339>[&deployment_id=&model=]`，`since`/`until` **必填**；返回 `StatsView`（顶层键集恰 `{windows}`）；每 `StatsWindow` 必填 13 键（`stat_hour, deployment_id, model, status_breakdown, error_4xx_count, error_5xx_count, request_count, error_count, latency_p50_ms, latency_p95_ms, latency_min_ms, latency_max_ms, latency_sum_ms`）；`stat_hour` 匹配 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}$`（小时桶）；认证 `admin`；失败走统一信封 `{error:{message,type,code,param,retryable}}`（401/403/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-STATS`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-STATS`、§4.9、§4.10 "统计持久、样本缺失时百分位为 null 而非 0"）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`StatsView`/`StatsWindow`，`security=AdminBearerAuth`）。**不证明什么**：不证明缺 `since`/`until` 的 400（OBS-STATS-02）、不证明 `stats_enabled` 写入门控的业务效果（机制 `INV-4`/`CON-OBS-001`）、不证明 `/v1/stats`（管理面聚合，ADM-STATS-01..03）、不证明快照/trace（OBS-SNAP-01、OBS-TRACE-01）、不证明别名等价（OBS-ALIAS-05）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线；`stats_enabled` 默认 false，若从未开启过统计，`windows` 可能为空——**本 case 为形状/类型断言，不以非空为 PASS 前提**。本 case 纯读，初态即终态。
- **输入与构造**：固定请求（无 body，时间窗取足够宽以容纳现有数据）：
  `GET /v1/diagnostics/stats?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z`、`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：`since`/`until` 必须是 RFC3339 date-time；实现按 `since[:13]`/`until[:13]` 取小时桶（[`src/libdiag/stats.py`](../../../../src/libdiag/stats.py)）；不构造缺参（OBS-STATS-02）；不注入、不写入；`windows` 是否非空不固定。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/stats?since=...&until=...`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层键集**恰为** `{windows}`；`windows` 为数组。
  5. 对每个 `window`：断言键集**恰为** 13 键；`stat_hour` 匹配 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}$`；`deployment_id`/`model` 为字符串或 `null`；`status_breakdown` 为对象（值 ∈ 非负整数）；`error_4xx_count`/`error_5xx_count`/`request_count`/`error_count` 为非负整数；`latency_p50_ms`/`latency_p95_ms`/`latency_min_ms`/`latency_max_ms` 为 `null` 或数值；`latency_sum_ms` 为数值（≥0；无样本为 0）。
  6. （`deployment_id`/`model` 过滤交叉核对，不改变判定）带 `&deployment_id=dep_omlx_qwen36` 再请求一次，断言 200 且过滤窗口的 `deployment_id` 均等于该值；本 case 不承担过滤语义判定。
- **重点关注步骤**：① **顶层键集精确**——恰 `{windows}`（`additionalProperties:false`）；② **窗口键集精确**——恰 13 键；③ **`stat_hour` 形状**——小时桶字符串，不是完整 timestamp、不是毫秒；④ **计数类型**——计数键必须是非负整数（不是字符串/浮点/`null`）；⑤ **百分位 `null` vs 0**——无延迟样本时 `latency_p50/p95/min/max` 必须为 `null`，`latency_sum_ms` 为 `0`（机制 §4.10 明确"样本缺失 → null 而非 0"）；⑥ **空 `windows` 合法**——`stats_enabled=false` 或无数据时 `{"windows":[]}` 仍合法形状（PASS），**不得**因空判 FAIL；⑦ **降级/存储**——`_UnavailableDiagnostics.stats` 恒返回 `{"windows":[]}` 的 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_stats_01.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `StatsView`/`StatsWindow` wire 形态 + 机制 §4.2/§4.10 聚合语义（不依赖实现内部计数）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：`{"windows":[...]}`，顶层键集恰 1；每窗口恰 13 键且类型/范围/`stat_hour` 形状如上。
  - 空窗口：`windows=[]` 合法。
  - **fail-open**：降级实例 `200 + {"windows":[]}` → **PASS**（本 case 不要求非空）；健康实例非 200、键集/类型/形状不符、百分位该 `null` 却为 `0` → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `{windows}` 顶层键集 + 每窗口恰 13 键且类型/范围/`stat_hour` 正确（含空窗口 fail-open）。
  - **FAIL**：非 200（存储健康时）、键集不符、计数非整数、`stat_hour` 形状错、或样本缺失百分位错为 0。
  - **BLOCKED**：测试代码/契约问题或存储不可达 `503 usage_store_unavailable`——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存原始 HTTP status/headers/body、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读，不写 `data_plane_stats`/`data_plane_latency_samples`、不改开关、不注入。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；M007 `data_plane_stats`/`data_plane_latency_samples`（`002_observability.sql`）；`StatsView`/`StatsWindow` 机器契约；实现 [`src/libdiag/stats.py`](../../../../src/libdiag/stats.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_stats_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-STATS-02（缺参 400）、OBS-DIAG-02（开关写）语义相邻但各自独立执行。
