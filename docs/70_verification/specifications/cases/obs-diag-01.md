# OBS-DIAG-01 — 读取诊断开关

- **Case ID**：`OBS-DIAG-01`
- **标题**：`GET /v1/diagnostics` 读取全局诊断开关：HTTP 200 + 精确 `SwitchState` 字段集/类型（`snapshots_enabled`、`stats_enabled` 均为布尔），纯读、无副作用。
- **目的（被测契约）**：验证 Observability `GET /v1/diagnostics` 的**开关读契约**。被测端点/规则：`GET /v1/diagnostics`，成功返回 `SwitchState`（`snapshots_enabled`、`stats_enabled` 两个必填 JSON 布尔，`additionalProperties:false`）；认证角色 `admin`；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（401 `authentication_required` / 403 `permission_denied` / 503 `usage_store_unavailable`）。设计验证项 `VRC-DIAG-001`；机制 `T-OBS-SWITCH`（见[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.1/§5.1，`IF-OBS-API-SWITCH`/`IF-OBS-SWITCH`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01`/`R-OBS-02`、`CT-ADMIN-001`/`CT-LOG-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 `interfaces/openapi/llmtier.openapi.json`（`SwitchState`，`security=AdminBearerAuth`）；等价别名 `/tier/admin/v1/diagnostics`（同一 handler）。**不证明什么**：本 case 只读、不改变开关，**不证明**开关值对写入的零写入语义（机制 `INV-4`/`CON-OBS-001`，见 OBS-DIAG-02 的 PATCH 及其后的写入断言），**不证明**快照/统计/trace 查询（OBS-SNAP-01/02、OBS-STATS-01/02、OBS-TRACE-01/02），**不证明**别名逐字节等价（OBS-ALIAS-01），**不证明** `PATCH` 的非法值拒绝（OBS-DIAG-03），也**不证明**角色负向（data token 403，由 AUTH-08 及 OBS-REQTRACE-03 风格的角色负向承接）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `admin`，只读/无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 5 项就绪检查（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`、`provider_omlx_m5mac.secret_ref` 为 `file:`）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`（`httpx.Client`，`Authorization: Bearer dev-admin`，定义于 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py)）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；`diagnostic_settings` 单行存在（M007 迁移 `002_observability.sql` 以 `INSERT OR IGNORE ... VALUES(1,0,0)` 建表并播种），即默认 `{snapshots_enabled:false, stats_enabled:false}`。本 case 不写库、不改开关，初态即终态。
- **输入与构造**：固定请求（无 body、无查询参数）：

  ```http
  GET /v1/diagnostics HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```

  边界/构造点：**无请求体**（GET 不携带 body）；**无查询参数**（`SwitchState` 读取不接受参数，注入无关 query 不在本 case 范围）；凭据固定为 `admin`（`dev-admin`）；不注入故障；不构造非法输入（非法/缺凭据属 AUTH-*，非法 PATCH body 属 OBS-DIAG-03）。值的期望**不固定**（开关默认关闭，但 m5air 实际值以读取为准），只断言字段集与类型。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `GET /v1/diagnostics`（上表），`resp = admin_client.get("/v1/diagnostics")`；记录 status、`Content-Type`、`X-Request-ID`。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON body，断言其为对象且键集**恰为** `{snapshots_enabled, stats_enabled}`（不多不少；`additionalProperties:false`）。
  5. 断言两键值类型均为 JSON 布尔（`type(v) is bool`，不得把 `0/1` 当 `true/false`）。
  6. （交叉核对，不改变本 case 判定）与别名 `GET /tier/admin/v1/diagnostics` 同凭据下的响应体逐字节比对，作为 OBS-ALIAS-01 的旁证；本 case 不承担别名等价判定。
