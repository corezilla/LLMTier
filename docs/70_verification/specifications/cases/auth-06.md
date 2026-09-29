# AUTH-06 — 空 bearer

- **Case ID**：`AUTH-06`（与 §3.2 权威清单一致；本文件名 `auth-06.md`，唯一对应）。
- **标题**：`GET /v1/models` 在**携带 `Authorization: Bearer `（Bearer 前缀 + 空 token）**时被拒，返回 403 + `permission_denied`（头存在但 token 为空 ≠ 头缺省的 LAN trust）。
- **目的（被测契约）**：验证 access-trust 机制的 **空 token 判定路径**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，securityScheme `BearerAuth`）；入口 [`_auth()`](../../../../src/http_api/app.py)（默认 role=`data`）先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py) 判空——因 `Authorization` 头存在（`"Bearer "` 为真值）而返回 `None`（`auth.py:25`），再落入 [`authenticate()`](../../../../src/http_api/auth.py)：`raw.startswith("Bearer ")` 为真，`supplied = ""`，`hmac.compare_digest("", configured)` 为假 ⇒ `ApiError(403, "permission_denied")`（`auth.py:53-57`）。**角色澄清**：§3.2 角色 `data`（`/v1/models` 默认 role）；核心区分点是"头存在但 token 空"，与 AUTH-01 的"头完全缺省"形成对照。设计验证项 `VRC-API-002`；机制 `T-TRUST-BEARER`（机制需求 `R-TRUST-01`：凭据形态合法但值不匹配→403；见 [access-trust 机制 §5.1/§8 INV-2/INV-5](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`。

  > **契约一致性登记（openapi gap）**：openapi `listModels` 的 responses **仅有 `200` 与 `401`**，**未声明 `403`**；本 case 依赖的 403 `permission_denied`（头存在但空 token）由机制 `T-TRUST-BEARER`（`R-TRUST-01`/`INV-2`/`INV-5`）与实现 [`auth.py`](../../../../src/http_api/auth.py) 保障，属机器契约未表达的路径。本 case 的 Oracle 仍为 403，并把该 openapi 缺口**登记**为已知差异；`X-Request-ID` 亦仅在 openapi 声明的 200 响应头中出现、**非契约**。
**不证明什么**：不证明 **无 `Authorization` 头**的 LAN trust 免登录（AUTH-01）、**非空错误 bearer** 被拒（AUTH-02）、**非法方案（如 `Basic`）→401**（AUTH-10）、**未配置鉴权→503**（AUTH-07）、**未命中免登录的缺 Bearer→401**（AUTH-10）；也不证明恒定时间比较（INV-2）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；**工具约束**：`httpx` 会对 `Authorization: Bearer `（空 token）做规范化/裁剪，可能发送不出字面空 token；须使用 [`urllib.request`](../../../../tests/system/api_test_v03/at_auth_06.py)（或原始 socket）直连以保留 `Bearer ` 尾随空格，**不得**因此改用 `api_client` 或给空串加引号；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer␠
  Accept: application/json
  ```
  构造点：`Authorization` 头**存在**，值为精确的 `Bearer `（`B-e-a-r-e-r` + 一个尾随空格 + 空 token），即头非空所以不进 LAN trust，但 token 为空所以不匹配任何配置凭据。`␠` 表示一个尾随空格字面量；不得写成 `Bearer`（无空格，属非法方案→401）或 `Bearer null`（非空错误 token→AUTH-02）。源地址为执行机到 m5air 可达的 LAN IP。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 用 `urllib.request.Request("http://192.168.1.9:8181/v1/models", headers={"Authorization": "Bearer "})` 发送（保留尾随空格）；捕获 `HTTPError`/响应本体，读取 status 与 body。
  3. 断言 `status == 403`（头存在 + 空 token ⇒ 403；**不是** 401（那是非法方案/缺前缀），**也不是** 200（那是头缺省的 LAN trust））。
  4. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  5. 断言 body **不含** `object=="list"`/`data` 等 `ModelList` 字段（错误路径不得泄露模型清单）。
- **重点关注步骤**：① **头存在与否是分界的核心**——`"Bearer "` 使 `unauthenticated_principal()` 返回 `None`，因此不命中 LAN trust；若执行环境把该头裁剪成"无头"，请求会 200（AUTH-01 行为）从而误判，必须验证实际发出的字节；② **空 token 仍是"形态合法"**——`startswith("Bearer ")` 为真 ⇒ 403 而非 401；③ **工具规范化陷阱**——`httpx` 不可靠，须用 `urllib`/原始 socket；④ **信封恰 5 键**（无 `category`）；⑤ **403 在 dispatch 之前**，无上游调用、无账本义务（[测试设计 §4.6](../llmtier-api-test-specification.md)）；⑥ 不在此 case 断言 401/404 或角色隔离。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 规则本身——"`Authorization: Bearer `（存在但空）⇒ 凭据不匹配 ⇒ 403 `permission_denied`"，与 m5air 具体数据无关。
  - HTTP：`403`；响应头 `X-Request-ID` **非契约**（openapi `listModels` 仅声明 `200` 的响应头，且 `403` 未在 responses 中列出——见"契约一致性登记"，`X-Request-ID` 为运行时注入、不列入 Oracle）。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无 `ModelList`/业务载荷：本 case 不应出现 `object=="list"` 或 `data`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200（空 bearer 被当作免登录）/401/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如客户端无法保留空 token、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以**头缺省**（LAN trust，属 AUTH-01）冒充空 bearer——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。
- **证据与 Run**：保存发出请求的原始字节/命令（证明头为 `Bearer ` 且保留尾随空格）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改/删除资源、不写 usage/账本。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`urllib`/原始 socket 直连能力（保留空 token）；m5air 已配置 dev-data；自动化入口 [`at_auth_06.py`](../../../../tests/system/api_test_v03/at_auth_06.py)。**不依赖**其它 Case；与 AUTH-01/AUTH-02/AUTH-10 共享同一鉴权机制但各自独立执行、互不关闭。
