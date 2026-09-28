# ADM-STATS-02 — 分组

- **Case ID**：`ADM-STATS-02`（与 §3.2 权威清单一致；本文件名 `adm-stats-02.md`，唯一对应）。
- **标题**：`GET /v1/stats?group_by=tier` 显式按 tier 分组：HTTP 200 + `group_by=="tier"` + tier 聚合行。
- **目的（被测契约）**：验证统计的**显式 `group_by=tier` 契约**。被测端点/规则：`GET /v1/stats`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getStats`，query `group_by` enum `tier|deployment`）；[`AdminService.stats`](../../../../src/management/admin.py) 在 `group_by=="tier"` 分支按 `v.model` 聚合（行含 `tier` 键）。设计验证项 `VRC-MGMT-006`；需求/机制链 `LT-FUN-006`、`R-MET-03`、`CT-USAGE-001`。**不证明什么**：不证明默认分组（ADM-STATS-01）、不证明 `group_by=deployment` 分支（未单独构 case）、不证明缺窗 400（ADM-STATS-03）、不证明非法 `group_by` 的 400（`group_by ∉ {tier,deployment}` → 400，未单独构 case）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。就绪检查同[测试设计 §2.1](../llmtier-api-test-specification.md)（**6** 项，`pytest_configure` 自动执行）。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。时间窗用动态 [`recent_window()`](../../../../tests/system/api_test_v03/constants.py)。初始状态 = m5air 基线；只读。
- **输入与构造**：
  ```http
  GET /v1/stats?from=<recent_window.from>&to=<recent_window.to>&group_by=tier HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：显式 `group_by=tier`（enum 合法值）；`from`/`to` 动态近窗；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/stats", params={"from": since, "to": until, "group_by": "tier"})`。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `group_by == "tier"`（回显）；`data` 为数组。
  5. 抽查每个 `data` 元素含 `tier` 键（非 deployment 分支的 `deployment_id` 等），且 `calls` 为 int、token 字段为 int。
  6. （可选）`model`/`tier` 值 ⊆ 已知 tier 集合或为空（不硬编码具体值）。
- **重点关注步骤**：① **显式分支回显**——`body.group_by` 必须为 `"tier"`；② **行形状区分**——tier 分支行含 `tier` 键、deployment 分支行含 `deployment_id`/`deployment_name`/`backend_model`/`provider_*`；本 case 锁定 tier 形状，不得混入 deployment 键；③ **空数据合法**——窗内无记录时 `data==[]`，仍 PASS（只断形状/回显）；④ **半开窗**——同 ADM-STATS-01（`[from,to)`）；⑤ **纯读**——不写库。
- **期望结果与独立 Oracle**：独立 Oracle = `AdminService.stats(stats,"tier")` 的 schema + enum 规则。
  - HTTP：`200`；body `{"from":…,"to":…,"group_by":"tier","data":[…]}`；`data` 元素含 `tier`/`calls`/`measured_calls`/`unknown_calls`/token 字段。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `group_by=="tier"` + `data` 为数组且元素为 tier 形状。
  - **FAIL**：status 非 200、`group_by` 回显错、`data` 非数组、行形状错（含 deployment 键）。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL（含 group_by）、原始 HTTP status/body、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`constants.recent_window`；`AdminService.stats` 的 tier 分支。自动化入口 [`at_adm_stats_02.py`](../../../../tests/system/api_test_v03/at_adm_stats_02.py)。**不依赖**其它 Case；与 ADM-STATS-01（默认分组）/03 互补。
