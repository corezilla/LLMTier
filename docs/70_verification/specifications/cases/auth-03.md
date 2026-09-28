# AUTH-03 — Data token 访问 admin 面

- **Case ID**：`AUTH-03`（与 §3.2 权威清单一致；本文件名 `auth-03.md`，唯一对应）。
- **标题**：`GET /v1/providers` 在**携带有效 data token**时被拒，返回 403 + `permission_denied`（data 角色不授权 admin 面）。
- **目的（被测契约）**：验证 access-trust 机制的 **per-endpoint 角色选择与角色隔离**。被测端点/规则：`GET /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviders`，securityScheme `AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 在路由分派前先执行 `principal = self._auth("admin")`（`app.py:239`），即 [`authenticate()`](../../../../src/http_api/auth.py) 以 role=`admin` 取 `_configured_token("admin")`（= `dev-admin`），而请求携带的是 data token（`dev-data`），`hmac.compare_digest` 不匹配 ⇒ 403 `permission_denied`（`auth.py:56-57`）。设计验证项 `VRC-API-002`；机制 `T-TRUST-SHARED`、`T-TRUST-ENDPOINTS`（机制需求 `R-TRUST-02`：按端点选 role、分发；见 [access-trust 机制 §5.1/§8 INV-4](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`。**不证明什么**：不证明 **无 token 的 LAN trust** 是否受理 admin 面（AUTH-04）、**管理面未授权优先于资源存在性**（AUTH-09）、**别名命名空间**需 admin（AUTH-08）、**错误 bearer** 被拒（AUTH-02）、**缺/非法凭据→401**（AUTH-10）、**未配置鉴权→503**（AUTH-07）；也不证明 `permission_denied` 的具体比较是否恒定时间（INV-2）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，已配置 `LLMTIER_ADMIN_TOKEN=dev-admin`/`LLMTIER_DATA_TOKEN=dev-data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。本 case **使用** `api_client` fixture（[§4.4](../llmtier-api-test-specification.md)），其 `Authorization: Bearer dev-data` 正是被测输入；**不得**改用 `admin_client`（会以 `dev-admin` 通过，令本 case 失去意义）。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```
  构造点：使用 m5air 已配置的 **data 凭据** `dev-data`（`api_client` 默认头），访问 **admin 端点** `/v1/providers`。`dev-data` 是合法凭据，但角色为 `data`，与端点要求的 `admin` 不匹配。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/providers")`（fixture 已带 `Authorization: Bearer dev-data`）；记录 status、headers、body。
  3. 断言 `resp.status_code == 403`（data token 不满足 admin 角色 ⇒ 403；不是 200、不是 401）。
  4. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  5. 断言 body **不含** `data`/`has_more` 等 `ProviderPage` 字段（拒绝路径不得泄露 provider 列表）。
  6. （可选交叉核对）用 `admin_client.get("/v1/providers")` 发一次并记录 200，佐证"同一端点、凭据角色不同结果不同"——该次通过不由本 case 断言（属 AUTH-04/ADM-PROV-01 语义）。
- **重点关注步骤**：① **合法凭据 + 错误角色 ≠ 无权限**——`dev-data` 能过 data 面（AUTH-01/DP-MODELS），但在 admin 面必须 403；② **不能误用 `admin_client`**——那会发送 `dev-admin` 而 200，本 case 的输入必须是 data token；③ **`_auth("admin")` 在路由分发前**（`app.py:239`）——403 先于 `list_providers()`，无上游调用、无账本义务；④ **不得把 401 当成功**——凭据形态合法但无权是 403，401 属 AUTH-10；⑤ **信封恰 5 键**（无 `category` 键，`type` 即类别）；⑥ 不在此 case 断言资源存在性优先级（AUTH-09）。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的角色矩阵本身——"data 角色凭据访问 admin 端点 ⇒ 403 `permission_denied`"，与 m5air 具体 provider 数据无关。
  - HTTP：`403`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无业务载荷：本 case 不应出现 `ProviderPage` 的 `data`/`has_more`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200（角色隔离失效）/401/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（如 m5air 未配置 dev-data）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充本 case——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。
- **证据与 Run**：保存原始命令、发送 headers 快照（证明为 `Bearer dev-data`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，`manifest.json` 必含 `{git_commit, db_schema_version, openapi_version}` 与 `redactions`（`Bearer dev-data` 为测试凭据可保留）。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改 provider/deployment/service-level，不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（带 `dev-data`，[§4.4](../llmtier-api-test-specification.md)）；m5air admin 端点 `/v1/providers` 可用；自动化入口 [`at_auth_03.py`](../../../../tests/system/api_test_v03/at_auth_03.py)。**不依赖**其它 Case；与 AUTH-04/AUTH-08/AUTH-09 共享 admin 面鉴权但各自独立执行、互不关闭。