- **重点关注步骤**：① **字段集精确性**——不是"含两个字段"，而是"键集恰好等于 `SwitchState`"，多一个键即违反 `additionalProperties:false`；② **类型精确性**——`snapshots_enabled`/`stats_enabled` 必须是 JSON 布尔，不能是 `0/1`/字符串；③ **纯读、无副作用**——GET 不得写 `diagnostic_settings`（不改开关）、不得写审计（机制 §5.1 明确 PATCH 才"副作用=同事务审计"）、不得新增 trace；④ **不得被错误信封冒充**——若返回非 200，需确认是可解释的 `ERR-AUTH-*`/`ERR-STORE`，而非把错误体当 `SwitchState` 读；⑤ **不依赖开关值**——不对 `true/false` 做业务断言（m5air 实际值未知，默认关）；⑥ **降级判定**——区分"诊断服务降级返回默认 `SwitchState`"（仍 200，PASS）与"存储不可达返回 503 `usage_store_unavailable`"（环境问题，非本 case 的契约 FAIL，见判定）。注意：本 case 当前 `MISSING`（§3.2），尚无自动化入口 `at_obs_diag_01.py`，其落位与命名须遵循 §4.9/§8.5（`at_<family>_<seq>.py`）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `SwitchState` 的 wire 形态（不依赖实现的开关值）。
  - HTTP：`200`；响应头 `Content-Type: application/json`；`X-Request-ID` 存在。
  - body：JSON 对象，键集**恰为** `{snapshots_enabled, stats_enabled}`；两键均存在且为 JSON 布尔。
  - 值域：无额外约束（默认 `{false,false}`，实际值以库中 `diagnostic_settings.singleton=1` 行为准）。
  - **缺失/降级诊断子系统的表现（fail-open 规则）**：按[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.10/§8.1（`CON-OBS-002`/`INV-6`，`DiagnosticsService` 初始化失败时降级运行），实现以 `_UnavailableDiagnostics` 兜底，其 `switches()` 恒返回 `{"snapshots_enabled": false, "stats_enabled": false}`（[`src/http_api/app.py`](../../../../src/http_api/app.py)）。因此**缺失/降级**表现为 `HTTP 200 + {false,false}`——因 Oracle 只约束字段集/类型、观测故障不得制造新的失败面，这**仍是本 case 的 PASS**。反之，若健康实例返回非 200、或返回体不是合法 `SwitchState`（键集不符/类型非 bool/以错误信封冒充），即 **FAIL**。唯一例外是存储层读取异常由 handler 的 `_store_read` 转为 `503 usage_store_unavailable`（`ERR-STORE`）——这是机制 §4.8.1 明示的存储不可达语义，属环境问题按[测试设计 §9](../llmtier-api-test-specification.md) 判 BLOCKED/SKIP，不作为契约 FAIL。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 `{snapshots_enabled, stats_enabled}` 且两值均为 JSON 布尔（含降级实例返回默认 `{false,false}` 的 fail-open 形态）。
  - **FAIL**：`status!=200` 且存储健康；或 body 键集不等/缺失/多键；或值非 JSON 布尔；或以错误信封冒充 `SwitchState`。
  - **BLOCKED**：测试代码/契约本身问题（如 fixture 写不出、断言逻辑错、`openapi` 语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或未命中真实诊断服务却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令（`curl`/httpx）、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）。每 Case `manifest.json` 含被测版本锁定 `target_artifact`（`git_commit`/`db_schema_version`/`openapi_version`）与 `redactions`（`Authorization` 脱敏）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/`，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为纯读，不写 `diagnostic_settings`、不改开关、不创建/修改 provider/deployment/service-level、不写注入项、不新增 trace。退出前确认无未清空的注入项（本 case 不注入）、`/readyz` 仍显示 7 tier；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、双 OMLX、`provider_omlx_m5mac` secret）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；M007 `diagnostic_settings` 单行（`002_observability.sql`）；`SwitchState` 机器契约（`interfaces/openapi/llmtier.openapi.json`）。自动化入口 `at_obs_diag_01.py`（**当前 `MISSING`，尚未实现**，落位按 §4.9/§8.5）。**不依赖**其它 Case；与 OBS-ALIAS-01（别名 `/tier/admin/v1/diagnostics` 逐字节等价）、OBS-DIAG-02（PATCH 更新开关 + 审计）、OBS-DIAG-03（PATCH 非法值 400）语义相邻但各自独立执行；角色负向参照 OBS-REQTRACE-03 风格（data token → 403）与 AUTH-08。
