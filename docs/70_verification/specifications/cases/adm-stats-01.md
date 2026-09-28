# ADM-STATS-01 — 统计聚合

- **Case ID**：`ADM-STATS-01`（与 §3.2 权威清单一致；本文件名 `adm-stats-01.md`，唯一对应）。
- **标题**：`GET /v1/stats?from&to` 返回时间窗内 token 用量聚合：HTTP 200 + `{from,to,group_by,data[]}`（半开窗 `[from,to)`）。
- **目的（被测契约）**：验证管理统计的**聚合读契约与半开时间窗**。被测端点/规则：`GET /v1/stats`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getStats`，query `from`/`to` **必填**，`group_by∈{tier,deployment}` 默认 `tier`，`security=AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 缺 `from`/`to` → 400；[`AdminService.stats`](../../../../src/management/admin.py) 以 `v.recorded_at>=? AND v.recorded_at<?`（**半开**）聚合 `usage_record_versions`（只计 head version），返回 `{from,to,group_by,data[]}`。设计验证项 `VRC-MGMT-006`；需求/机制链 `LT-FUN-006`、`R-MET-03`、`T-MET-FINAL`、`CT-USAGE-001`。**不证明什么**：不证明 `group_by=tier` 的显式分支细节（ADM-STATS-02）、不证明缺时间窗 400（ADM-STATS-03）、不证明 usage 分页（ADM-USAGE-02）、不证明账本写入时机（DP-USAGE-02）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`。时间窗用 [`constants.recent_window()`](../../../../tests/system/api_test_v03/constants.py)（**动态**：`now-30d … now`，RFC3339 `Z`，秒精度），不得硬编码日期。初始状态 = m5air 基线；本 case 只读。
- **输入与构造**：
  ```http
  GET /v1/stats?from=<recent_window.from>&to=<recent_window.to> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`from`/`to` 取动态近窗口（覆盖 m5air 既有 usage）；不显式传 `group_by`（用默认 `tier`）；不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/stats", params={"from": since, "to": until})`；记录 status、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言含 `from`、`to`、`group_by`、`data` 四键；`from==since`、`to==until`（回显）、`group_by=="tier"`（默认）、`data` 为数组。
  5. 抽查每个 `data` 元素键集含 `{tier,calls,measured_calls,unknown_calls,input_tokens,output_tokens,total_tokens,cached_tokens,cache_write_tokens,reasoning_tokens}`（`AdminService.stats` 的 tier 分支，`admin.py:59-61`），且 `calls` 为 int。
  6. （可选）交叉核对：`request_id` 型查询——本 case 不断言具体数值，只断结构。
- **重点关注步骤**：① **半开窗**——SQL 条件为 `>=from AND <to`；记录恰好落在 `to` 的记录不计入（可在报告中说明，但本 case 主断言为聚合结构）；② **必填 query**——`from`/`to` 缺任一 → 400（ADM-STATS-03），本 case 必传；③ **回显一致性**——`body.from/to` 必须等于请求参数（未做时区/格式改写）；④ **默认 `group_by`**——不传时为 `"tier"`（实现 `query.get("group_by",["tier"])`）；⑤ **只计 head version**——聚合 join `usage_heads` 且 `record_version=head_record_version`，不得重复计历史版本（结构断言，不断言总数）；⑥ **纯读**——`stats` 直接查库，不创建 `query_snapshots`。
- **期望结果与独立 Oracle**：独立 Oracle = `AdminService.stats` 的返回 schema + 半开窗规则。
  - HTTP：`200`；body `{"from":<since>,"to":<until>,"group_by":"tier","data":[...]}`。
  - `data` 元素为 tier 聚合行，键集为上述 10 键；`calls` 等为 int。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 四键齐全 + `from`/`to` 回显一致 + `group_by=="tier"` + `data` 为数组且元素键集正确。
  - **FAIL**：status 非 200、缺键、回显不符、`data` 非数组、元素键集错、或出现错误信封。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或硬编码日期窗冒充动态窗——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL（含 from/to）、原始 HTTP status/body、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs(时间窗),oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——纯读，不改账本/配置/注入。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`constants.recent_window`；`AdminService.stats`；机制 `R-MET-03`/`T-MET-FINAL`。自动化入口 [`at_adm_stats_01.py`](../../../../tests/system/api_test_v03/at_adm_stats_01.py)。**不依赖**其它 Case；与 ADM-STATS-02（显式 group_by=tier）/03（缺窗 400）互补。
