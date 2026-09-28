# AUTH-02 — 错误 bearer

- **Case ID**：`AUTH-02`（与 §3.2 权威清单一致；本文件名 `auth-02.md`，唯一对应）。
- **标题**：`GET /v1/models` 在**携带 Authorization 头但 bearer 值错误**时被拒，返回 403 + `permission_denied`（凭据不匹配 ≠ 缺凭据）。
- **目的（被测契约）**：验证 access-trust 机制的 **bearer 不匹配判定路径**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，securityScheme `BearerAuth`）；入口 [`_auth()`](../../../../src/http_api/app.py)（默认 role=`data`）先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py) 判空，因 `Authorization` 头存在而返回 `None`，再落入 [`authenticate()`](../../../../src/http_api/auth.py)，以 `hmac.compare_digest(supplied, configured)` 比较（`auth.py:56-57`），不匹配则抛 `ApiError(403, "permission_denied")`。**角色澄清**：§3.2 把本 Case 角色记为 `data`（`/v1/models` 的默认 role），实际观测点是"错误 bearer 被拒"，与是否具备 data 权限无关。设计验证项 `VRC-API-002`；机制 `T-TRUST-BEARER`（机制需求 `R-TRUST-01`：错误凭据→403，见 [access-trust 机制 §5.1/§8 INV-2](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`（[errors.py](../../../../src/http_api/errors.py)）。**不证明什么**：不证明 **空 bearer** 被拒（AUTH-06）、**无 Authorization 头**的 LAN trust 免登录（AUTH-01）、**data token 访问 admin 面**被拒（AUTH-03）、**管理面未授权优先于资源存在性**（AUTH-09）、**未配置鉴权→503**（AUTH-07）、**缺/非法凭据→401**（AUTH-10）；也不证明 `hmac.compare_digest` 的恒定时间性（INV-2 需专门时序测量，不属本 case）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，已配置 `LLMTIER_ADMIN_TOKEN=dev-admin`/`LLMTIER_DATA_TOKEN=dev-data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX、m5mac OMLX、`provider_omlx_m5mac.secret_ref` 为 `file:`、必需 provider/deployment 已注册），由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。本 case **不复用** `api_client`（其已注入 `Authorization: Bearer dev-data`，会走**正确凭据**路径而得到 200），使用独立 `httpx.Client`（无默认头）并显式设置错误 bearer。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer bogus-token-xxx
  Accept: application/json
  ```
  构造点：`Authorization` 头**必须存在且以 `Bearer ` 开头**（进入 `authenticate()` 的 Bearer 分支），token 值故意不匹配任何已配置凭据（`bogus-token-xxx`）。错误 bearer 的取值不要求特定字面量，只要不等于 `dev-data`/`dev-admin`；不得使用空串（属 AUTH-06）、不得缺省（属 AUTH-01）。源地址为执行机（`192.168.x.x`）到 m5air 可达的 LAN IP。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设默认 `Authorization`**。
  3. `resp = client.get("/v1/models", headers={"Authorization": "Bearer bogus-token-xxx"})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 403`（凭据不匹配 ⇒ 403；**不是** 401，401 仅用于缺 Bearer 前缀/未命中免登录，属 AUTH-10）。
  5. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键（`message/type/code/param/retryable`）。
  6. 断言 body **不含** `object=="list"`/`data` 等 `ModelList` 字段（错误路径不得泄露模型清单）。
- **重点关注步骤**：① **错误 bearer ≠ 缺凭据**——403 `permission_denied` 与 401 `authentication_required` 是两条分支，断言错把 401 当成功即 FAIL；② **误用带凭据 fixture**——`api_client` 发送 `dev-data` 会得到 200，令本 case 失去意义，必须用独立无默认头客户端；③ **空 bearer 与错误 bearer 的区分**——`Bearer `（空串）走 `compare_digest("", …)` 属 AUTH-06，本 case 的 token 非空；④ **信封恰 5 键**——不得把 `category` 当键（本实现无该键，`type` 即类别）；⑤ **403 在 dispatch 之前**——认证失败不得触达 `app.models.list()`、不产生任何账本义务（[测试设计 §4.6](../llmtier-api-test-specification.md)）；⑥ 不在此 case 断言 401/404 或角色隔离。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的凭据判定规则本身——"`Authorization: Bearer <非配置值>` ⇒ 凭据不匹配 ⇒ 403 `permission_denied`"，与 m5air 具体数据无关。
  - HTTP：`403`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无 `ModelList`/业务载荷：本 case 不应出现 `object=="list"` 或 `data`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200/401/其它 status，或 `error.code` 不符（如落为 `authentication_required`），或信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如客户端把错误 bearer 换成 dev-data、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以**空/缺** Authorization 冒充本 case——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。
- **证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明 bearer 存在且错误）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/A-api/<case-id>/`，`manifest.json` 必含 `{git_commit, db_schema_version, openapi_version}` 与 `redactions`（`Bearer bogus-token-xxx` 为测试凭据可保留）。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改 provider/deployment/service-level，不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；独立 `httpx` 无默认头客户端（不复用 `api_client`）；m5air 已配置 dev-data/dev-admin 凭据；自动化入口 [`at_auth_02.py`](../../../../tests/system/api_test_v03/at_auth_02.py)。**不依赖**其它 Case；与 AUTH-01/AUTH-03/AUTH-06/AUTH-10 共享同一鉴权机制但各自独立执行、互不关闭。
