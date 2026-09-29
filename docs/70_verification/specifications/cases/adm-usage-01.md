# ADM-USAGE-01 — 管理面 usage

- **Case ID**：`ADM-USAGE-01`（与 §3.2 权威清单一致；本文件名 `adm-usage-01.md`，对应 §3.4 索引 `cases/adm-usage-01.md`）。
- **标题**：`GET /v1/usage?from&to`（admin 视角）返回聚合用量页：HTTP 200 + `UsagePage`（`data`/`next_cursor`/`has_more`/`snapshot_id`/`snapshot_at`）。
- **目的（被测契约）**：验证管理面 usage 查询的**聚合读契约与页信封**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，`from`/`to` **必填**，query `model`/`request_id`/`cursor`/`limit` 可选，`security`=data 或 admin）；[`app.py`](../../../../src/http_api/app.py) 用 `_auth_either()`，admin 主体 `admin=True` 时 [`UsageRecorder._page`](../../../../src/inference/usage.py) **不加 principal 过滤**（见全局），返回 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`，窗口 `v.recorded_at>=from AND <to`（**半开**）、稳定排序 `(recorded_at,request_id)`。设计验证项 `VRC-MGMT-006`；机制 `R-MET-02`、`T-MET-FINAL`；需求/机制链 `LT-FUN-004`、`LT-OPS-002`、`CT-USAGE-001`。**不证明什么**：不证明 cursor 分页边界（ADM-USAGE-02）、不证明 `DELETE /v1/usage` 清空（ADM-USAGE-03）、不证明 data 主体隔离（DP-USAGE-06）、不证明 cursor 过期（DP-USAGE-04）、不证明缺窗 400（`/v1/usage` 缺 `from`/`to` 由 `app.py` 拒绝，未单独构 case）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；时间窗用动态 [`recent_window()`](../../../../tests/system/api_test_v03/constants.py)；初始状态=§2.3 A 类基线。
  > **实现注记**：无 `cursor` 的 usage 查询会向 `query_snapshots`/`query_snapshot_items` 写入一条 kind=`usage` 的冻结快照（10 min TTL，`next_cursor` 指向它）。这是读操作的持久化副作用；本 case 不断言它，清理见"清理与复位"。
- **输入与构造**：
  ```http
  GET /v1/usage?from=<recent_window.from>&to=<recent_window.to> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`from`/`to` 动态近窗；不传 `cursor`/`limit`（默认 `limit=100`）、不传 `model`/`request_id`（admin 全局视图）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/usage", params={"from": since, "to": until})`。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言五键齐全 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`（`UsagePage.required`）；`data` 为数组、`has_more` 为 bool、`snapshot_id` 为非空字符串、`snapshot_at` 为 RFC3339 字符串。
  5. 断言一致性：`has_more is False ⇒ next_cursor is None`（`UsagePage.allOf` 的 if/then）；`has_more is True ⇒ next_cursor` 为非空字符串（形如 `"<snapshot_id>:<offset>"`）。
  6. 抽查 `data` 元素含 `UsageRecord` 键 `{request_id,record_version,is_final,model,endpoint,recorded_at,updated_at,measurement_status,source,input_tokens,output_tokens,total_tokens,cached_input_tokens,cache_write_tokens,reasoning_tokens}`。
- **重点关注步骤**：① **页信封 identity**——五键缺一不可（与 `AdminPageMeta` 的 `{has_more,next_cursor}` 不同，`UsagePage` 多出 `snapshot_id`/`snapshot_at`）；② **admin 全局视图**——admin 主体不加 principal 过滤（data 主体仅见自身，属 DP-USAGE-06），本 case 只断结构不断言跨主体内容；③ **`snapshot_id`/`snapshot_at`**——无 cursor 请求必回填本次快照 id 与创建时间；④ **半开窗**——`[from,to)`；⑤ **读操作副作用**——第 2 步会写一条 `query_snapshots`，不得据此判 FAIL，也不得宣称绝对零写；⑥ **不硬编码数值**——`data` 条数与内容随 m5air 运行变化。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `UsagePage`/`UsageRecord` + 半开窗/稳定排序规则。
  - HTTP：`200`；body `{"data":[...],"next_cursor":<str|null>,"has_more":<bool>,"snapshot_id":"snap_…","snapshot_at":<RFC3339>}`。
  - `has_more` 与 `next_cursor` 一致。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 五键齐全 + 类型正确 + `has_more`/`next_cursor` 一致 + `data` 元素含 `UsageRecord` 键。
  - **FAIL**：status 非 200、缺任一页字段、类型错、一致性违反、或出现错误信封。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或硬编码时间窗——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL（含 from/to）、原始 HTTP status/body、`snapshot_id`/`snapshot_at`、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需业务 teardown**——只读查询不改账本/配置；查询写入的临时 `query_snapshots` 行有 10 min TTL、由服务自行过期，不作为残留清理对象。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`constants.recent_window`；`UsagePage`/`UsageRecord` 机器契约；`UsageRecorder._page`；机制 `R-MET-02`/`T-MET-FINAL`。自动化入口 [`at_adm_admin_usage_01.py`](../../../../tests/system/api_test_v03/at_adm_admin_usage_01.py)。**不依赖**其它 Case；与 ADM-USAGE-02/03 互补。
