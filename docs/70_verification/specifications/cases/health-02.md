# HEALTH-02 — readyz 就绪=全部 tier 可用

- **Case ID**：`HEALTH-02`（与 §3.2 权威清单一致；本文件名 `health-02.md`，唯一对应）。
- **标题**：`GET /readyz` 在全部 7 个 fixed tier 均 `available` 时返回 HTTP 200 + `ReadinessView{status:"ready", models[7]}`。
- **目的（被测契约）**：验证 IF-HEALTH 的**就绪聚合**契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`，`security:[]`，200 = `ReadinessView`）。实现 [`readiness_view`](../../../../src/http_api/health.py) 对 7 个 `FIXED_TIERS` 逐个聚合：某 tier 的候选 deployment `health=="healthy"` 计数 >0 ⇒ `availability="available"`；全部 7 个 `available` ⇒ `status="ready"`、HTTP 200（否则 503，见 HEALTH-03/04/05）。设计验证项 `VRC-MGMT-003`；机制 `T-OBS`（见 [observability 机制](../../../20_system_design/mechanisms/observability.md)）与 `T-CFG-BOOT`/`R-CFG-02`（见 [config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`VRC-UTIL-001/002`、`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明降级 `degraded`（HEALTH-03）、无 deployment `not_ready`（HEALTH-04）、bootstrap 失败（HEALTH-05）、health 端点的鉴权行为（HEALTH-06/AUTH-05）；不证明 `models[]` 中每 tier 的路由/推理可用（只证明 readiness 聚合字段）；不触发 provider 计费调用（`LT-OPS-001`）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `none`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 §2.1.2 `/readyz` 200 + 7 fixed tier；由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier，且 7 tier 均已探测为 `healthy`（否则 §2.1.2 不就绪，本 case 无法达成 ready）。本 case 纯读，不探测、不改 health。
- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /readyz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```

  边界/构造点：不携带凭据（端点 `security:[]`）；不构造非法输入；不改任何 deployment 的健康状态（`ready` 由 §2.1.6 的 m5air 基线资源与既有探测保证，不在此 case 重新 probe）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/readyz")`；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `status == "ready"`。
  5. 断言 `models` 为长度 **7** 的数组，元素 `id` 集合**恰为** `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`（与 `FIXED_TIERS`/§4.10 一致）。
  6. 断言每个 `models[]` 元素的 `availability == "available"`。
  7. （交叉核对）与 `GET /v1/models` 的 7 个 fixed tier 数量比对，佐证同一固定 tier 集合；本 case 不承担 `/v1/models` 的契约断言。
- **重点关注步骤**：① **`status` 必须是 `"ready"` 而非仅 200**——200 与 ready 在本实现同生（`readiness_view` 仅在全 available 时返回 200），但仍显式断言 `status=="ready"`。② **7 是精确数**——§4.10 与 `FIXED_TIERS` 固定 7 项；现有 [`at_obs_02.py`](../../../../tests/system/api_test_v03/at_obs_02.py) 已断言 `len(models)==len(FIXED_TIERS)` 且 `ids==set(FIXED_TIERS)`（无缺无多），本 case 与该精确集合/长度断言一致。③ **每 tier 必须 `available`**——任何 `degraded`/`unavailable` 都使整体不为 ready，须按对应 Case（HEALTH-03/04）处理，不得在本 case 判 PASS。④ **不得被错误信封冒充**——非 200 时确认是可解释状态（degraded/not_ready 的 `ReadinessView`，或环境错误），而非把 `{"error":...}` 当就绪体。⑤ **字段集**——`ReadinessView` `additionalProperties:false`，只允许 `{status, models}`；每个模型元素只允许 `{id, availability}`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ReadinessView` + §4.10 `/readyz` 状态定义（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)、[测试设计 §4.10](../llmtier-api-test-specification.md)），与 m5air 具体数据无关。
  - HTTP：`200`；`Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：键集**恰为** `{status, models}`；`status=="ready"`；`models` 长度 7，元素键集**恰为** `{id, availability}`，`id` = 7 个 fixed tier，`availability=="available"`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` + `status=="ready"` + `models` 恰为 7 个 fixed tier 且全 `available`。
  - **FAIL**：status ≠ 200，或 `status ≠ "ready"`，或 tier 集合/长度不符，或存在非 `available` 的 tier；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier 就绪等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 `127.0.0.1`/mock/替代路径冒充 m5air 真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 有实现（§3.2 `RUN`）但本轮未执行——见[测试设计 §9](../llmtier-api-test-specification.md)；不得补造为 PASS。
- **证据与 Run**：保存命令、exit code、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）。`manifest.json` 含 `target_artifact{git_commit,db_schema_version,openapi_version}` 与 `redactions`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/health-02/`，失败现场不截断。契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——纯读、无副作用、无凭据；不创建/修改资源、不写注入、不改 deployment health。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、`provider_omlx_m5mac` secret、§2.1.6 必需 provider/deployment）；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`health.py`](../../../../src/http_api/health.py)；自动化入口 [`at_obs_02.py`](../../../../tests/system/api_test_v03/at_obs_02.py)。**不依赖**其它 Case；与 HEALTH-03/04/05 同入口但状态互斥（ready / degraded / not_ready），各自独立执行。
