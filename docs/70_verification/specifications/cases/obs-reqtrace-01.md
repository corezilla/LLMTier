# OBS-REQTRACE-01 — 请求全生命周期 trace

- **Case ID**：`OBS-REQTRACE-01`
- **标题**：`GET /v1/trace/{request_id}` 返回单请求全生命周期 `TraceView`：`stages` 有序且覆盖 `received…completed`，并组合 `snapshot`/`usage`。
- **目的（被测契约）**：验证 Observability `GET /v1/trace/{request_id}` 的**单请求全生命周期只读契约**。被测端点/规则：`GET /v1/trace/{request_id}`，成功返回 `TraceView`（键集恰 `{request_id, correlation_id, stages, snapshot, usage}`）；`stages` `minItems:1` 且按 `timestamp` 升序（机制 `INV-5`）；`snapshot` 为 `null` 或 `SnapshotView`、`usage` 为 `null` 或 `UsageView`；该视图**组合** `trace_events`（trace）+ `diagnostic_snapshots`（快照）+ `usage_record_versions`（账本）（[`src/libdiag/traces.py`](../../../../src/libdiag/traces.py) `_trace_view`）；认证 `admin`；错误走统一信封（401/403/404/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-TRACE`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-TRACE`、§4.9 `D-OBS-TRACE` 映射、§4.10 `INV-5`）；错误目录 `ERR-NOTFOUND`/`ERR-STORE`；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`TraceView`/`TraceStage`/`SnapshotView`/`UsageView`，`security=AdminBearerAuth`）。**不证明什么**：不证明未知 id 的 404（OBS-REQTRACE-02）、不证明 data token 的 403（OBS-REQTRACE-03）、不证明注入命中（DP-RESP-11/22 的 trace `source=injected` 证明）、不证明 trace 列表去重/分页（OBS-TRACE-01/02）、不证明别名等价（OBS-ALIAS-03）。`X-Request-ID` 仅用于获取 `request_id` 的 harness 机制，**不是**本 case 的 Oracle（openapi 未声明 200 响应头）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin` 读 + 一次 `data` 推理调用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；就绪检查含 7 tier 与 responses-capable 上游。fixture：`admin_client`（`admin`）、`api_client`（`data`）（[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态=§2.3 A 类基线；`trace_events` **无开关、始终写**（机制 §4.10 `CON-OBS-001`）。本 case 产生一次 `store=false` 的无状态推理调用（不落账本配置变更）。
- **输入与构造**：
  1. 制造一条 trace（`data` 面，固定 prompt）：`POST /v1/responses` body `{"model":"Worker","input":[{"role":"user","content":"Hello"}],"stream":true,"store":false,"max_output_tokens":50}`（成功路径；若上游不稳可用 `Senior` 等 responses-capable tier）。该请求写入 `received`/`validated`/`routed`/`upstream_started`/`upstream_ended`/`completed` 等 stage（[`src/inference/responses.py`](../../../../src/inference/responses.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)）。
  2. **取得 `request_id`（harness，非 Oracle）**：优先 `GET /v1/diagnostics/traces?limit=1`（`admin_client`）取最新一条 `items[0].request_id`（列表按 `first_ts DESC`，最新请求在首）；或读取被测响应头 `X-Request-ID`（运行时注入，**不作契约断言**）。若列表为空则本 case 无数据可查，判 BLOCKED/SKIP。
  3. 查询：`GET /v1/trace/<request_id>`、`Authorization: Bearer dev-admin`。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `POST /v1/responses`（`api_client`，上表 body，流式读取至结束；不把生成内容当 oracle）。
  3. `GET /v1/diagnostics/traces?limit=1` → 取 `items[0].request_id`（若为 `None`/空则 BLOCKED/SKIP）。
  4. `GET /v1/trace/<request_id>`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  5. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  6. 解析 JSON，断言键集**恰为** `{request_id, correlation_id, stages, snapshot, usage}`；`request_id` 等于查询 id；`correlation_id` 字符串或 `null`。
  7. 断言 `stages` 为数组且长度 ≥1；每 `stage` 键集恰 `{stage, timestamp, detail}`；`stages` 的 `timestamp` 序列非降序（`INV-5`）。
  8. 断言本次成功请求的 `stages` 至少包含一个 **上游阶段**（`stage` 含 `upstream_started`/`upstream_ended`）与入口阶段（`received`）——"全生命周期"的结构证据；若仅有 `received` 而缺上游阶段，说明组合不完整，判 FAIL（或若响应为可解释错误，允许结构相应缩减，需在证据中说明）。
  9. 断言 `snapshot` 为 `null` 或合法 `SnapshotView`（11 键）；`usage` 为 `null` 或合法 `UsageView`（8 键：`record_version,is_final,model,input_tokens,output_tokens,total_tokens,measurement_status,source`）。
- **重点关注步骤**：① **全阶段组合**——不是"200 即可"，而是 `stages` 覆盖入口到上游结束的完整链且有序（`INV-5`）。② **键集精确**——`TraceView` 恰 5 键、`TraceStage` 恰 3 键。③ **`request_id` 回指**——返回的 `request_id` 必须等于查询 id（同一资源）。④ **`snapshot` 可为 `null`**——`snapshots_enabled=false`（m5air 默认）时 `snapshot=null` **合法**，不得判 FAIL；开启后应出现 `snapshot`。⑤ **`usage` 组合**——来自 `usage_record_versions` 最新版，`null` 合法（尚未记账），但成功请求通常有记录。⑥ **取得 id 的手段不是 Oracle**——`X-Request-ID`/traces 列表仅用于 harness；不得把响应头本身列入断言。⑦ **不依赖模型答案**——只断言结构/阶段，不写"答案正确"。⑧ **降级/存储**——`_UnavailableDiagnostics.trace` 对任意 id 返回 `{stages:[],...}` **200**，`stages=[]` 违反 `minItems:1`，属降级实例 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_reqtrace_01.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `TraceView`/`TraceStage`/`SnapshotView`/`UsageView` wire 形态 + 机制 §4.2/§4.10（`stages` 有序、组合快照/账本）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：键集恰 `{request_id, correlation_id, stages, snapshot, usage}`；`request_id` == 查询 id；`stages` ≥1 且 `timestamp` 非降序；每 stage 恰 3 键；成功请求含入口+上游阶段。
  - `snapshot`：`null` 或 11 键 `SnapshotView`；`usage`：`null` 或 8 键 `UsageView`。
  - **fail-open**：降级实例返回 `stages=[]` 视图——因违反 `minItems:1` 且无法证明组合，判 **BLOCKED/SKIP**（不把空 stages 当 PASS）；健康实例非 200、键集不符、stages 乱序/为空、或 request_id 不匹配 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 键集恰 5 + `request_id` 回指 + `stages` ≥1 有序且含入口/上游阶段 + `snapshot`/`usage` 类型正确。
  - **FAIL**：非 200（存储健康时）、键集不符、`request_id` 不匹配、`stages` 为空/乱序、或成功请求缺上游阶段。
  - **BLOCKED**：测试代码/契约问题、无法取得 `request_id`（trace 列表为空）、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（含 responses-capable 上游离线）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存制造请求及其响应（SSE 或可解释错误）、取得 `request_id` 的 traces 列表、`GET /v1/trace/{id}` 原始 status/headers/body、`stages` 有序证据、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——`store=false` 无状态、A 类只读；不写配置/注入、不删除既有资源。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client`/`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；responses-capable tier（`Worker`/`Senior`）；M007 `trace_events`/`diagnostic_snapshots` + 账本 `usage_record_versions`；`TraceView` 等机器契约；实现 [`src/libdiag/traces.py`](../../../../src/libdiag/traces.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)、[`src/inference/responses.py`](../../../../src/inference/responses.py)。自动化入口 `at_obs_reqtrace_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-REQTRACE-02/03（负向）、OBS-TRACE-01（列表去重）语义相邻但各自独立执行。
