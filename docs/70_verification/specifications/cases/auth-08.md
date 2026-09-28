# AUTH-08 — 别名命名空间需 admin

- **Case ID**：`AUTH-08`（与 §3.2 权威清单一致；本文件名 `auth-08.md`，唯一对应）。
- **标题**：别名端点 `GET /tier/admin/v1/diagnostics` 在**携带有效 data token**时被拒，返回 403 + `permission_denied`（别名命名空间与扁平路径同样要求 `admin` 角色）。
- **目的（被测契约）**：验证 `/tier/admin/v1/*` **别名命名空间的鉴权与 `/v1/*` 等价**。被测端点/规则：`GET /tier/admin/v1/diagnostics`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `x-llmtier-contract-aliases` 映射到 `/v1/diagnostics`，securityScheme `AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 的 `principal = self._auth("admin")`（`app.py:239`）位于所有 `/tier/admin/v1/*` 别名分支（`app.py:331-353`）**之前**，因此 [`authenticate()`](../../../../src/http_api/auth.py) 先以 role=`admin` 校验，data token（`dev-data`）与 `dev-admin` 不匹配 ⇒ 403 `permission_denied`，**在到达别名 handler 之前**即被拒。设计验证项 `VRC-API-002`；机制 `T-TRUST-SHARED`、`T-TRUST-ENDPOINTS`（机制需求 `R-TRUST-02`；见 [access-trust 机制 §5.1/§8 INV-4](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`。**不证明什么**：不证明别名与扁平路径的**响应逐字节等价**（OBS-ALIAS-01、`admin` 正向）、不证明 **admin 无 token 的 LAN trust**（AUTH-04，扁平路径）、**错误 bearer** 被拒（AUTH-02）、**缺/非法凭据→401**（AUTH-10）、**未配置鉴权→503**（AUTH-07）、**管理面未授权优先于资源存在性**（AUTH-09）。本 case **只**断言别名命名空间的角色隔离。

  > **实现状态（MISSING）**：§3.2 登记本 Case 的自动化入口为 `MISSING`（尚无 `at_auth_08.py`）。本设计定义 Case；在执行脚本补齐前，Run 应为 `NOT_RUN`，**不得**以 OBS-ALIAS 系列或手工 curl 冒充实现（[测试设计 §4.9/§9](../llmtier-api-test-specification.md)）。

- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，已配置 `LLMTIER_ADMIN_TOKEN=dev-admin`/`LLMTIER_DATA_TOKEN=dev-data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。本 case 使用独立 `httpx.Client`（无默认头）并显式设置 `Authorization: Bearer dev-data`（或复用 `api_client`，其恰好发送 `dev-data`）；**不得**使用 `admin_client`。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /tier/admin/v1/diagnostics HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```
  构造点：使用 **data 凭据** `dev-data` 访问**别名 admin 端点** `/tier/admin/v1/diagnostics`。该路径是 `/v1/diagnostics` 的精确别名（openapi `x-llmtier-contract-aliases`），角色要求同为 `admin`。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，`headers={"Authorization": "Bearer dev-data"}`。
  3. `resp = client.get("/tier/admin/v1/diagnostics")`；记录 status、headers、body。
  4. 断言 `resp.status_code == 403`（别名命名空间同样要求 admin ⇒ data token 被拒；不是 200、不是 401）。
  5. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  6. 断言 body **不含** `snapshots_enabled`/`stats_enabled` 等 `SwitchState` 字段（拒绝路径不得泄露诊断开关）。
  7. （可选交叉核对）用 `admin_client.get("/tier/admin/v1/diagnostics")` 发一次并记录 200，佐证"同一别名、凭据角色不同结果不同"——该次通过不由本 case 断言（属 OBS-ALIAS-01/正向前置）。
- **重点关注步骤**：① **别名与扁平路径鉴权等价**——`/tier/admin/v1/diagnostics` 不是免鉴权旁路，`_auth("admin")` 在其分支之前（`app.py:239`）执行；② **不能误用 `admin_client`**——那会发送 `dev-admin` 而 200，本 case 输入必须是 data token；③ **403 早于别名 handler**——认证失败不得触达 `app.diagnostics.switches()`，无账本义务；④ **不得把 401 当成功**（属 AUTH-10）；⑤ **信封恰 5 键**（无 `category`）；⑥ 不在此 case 断言响应等价性（OBS-ALIAS-01）或其它别名路径（snapshots/stats/traces/deployments/trace）。
- **期望结果与独立 Oracle**：独立 Oracle = 别名命名空间角色矩阵本身——"data 角色凭据访问 `/tier/admin/v1/*` 别名 admin 端点 ⇒ 403 `permission_denied`"，与 m5air 具体诊断数据无关。
  - HTTP：`403`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无业务载荷：本 case 不应出现 `SwitchState` 字段。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200（别名旁路鉴权）/401/404/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充本 case——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（**当前自动化入口 `MISSING`，默认即 NOT_RUN，直至补 `at_auth_08.py`**）。
- **证据与 Run**：保存原始命令、发送 headers 快照（证明 `Bearer dev-data`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，`manifest.json` 必含 `{git_commit, db_schema_version, openapi_version}` 与 `redactions`（`Bearer dev-data` 属测试凭据可保留）。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改 provider/deployment/service-level，不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；m5air 别名 `/tier/admin/v1/diagnostics` 可用；独立 `httpx` 客户端或 `api_client`（带 `dev-data`）；**自动化入口 `MISSING`**（需新建 `tests/system/api_test_v03/at_auth_08.py`）。**不依赖**其它 Case；与 AUTH-03/AUTH-09 共享 admin 面角色隔离但各自独立执行、互不关闭。
