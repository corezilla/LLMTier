# HEALTH-03 — readyz degraded

- **Case ID**：`HEALTH-03`（与 §3.2 权威清单一致；本文件名 `health-03.md`，唯一对应）。
- **标题**：`GET /readyz` 在某 tier 存在候选 deployment 但无 `healthy` 候选时返回 HTTP 503 + `ReadinessView{status:"degraded", models[7]}`（各 tier `availability="degraded"`）。
- **目的（被测契约）**：验证 IF-HEALTH 的**降级就绪**契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`）。实现 [`readiness_view`](../../../../src/http_api/health.py)：某 fixed tier 的候选 deployment 列表非空但 `health=="healthy"` 计数为 0 ⇒ 该 tier `availability="degraded"`；只要存在非 `unavailable` 且非全部 `available` ⇒ `status="degraded"`、HTTP 503。系统设计 §8.1 明确"bootstrap 成功后 deployments 初始 `health=unknown`，故先为 `degraded`"（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）。设计验证项 `VRC-MGMT-003`；机制 `T-OBS`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）、`T-CFG-BOOT`/`R-CFG-02`（[config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`VRC-UTIL-001/002`、`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明全可用 `ready`（HEALTH-02）、无候选 `not_ready`（HEALTH-04）、bootstrap 失败（HEALTH-05）；不证明探测/健康转换过程（`POST /v1/probes` 属 ADM-PROBE-*）、不证明推理路由可用；不触发 provider 计费调用（`LT-OPS-001`）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例：`127.0.0.1:<随机空闲端口>` + 临时 SQLite，同机第二个进程；见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。执行前必须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动且 `GET /healthz` 200。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：本 case 需要一个**已 bootstrap 基线资源但未探测 healthy** 的实例——等价于 `LLMTierInstance(_BASELINE_SETTINGS)`（`prov_b` + `depl_b` + 7 fixed tier，其 `service_levels` 的每个 tier 的 `deployment_ids` 均指向 `depl_b`；[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `_baseline_settings`），**但不调用** `_probe_deployment`。**不得复用 `llmtier_b` fixture**：它在启动时对 `depl_b` 探测到 `healthy`，会把 7 tier 全部翻成 `available`（那是 HEALTH-02 的 ready 形态）。因此本 case 依赖一个**尚未存在**的 fixture（如 `llmtier_b_unprobed`）。TS-003：`prov_b.endpoint` 必须是本机 **LAN IP** 上的 fake provider（不得用 `127.0.0.1` 作为被测服务的上游 endpoint）。初始状态 = 1 provider（`prov_b`）/ 1 deployment（`depl_b`，`health="unknown"`）/ 7 fixed tier，且 `diagnostic_injections` 为空。
- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  Accept: application/json
  ```

  边界/构造点：构造"有候选但无健康候选"——由 bootstrap 插入 `depl_b` 时 `health` 初始为 `"unknown"`（[`registry.py`](../../../../src/management/registry.py) `bootstrap_settings` 的 `INSERT INTO deployments ... 'unknown'`），且 7 tier 的 `deployment_ids` 均为 `["depl_b"]`，故每 tier `candidates` 非空、`healthy` 计数为 0 ⇒ `availability="degraded"`。**不在本 case 调用 `POST /v1/probes`**（保持 `unknown`，避免翻成 `healthy`）。备选构造：探测指向不可达上游的 `depl_b` 使其 `health` 变为 `unhealthy`（仍 `degraded`，因候选存在而健康为 0）；但"未探测"更确定、无上游依赖，优先。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）临时实例用 `_BASELINE_SETTINGS` 启动并轮询 `GET /healthz` 200；**不**执行 `_probe_deployment`；确认初始 `GET /readyz` 即为 `degraded`（若已是 `ready`，说明实例被误探测，判 BLOCKED/构造失败）。
  2. `GET /readyz`（上表）；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 503`。
  4. 解析 body：断言键集**恰为** `{status, models}`，`status == "degraded"`。
  5. 断言 `models` 长度为 7，`id` 集合恰为 `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`。
  6. 断言每个 `models[]` 元素 `availability == "degraded"`（存在候选、无 healthy）；逐元素键集恰为 `{id, availability}`。
  7. （清理）整班结束时由 fixture `stop()` 销毁实例。
- **重点关注步骤**：① **`degraded` 与 `not_ready`/`ready` 的区分**——`degraded` 要求"候选存在但无 healthy"；无候选是 `unavailable` ⇒ `not_ready`（HEALTH-04），全 healthy ⇒ `ready`（HEALTH-02）。构造错会把状态判错。② **不得复用 `llmtier_b`**——该 fixture 启动即 probe 成 `healthy`，会导致 `ready`；必须用未探测实例。③ **`status` 由聚合导出**——`ReadinessView.status` 不是独立字段，是 7 个 `availability` 的聚合；只断言 503 + status 而不逐 tier 校验会漏判。④ **字段集精确性**——`ReadinessView` `additionalProperties:false`，只允许 `{status, models}`；模型元素只允许 `{id, availability}`。⑤ **不得被错误信封冒充**——503 时必须确认 body 是 `ReadinessView` 而非 `{"error":...}`（本端点未鉴权、不走错误信封）。⑥ **TS-003**——`prov_b.endpoint` 必须为 LAN IP，构造失败时应 BLOCKED/SKIP 而非改用 `127.0.0.1` 冒充。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ReadinessView` + §4.10 `/readyz` 状态定义（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)、[测试设计 §4.10](../llmtier-api-test-specification.md)），不依赖实现内部数据。
  - HTTP：`503`；`Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：键集**恰为** `{status, models}`；`status=="degraded"`；`models` 长度 7，元素键集 `{id, availability}`，`id` = 7 个 fixed tier，`availability=="degraded"`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==503` + `status=="degraded"` + `models` 恰为 7 个 fixed tier 且全 `degraded`。
  - **FAIL**：status/字段/聚合不符——含误为 `ready`（被探测）或 `not_ready`（无候选），或返回错误信封；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：**无法构造"有候选但无健康候选"的确定性实例**——例如缺少未探测 fixture、实例启动即被探测成 healthy、或无法在 B 类实例上保留 `health=unknown`；或测试代码/断言不可实现（见[测试设计 §9](../llmtier-api-test-specification.md)）。本 case 当前 `自动化入口 = MISSING`（§3.2），无脚本时应按 §9 记为缺口而非 PASS。若实例根本起不来/`/healthz` 不就绪，属依赖失败，按 §9 视情形 BLOCKED 或 SKIP。
  - **SKIP**：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP 可用（TS-003）等 §2 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 当上游 endpoint，或以替代路径冒充真实临时实例——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case `自动化入口 = MISSING`（§3.2），本轮未执行；缺口引用见[测试设计 §9/§8.5](../llmtier-api-test-specification.md)（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
- **证据与 Run**：保存实例启动参数/settings（`_BASELINE_SETTINGS` 内容，脱敏后）、确认"未探测"的证据（未调用 `POST /v1/probes` 的请求日志）、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz` + `/readyz`）。`manifest.json` 含 `target_artifact{git_commit,db_schema_version,openapi_version}`、`environment:"b"` 与 `redactions`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，失败现场不截断。契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：B 类实例由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `shutil.rmtree` 临时目录销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）；本 case 只读 `/readyz`，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。（本 case 无 A 类污染风险。）
- **依赖**：B 类 fixture（**待新增**的"未探测基线"实例，如 `llmtier_b_unprobed`；**不可复用** `llmtier_b`）与 `_baseline_settings`/`provider_endpoint_b`（LAN fake provider，TS-003）（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`health.py`](../../../../src/http_api/health.py)；系统设计 §8.1 的 `degraded` 初始态（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；自动化入口：**`MISSING`**（§3.2；尚无 HEALTH-03 脚本——`at_obs_03.py` 承接的是 HEALTH-04，不承接本 case；落位按[测试设计 §4.9/§8.5](../llmtier-api-test-specification.md)）。**不依赖**其它 Case；与 HEALTH-02/04/05 同入口但状态互斥。
