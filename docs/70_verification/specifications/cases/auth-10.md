# AUTH-10 — 缺/非法凭据 401

- **Case ID**：`AUTH-10`（与 §3.2 权威清单一致；本文件名 `auth-10.md`，唯一对应）。
- **标题**：受保护端点 `GET /v1/models` 在**携带非法授权方案（`Authorization: Basic …`）**时返回 401 + `authentication_required`（非法凭据形态 ≠ 凭据不匹配 403）。
- **目的（被测契约）**：验证 access-trust 机制的 **缺凭据/非法方案判定路径**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`）；入口 [`_auth()`](../../../../src/http_api/app.py) 先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py)（因 `Authorization` 头存在而返回 `None`），再落入 [`authenticate()`](../../../../src/http_api/auth.py)：`raw.startswith("Bearer ")` 为假 ⇒ 抛 `ApiError(401, "authentication_required")`（`auth.py:53-54`）。**角色澄清**：§3.2 角色 `none`（该 case 关注"无效/缺失授权"而非 data 权限）；wire 契约是"非法授权方案 ⇒ 401 `authentication_required`"。设计验证项 `VRC-API-002`；机制 `T-TRUST-BEARER`（机制需求 `R-TRUST-01`：单点判定、错误映射；见 [access-trust 机制 §5.1/§7/§8 INV-1](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`，`type` 由状态导出（401 < 500 ⇒ `request_error`）。**不证明什么**：不证明 **错误 bearer（形态合法）→403**（AUTH-02）、**空 bearer→403**（AUTH-06）、**data token 访问 admin 面→403**（AUTH-03/08/09）、**未配置鉴权→503**（AUTH-07）、**无 token 的 LAN trust→200**（AUTH-01/04）、**公共端点无需 token**（AUTH-05）。本 case **不**证明非受信来源下"缺 Bearer→401"（见下构造说明）。

  > **构造诚实性（如何触发）**：本 case 的契约有两半——(a)"无 Bearer 且不命中免登录"、(b)"非法授权方案"。在 A/B 两班**均无法构造 (a)**：A 类 m5air 监听 LAN，执行机源地址为 `192.168.1.x`（RFC1918 受信）；B 类临时实例监听 `127.0.0.1`（loopback 受信）；源码 `unauthenticated_principal()`（`auth.py:33-34`）对 loopback/RFC1918 在**无 `Authorization` 头**时**无条件**授予共享角色（不读 `LLMTIER_TRUSTED_LAN_MODE`），因此"完全无头"在 A/B 上恒为 200，非受信来源需公网源地址，A/B 不可得（[测试设计 §4.2/§11.2 第 5 项](../llmtier-api-test-specification.md)）。故本 case 以 **(b) 非法方案**（`Authorization: Basic …`）触发 401——它进入同一 `authenticate()` 的"非法方案"分支，产出契约要求的 401 `authentication_required`；但**不得**据此声称已验证 (a) 的"来源不受信"门。若伪造来源（`X-Forwarded-For`、改 `client_address`、mock）冒充 (a)，判 INVALID。

- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，已配置 `LLMTIER_ADMIN_TOKEN=dev-admin`/`LLMTIER_DATA_TOKEN=dev-data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。本 case **不复用** `api_client`/`admin_client`（它们注入合法 bearer，会 200），使用独立 `httpx.Client`（无默认头）并显式设置 `Basic` 方案。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Basic ZGV2LWRhdGE=
  Accept: application/json
  ```
  构造点：`Authorization` 头**存在且非 `Bearer ` 前缀**（此处为 `Basic <base64>`，`ZGV2LWRhdGE=` 是 `dev-data` 的 base64，仅作形态占位），落入 `authenticate()` 的"非法方案"分支 ⇒ 401。变体（可选）：`Authorization: Token dev-data`、`Authorization: Bearer`（无尾随空格）同样应 401；任一变体均须经 `authenticate()` 且以 401 收场。不得使用 `Bearer <错误值>`（属 AUTH-02）或 `Bearer `（空 token，属 AUTH-06）。源地址为执行机到 m5air 可达的 LAN IP。不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设默认 `Authorization`**。
  3. `resp = client.get("/v1/models", headers={"Authorization": "Basic ZGV2LWRhdGE="})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 401`（非法方案 ⇒ 401 `authentication_required`；**不是** 403，也不是 200）。
  5. 解析 body 的 `error` 信封，断言 `error.code == "authentication_required"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  6. 断言 body **不含** `object=="list"`/`data` 等 `ModelList` 字段（拒绝路径不得返回业务载荷）。
  7. （可选）对变体 `Authorization: Token dev-data` 重复第 3–6 步，确认同样 401（同一分支）。
- **重点关注步骤**：① **401 与 403 的分界**——非法方案/缺 Bearer 前缀 ⇒ 401；形态合法（`Bearer `）但值错 ⇒ 403（AUTH-02/06）。把 403 当 401 或反之即 FAIL；② **不能以"完全无头"构造本 case**——A/B 上无头因 LAN/loopback trust 得 200；若观察到 200，说明构造错误而非行为错误；③ **不得伪造来源**——代码以 socket `client_address[0]` 判定（`app.py:175`），`X-Forwarded-For` 等头不参与；伪造/改地址冒充非受信来源判 INVALID（[测试设计 §9](../llmtier-api-test-specification.md)）；④ **401 的 `type` 是 `request_error`**（401 < 500），信封恰 5 键（无 `category`）；⑤ **拒绝先于 dispatch**——无上游调用、无账本义务（[测试设计 §4.6](../llmtier-api-test-specification.md)）；⑥ 不在此 case 断言 403/404/503 或角色隔离。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的凭据形态规则本身——"受保护端点 + 非 `Bearer` 授权方案 ⇒ 401 `authentication_required`"，与 m5air 具体数据、来源网段无关（来源门未被本构造覆盖，见构造说明）。
  - HTTP：`401`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"authentication_required","param":null,"retryable":false}}`，恰 5 键。
  - 无 `ModelList`/业务载荷：本 case 不应出现 `object=="list"` 或 `data`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==401` 且 `error.code=="authentication_required"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200/403/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如无法构造非法方案、断言不可实现）；**另**：若执行者只尝试"完全无头"路径并因 A/B 恒 200 而无法触达 401，应判 BLOCKED（构造失败）而非 FAIL，并在报告中说明非受信来源不可得（[测试设计 §9](../llmtier-api-test-specification.md)）。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 `X-Forwarded-For`/改 `client_address` 伪造非受信来源冒充 (a)，或以错误/空 bearer 冒充本 case——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（**当前自动化入口 `MISSING`，默认即 NOT_RUN，直至补 `at_auth_10.py`**）。
- **证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明为 `Basic` 方案）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，`manifest.json` 必含 `{git_commit, db_schema_version, openapi_version}` 与 `redactions`（`Basic ZGV2LWRhdGE=` 为形态占位、非有效凭据）。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改 provider/deployment/service-level，不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；独立 `httpx` 无默认头客户端（不复用 `api_client`/`admin_client`）；m5air `GET /v1/models` 可用；**自动化入口 `MISSING`**（需新建 `tests/system/api_test_v03/at_auth_10.py`）。**不依赖**其它 Case；与 AUTH-01/AUTH-02/AUTH-06 构成"凭据形态→状态码"矩阵（200/403/403/401）但各自独立执行、互不关闭。
