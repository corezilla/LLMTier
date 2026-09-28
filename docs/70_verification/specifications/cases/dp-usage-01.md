# DP-USAGE-01 — Usage 时间窗查询

- **Case ID**：`DP-USAGE-01`（与 §3.2 权威清单一致；本文件名 `dp-usage-01.md`，唯一对应）。
- **标题**：`GET /v1/usage` 以**动态时间窗**查询返回合法 `UsagePage`：`from`/`to` 必填且 `from<to`，`data[]` 全部落在 `[from,to)`，`next_cursor`/`has_more` 同步、含 `snapshot_id`/`snapshot_at`。
- **目的（被测契约）**：验证 Data Plane **Usage 查询的时间窗 + cursor 元数据契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`），`from`/`to` **必填** `date-time`，服务端按 `[from,to)`（`from` 含、`to` 不含）与稳定排序 `(recorded_at,request_id)` 返回 [`UsagePage`](../../../../interfaces/openapi/llmtier.openapi.json)（`data[]` + `next_cursor` + `has_more` + `snapshot_id` + `snapshot_at`，`additionalProperties:false`）；首屏在单事务内创建 `query_snapshots` 并冻结有序成员（实现 `src/inference/usage.py::UsageRecorder._page`）。设计验证项 `VRC-MGMT-006`；机制需求 `R-MET-02`；机制 `T-MET-PAGE`、`T-MET-FINAL`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.5/§4.7 CON-METER-004）；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`/`CT-STORE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；错误码 `invalid_request`（缺参/坏日期/`from>=to`）、`permission_denied`、`usage_store_unavailable`。**不证明什么**：不证明某次调用后的**记录内容/账本终态**（DP-USAGE-02，`T-MET-FINAL`）、不证明 `limit=1` 分页推进（DP-USAGE-03）、不证明过期 cursor 拒绝（DP-USAGE-04）、不证明主体隔离（DP-USAGE-06）、不证明 cursor 重放幂等（DP-USAGE-07）、不证明 store 不可用 → 503（DP-USAGE-08）、不证明 `DELETE /v1/usage`（ADM-USAGE-03）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，纯读/无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`、`provider_omlx_m5mac.secret_ref` 为 `file:`、必需 provider/deployment 已注册），由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`，`Authorization: Bearer dev-data`，dev-data 主体 principal_id=`consumer`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。**时间窗必须动态**：由 [`constants.recent_window()`](../../../../tests/system/api_test_v03/constants.py) 以 `now()` 生成最近窗口（默认 30×24 h），**禁止硬编码日期**，避免历史数据随日期迁移而失效。
- **输入与构造**：固定请求（动态窗口，无 body）：
  ```http
  GET /v1/usage?from=<now-30d>&to=<now> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```
  构造点：`from`/`to` 为 RFC3339 UTC（秒精度，`Z` 后缀），`from<to`；不传 `cursor`（首屏）、不传 `limit`（用默认 100）、不传 `model`/`request_id`（窗口全量）。不注入故障；不构造非法输入（缺参/坏日期归 DP-USAGE-05）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = api_client.get("/v1/usage", params={"from": since, "to": until})`；记录 status/headers。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`（非错误信封）。
  4. 解析 body：断言其为对象，键集**恰为** `{data,next_cursor,has_more,snapshot_id,snapshot_at}`（`additionalProperties:false`）。
  5. 断言 `data` 为数组；`has_more` 为 JSON 布尔；`next_cursor` 为 `null` 或非空字符串，且**当且仅当** `has_more=false` 时为 `null`（openapi `if/then` 不变式）；`snapshot_id` 非空字符串；`snapshot_at` 为 RFC3339 `date-time`。
  6. 对 `data` 每条记录断言 `UsageRecord` 必填键齐备（`request_id`/`record_version`/`is_final`/`model`/`endpoint`/`recorded_at`/`updated_at`/`measurement_status`/`source`/`input_tokens`/`output_tokens`/`total_tokens`/`cached_input_tokens`），`endpoint ∈ {"/v1/responses","/v1/embeddings"}`，`measurement_status ∈ {measured,estimated,unknown}`，`source ∈ {provider,gateway_estimate,unavailable}`；`unknown ⇒ 各 token 字段为 null`（`[usage-metering](../../../20_system_design/mechanisms/usage-metering.md)` INV-5）。
  7. 对每条记录断言 `recorded_at >= since` 且 `recorded_at < until`（`[from,to)` 边界）。
- **重点关注步骤**：① **时间窗动态化**——`from`/`to` 必须由执行时刻生成，不得写死；否则 A 类历史数据漂移导致假失败；② **`next_cursor`/`has_more` 同步**——不是"有 next_cursor 就行"，而是"`has_more=false ⇒ next_cursor=null`"这一 openapi 不变式；③ **键集精确**——`UsagePage` `additionalProperties:false`，多键/缺键即 FAIL；④ **`[from,to)` 半开区间**——`recorded_at == to` 的记录必须被排除，`== from` 必须包含；⑤ **不把错误当空页**——非 200 时必须确认是可解释的 `ERR-AUTH-*`/`ERR-STORE` 信封，而不是把错误体读成 `UsagePage`；⑥ **不夸大**——本 case **不**断言 `data` 非空（m5air 是否有记录由 DP-USAGE-02 承接），空 `data` + 合法 `snapshot_id`/`snapshot_at` 仍是 PASS。注意：现有 [`at_dp_usage_01.py`](../../../../tests/system/api_test_v03/at_dp_usage_01.py) 已覆盖步骤 3–5，但**未**断言步骤 4 的精确键集与步骤 6/7 的 `UsageRecord`/区间；本设计与脚本存在覆盖缺口，脚本须补齐后方可判本 Case PASS。
- **期望结果与独立 Oracle**：独立 Oracle = [`openapi` `UsagePage`/`UsageRecord`](../../../../interfaces/openapi/llmtier.openapi.json) 的 wire 形态 + 机制 `[from,to)`/稳定排序语义（不依赖实现的输出内容）。
  - HTTP：`200`；响应头 `Content-Type: application/json`。
  - body 键集恰为 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`；`data` 为数组，元素满足 `UsageRecord`。
  - `has_more=false ⇒ next_cursor is null`；`snapshot_id` 非空；`snapshot_at` 合法 RFC3339。
  - 每条 `data[].recorded_at ∈ [from,to)`；`measurement_status=unknown` 时 token 字段为 `null`（非 `0`）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集/类型/不变式、`UsageRecord` 必填项、`[from,to)` 区间与 unknown⇒null 全部 match。
  - **FAIL**：status 非 200（存储健康时）、键集不符、`has_more`/`next_cursor` 不变式破裂、记录字段/枚举错、`recorded_at` 越界、unknown 却填 0。
  - **BLOCKED**：测试代码/契约本身问题（断言不可实现、解析器错）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时记 `NOT_RUN`，不得以未跑冒充 PASS。
- **证据与 Run**：保存原始请求（含动态 `from`/`to` 实际值）、HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）。每 Case `manifest.json` 含被测版本锁定 `target_artifact`（`git_commit`/`db_schema_version`/`openapi_version`）与 `redactions`（`Authorization` 脱敏）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/dp-usage-01/`，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为纯读 `GET`，不改 provider/deployment/service-level、不写注入项、不删除用户 usage；唯一副作用是服务端创建一条 10 分钟 TTL 的 `query_snapshots` 首屏快照（只读查询的正常产物，非需复位状态）。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；[`constants.recent_window()`](../../../../tests/system/api_test_v03/constants.py) 动态窗口；`UsagePage`/`UsageRecord` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；机制 [`usage-metering` §4.5/§4.7](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 [`at_dp_usage_01.py`](../../../../tests/system/api_test_v03/at_dp_usage_01.py)。**不依赖**其它 Case；与 DP-USAGE-02/03（记录可见/分页）、DP-USAGE-05（缺参负向）语义相邻但各自独立执行。
