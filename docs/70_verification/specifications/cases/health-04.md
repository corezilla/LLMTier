# HEALTH-04 — readyz not_ready（无 deployment）

- **Case ID**：`HEALTH-04`（与 §3.2 权威清单一致；本文件名 `health-04.md`，唯一对应）。
- **标题**：`GET /readyz` 在无任何 deployment（无候选）时返回 HTTP 503 + `ReadinessView{status:"not_ready", models[7]}`（7 个 fixed tier 全 `availability="unavailable"`）。
- **目的（被测契约）**：验证 IF-HEALTH 的**不可用就绪**契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`）。实现 [`readiness_view`](../../../../src/http_api/health.py)：fixed tier 无候选 deployment ⇒ `availability="unavailable"`；全部 tier `unavailable` ⇒ `status="not_ready"`、HTTP 503。设计验证项 `VRC-MGMT-003` 与 `VRC-UTIL-001/002`；机制 `T-OBS`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）、`T-CFG-BOOT`/`R-CFG-02`（[config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明有候选但无健康候选的 `degraded`（HEALTH-03）、bootstrap 失败的 `not_ready`（HEALTH-05，后者 body 的 `models` 为空 `[]`）；不证明鉴权行为（HEALTH-06/AUTH-*）；不证明 `/v1/*` 的行为（bootstrap 成功时它们被错误信封/降级路径覆盖，不属本 case）；不触发 provider 计费调用（`LT-OPS-001`）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。执行前必须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动且 `GET /healthz` 200。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b_empty`（`_EMPTY_SETTINGS` = 三个空 section）与 `admin_client_b_empty`（[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py)）。初始状态的关键机制：`_EMPTY_SETTINGS` 是**合法 bootstrap**（含 `providers`/`deployments`/`service_levels` 三空 section，[`registry.py`](../../../../src/management/registry.py) `bootstrap_settings` 校验全通过），故 `app.bootstrap_error` 为 `None`；随后 `ensure_fixed_tiers()` 插入 7 个空 `service_levels`（`deployment_ids` 为空）。于是 7 tier 均无候选 ⇒ 全 `unavailable` ⇒ `not_ready`、503。**这与 HEALTH-05（bootstrap 失败 → `models:[]`）必须区分。**
- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  Accept: application/json
  ```

  边界/构造点：空库 + `_EMPTY_SETTINGS`，无 provider/deployment；`ensure_fixed_tiers()` 保证仍有 7 个 fixed tier 条目（但无 deployment 关联）。**不携带凭据**（端点 `security:[]`）。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b_empty` 启动并轮询 `/healthz` 200；确认 DB 中无 provider/deployment，但 7 tier 存在。
  2. `resp = admin_client_b_empty.get("/readyz")`（客户端凭据与契约无关；本端点不读 `Authorization`）；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 503`。
  4. 解析 body：断言键集**恰为** `{status, models}`，`status == "not_ready"`。
  5. 断言 `models` 长度为 7，`id` 集合恰为 `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`。
  6. 断言每个 `models[]` 元素 `availability == "unavailable"`，元素键集恰为 `{id, availability}`。
  7. （清理）整班结束时由 fixture `stop()` 销毁实例。
- **重点关注步骤**：① **`not_ready` vs `degraded`**——无候选是 `unavailable` ⇒ `not_ready`；有候选但无 healthy 是 `degraded`（HEALTH-03）。② **`models` 为 7（非 0）**——本例 `models` 是 7 个全 `unavailable` 的 fixed tier；HEALTH-05 的 bootstrap 失败才是 `models:[]`（[`app.py:188-189`](../../../../src/http_api/app.py) 短路）。若观测到 `models:[]` 说明命中了 bootstrap 失败路径而非本 case。③ **503 而非 200**——现有 [`at_obs_03.py`](../../../../tests/system/api_test_v03/at_obs_03.py) 已收紧为断言 `status_code == 503`（精确，不接受 200），并断言 body 键集恰为 `{status, models}`；本 case 与该精确断言一致。④ **字段集精确性**——`ReadinessView` `additionalProperties:false`，只允许 `{status, models}`；模型元素只允许 `{id, availability}`。⑤ **不得被错误信封冒充**——503 时确认是 `ReadinessView` 而非 `{"error":...}`。⑥ **构造正确性**——确认实例确为空库/无 deployment；若误用 `llmtier_b`（有 `depl_b`）会得到 `degraded`/`ready`。
- **期望结果与独立 Oracle**：独立 Oracle = 实现 [`src/http_api/app.py`](../../../../src/http_api/app.py) 的 `/readyz` 处理分支（[`app.py:188-190`](../../../../src/http_api/app.py)：503 返回 `ReadinessView`，**不是** `ErrorEnvelope`）+ [`src/http_api/health.py`](../../../../src/http_api/health.py) `readiness_view` 的聚合规则 + 系统设计 §8.1 `/readyz` 503 `ReadinessView{status:"not_ready", models:[...]}` 契约（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)），§4.10 状态定义见[测试设计 §4.10](../llmtier-api-test-specification.md)；`openapi` 的 `/readyz` 503 schema 已修正为 `ReadinessView`（`NotReady`），与代码 + §8.1 一致（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），故本 case 的 503 Oracle 以代码 + §8.1 为准，不依赖实现内部数据。
  - HTTP：`503`；`Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：键集**恰为** `{status, models}`；`status=="not_ready"`；`models` 长度 7，元素键集 `{id, availability}`，`id` = 7 个 fixed tier，`availability=="unavailable"`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==503` + `status=="not_ready"` + `models` 恰为 7 个 fixed tier 且全 `unavailable`。
  - **FAIL**：status ≠ 503（尤其误判为 200/PASS），或 `status ≠ "not_ready"`，或 `models` 长度/集合不符，或存在非 `unavailable` 的 tier，或 body 为错误信封；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如空库 fixture 写不出、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用、§2.1 附加就绪不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以替代路径冒充真实临时实例（如用 `127.0.0.1` 以外的假路径、mock 响应）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 有实现（§3.2 `RUN`：`at_obs_03.py`）但本轮未执行——见[测试设计 §9](../llmtier-api-test-specification.md)；不得补造为 PASS。
- **证据与 Run**：保存 `_EMPTY_SETTINGS` 内容、实例启动证据、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz` + `/readyz`）；manifest 与报告落位见 §4.8/§10（本 case `environment:"b"`）。
- **清理与复位**：B 类实例按 §4.7 由 fixture `stop()` + `shutil.rmtree` 临时目录销毁；本 case 只读 `/readyz`，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。
- **依赖**：`llmtier_b_empty` / `admin_client_b_empty` fixture 与 `_EMPTY_SETTINGS`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`ensure_fixed_tiers()` 的 7 tier 播种（[`registry.py`](../../../../src/management/registry.py)）；`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`health.py`](../../../../src/http_api/health.py) 与 [`app.py:188-190`](../../../../src/http_api/app.py)；自动化入口 [`at_obs_03.py`](../../../../tests/system/api_test_v03/at_obs_03.py)。**不依赖**其它 Case；与 HEALTH-03（degraded）、HEALTH-05（bootstrap 失败，`models:[]`）同入口但状态/body 互斥，各自独立执行。
