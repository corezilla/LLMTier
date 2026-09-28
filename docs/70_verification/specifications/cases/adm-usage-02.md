# ADM-USAGE-02 — 管理面分页

- **Case ID**：`ADM-USAGE-02`（与 §3.2 权威清单一致；本文件名 `adm-usage-02.md`，对应 §3.4 索引 `cases/adm-usage-02.md`）。
- **标题**：`GET /v1/usage?from&to&limit=1`（admin 视角）有界分页：HTTP 200 + `data.length ≤ 1` + 页元数据一致。
- **目的（被测契约）**：验证管理面 usage 的**有界分页与 cursor 元数据契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，query `limit` 默认 100/上限 200，`cursor` 可选）；[`UsageRecorder._page`](../../../../src/inference/usage.py) 冻结快照后 `LIMIT limit+1`，`more = len(rows) > limit`，返回 `next_cursor="<snapshot_id>:<offset+limit>" if more else None`，稳定排序 `(recorded_at,request_id)`。设计验证项 `VRC-MGMT-006`；机制 `T-MET-PAGE`；需求/机制链 `LT-FUN-004`、`R-MET-02`、`CT-USAGE-001`。**不证明什么**：不证明 cursor 跨页去重/重放（DP-USAGE-03/07）、不证明过期 cursor 400（DP-USAGE-04）、不证明清空（ADM-USAGE-03）、不证明 data 主体隔离（DP-USAGE-06）。本 case 只断 `limit=1` 边界与页元数据一致性。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。就绪检查同[测试设计 §2.1](../llmtier-api-test-specification.md)（**6** 项，`pytest_configure` 自动执行）。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。时间窗用动态 [`recent_window()`](../../../../tests/system/api_test_v03/constants.py)。只读（会写一条临时 `query_snapshots`）。
- **输入与构造**：
  ```http
  GET /v1/usage?from=<recent_window.from>&to=<recent_window.to>&limit=1 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`limit=1`（下界边界）；`from`/`to` 动态近窗；不传 `cursor`（首页）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/usage", params={"from": since, "to": until, "limit": 1})`。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `len(data) <= 1`；五键 `{data,next_cursor,has_more,snapshot_id,snapshot_at}` 齐全；`has_more` 为 bool。
  5. 断言一致性：`has_more is True ⇒ next_cursor` 非空且形如 `"<snapshot_id>:<offset>"`；`has_more is False ⇒ next_cursor is None`。
  6. （可选）用步骤 4 的 `next_cursor` 发第二页（同参数 + `cursor`），断言返回不重复且 `offset` 前进（本 case 不断言重放语义，仅作边界观察）。
- **重点关注步骤**：① **`limit=1` 边界**——首页返回条数必须 ≤1（空表 0 亦合法）；② **`next_cursor` 与 `has_more` 一致**——`has_more=true` 时 `next_cursor` 必须非空且 `snapshot_id` 前缀与 `body.snapshot_id` 相同（cursor 绑定本次快照）；③ **稳定排序**——`(recorded_at,request_id)`；本 case 只断首页结构；④ **读取副作用**——写临时 `query_snapshots`，非 FAIL 依据；⑤ **不硬编码条数**——是否 `has_more` 取决于 m5air 窗内记录数，不得硬编码为真/假。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `UsagePage` + `limit` 边界 + cursor 绑定规则。
  - HTTP：`200`；body `{"data":[...≤1...],"next_cursor":<str|null>,"has_more":<bool>,"snapshot_id":"snap_…","snapshot_at":<RFC3339>}`。
  - `has_more`/`next_cursor` 一致；`next_cursor` 前缀 == `snapshot_id`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `len(data)≤1` + 五键齐全 + `has_more`/`next_cursor` 一致（含 cursor 前缀绑定）。
  - **FAIL**：status 非 200、`len(data)>1`、缺键、或一致性违反。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或硬编码 `has_more` 期望——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL（含 limit）、原始 HTTP status/body、`snapshot_id`/`next_cursor`、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需业务 teardown**——只读；临时 `query_snapshots` 10 min TTL 自行过期。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`constants.recent_window`；`UsagePage` 机器契约；`UsageRecorder._page`；机制 `R-MET-02`/`T-MET-PAGE`。自动化入口 [`at_adm_admin_usage_02.py`](../../../../tests/system/api_test_v03/at_adm_admin_usage_02.py)。**不依赖**其它 Case；cursor 重放/过期属 DP-USAGE-03/04/07。
