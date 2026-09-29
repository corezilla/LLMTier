# ADM-SL-01 — 列出 service-levels

- **Case ID**：`ADM-SL-01`（与 §3.2 权威清单一致；本文件名 `adm-sl-01.md`，唯一对应）。
- **标题**：`GET /v1/service-levels` 返回全部固定 Tier：HTTP 200 + `ServiceLevelPage` 的 `data[]` 含 7 个 `FIXED_TIERS`。
- **目的（被测契约）**：验证 Management Service Level CRUD 的**列表契约**。被测端点/规则：`GET /v1/service-levels`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listServiceLevels`，`security=AdminBearerAuth`，query `cursor`/`limit`），成功 `200` + `ServiceLevelPage`（`{data:[ServiceLevelView], page:{has_more,next_cursor}}`，`additionalProperties:false`）；`data[]` 为固定 Tier 集合（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`，[`registry.list_service_levels`](../../../../src/management/registry.py) 按 `FIXED_TIERS` 顺序、只列已存在者）。设计验证项 `VRC-MGMT-002`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-CAS`、`T-CFG-SPACE`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明单条详情（ADM-SL-03）、不证明创建/更新/删除（ADM-SL-02/02b/04/04b/05/06/07/08）、不证明分页 cursor 语义（本 case 7 条 < 默认 limit 100，`has_more=false`）、不证明成员能力交集计算（ADM-SL-06）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。
  > **实现注记**：列表走 [`AdminService.page`](../../../../src/management/admin.py) 的 cursor 冻结页，**无 cursor 时会向 `query_snapshots`/`query_snapshot_items` 写入一条 kind=`admin:service-levels` 的临时快照**（10 min TTL）。这是读操作的实现副作用，非被测契约；本 case 不断言该写，清理见"清理与复位"。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/service-levels HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：不传 `cursor`/`limit`（用默认 `limit=100`，确保 7 条一页返回）；凭据固定 `admin`；不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/service-levels")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言为对象、含 `data`（数组）与 `page`（对象）；`page` 键集恰为 `{has_more,next_cursor}`（`AdminPageMeta`）。
  5. `ids = {s["id"] for s in data}`；断言 `set(FIXED_TIERS) - ids == set()`（7 个固定 Tier 全在，A 类基线无缺口）。
  6. 抽查每个元素满足 `ServiceLevelView` 必填键 `{id,deployment_ids,enabled,capabilities,version}`；`enabled` 为 bool、`version≥1`、`capabilities` 为 12 键对象（`ModelCapabilities`）。
- **重点关注步骤**：① **数据完整性而非仅 200**——必须核对 7 个固定 Tier 一个不缺（`sorted(missing)==[]`），不能只断言 status；② **页信封形状**——`ServiceLevelPage.additionalProperties:false`，`data`/`page` 两键必在，`page` 恰为 `{has_more,next_cursor}`；③ **固定 Tier 身份**——只列 `FIXED_TIERS`，不得出现自定义 id（自定义 id 在 A 类不应存在；若出现即 FAIL）；④ **读操作副作用**——理解第 2 步会写一条临时 `query_snapshots`，不得据此把它当作"创建了资源"误判 FAIL，也不得声称绝对零写；⑤ **不依赖值**——`deployment_ids`/`capabilities` 具体值以 m5air 现状为准，本 case 只断结构。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelPage`/`ServiceLevelView`/`AdminPageMeta` 的 wire 形态。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：`{"data":[...7 ServiceLevelView...],"page":{"has_more":false,"next_cursor":null}}`。
  - `data` 中 `id` 集合 = `{Senior,Junior,Worker,Associate,Engineer,Executor,Embedding-v1}`。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 `data` 为数组、7 个固定 Tier 齐全、元素含 `ServiceLevelView` 必填键、`page` 键集正确。
  - **FAIL**：任一断言不符（status 错、缺 Tier、`data`/`page` 形状不符、出现错误信封）。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需业务 teardown**——本 case 只读，不创建/修改/删除资源、不写注入。列表实现写入的临时 `query_snapshots` 行有 10 min TTL、由服务自行过期，不作为残留清理对象。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ServiceLevelPage` 机器契约；`registry.list_service_levels`/`FIXED_TIERS`。自动化入口 [`at_adm_sl_01.py`](../../../../tests/system/api_test_v03/at_adm_sl_01.py)。**不依赖**其它 Case；与 ADM-SL-03（单条详情）互补。
