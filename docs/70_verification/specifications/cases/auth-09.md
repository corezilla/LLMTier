# AUTH-09 — 管理面未授权优先于资源存在性

- **Case ID**：`AUTH-09`（与 §3.2 权威清单一致；本文件名 `auth-09.md`，唯一对应）。
- **标题**：`GET /v1/providers/{id}` 在**携带有效 data token**时，**无论 `{id}` 是否存在**都先返回 403 + `permission_denied`，不泄露 `not_found`（授权先于资源存在性）。
- **目的（被测契约）**：验证 access-trust 的 **INV-3：401/403 不泄露资源存在性**。被测端点/规则：`GET /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProvider`，securityScheme `AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 在解析 `{id}` 后**先**执行 `principal = self._auth("admin")`（`app.py:239`），**再**进入 provider 详情分支与 `app.registry.get_provider(rid)`（`app.py:283-286`）。data token（`dev-data`）对 `admin` role 不匹配 ⇒ [`authenticate()`](../../../../src/http_api/auth.py) 抛 403 `permission_denied`，**在 `get_provider()` 之前**完成，因此不存在的 `{id}` 也只得到 403、绝不得到 404 `not_found`。设计验证项 `VRC-API-002`；机制 `T-TRUST-LEAK`（机制需求 `R-TRUST-01`/`R-TRUST-02`；见 [access-trust 机制 §4.4/§8 INV-3/§11](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`。**不证明什么**：不证明 **admin 凭据下不存在的 provider→404 `not_found`**（ADM-PROV-04）、**data token 访问 provider 列表**被拒（AUTH-03）、**别名命名空间**需 admin（AUTH-08）、**错误 bearer** 被拒（AUTH-02）、**缺/非法凭据→401**（AUTH-10）、**未配置鉴权→503**（AUTH-07）。本 case **只**断言认证拒绝发生在资源存在性判定之前、且拒绝形态不因存在性而异。

  > **实现状态（MISSING）**：§3.2 登记本 Case 的自动化入口为 `MISSING`（尚无 `at_auth_09.py`）。本设计定义 Case；在执行脚本补齐前，Run 应为 `NOT_RUN`，**不得**以 ADM-PROV-04 或手工 curl 冒充实现（[测试设计 §4.9/§9](../llmtier-api-test-specification.md)）。

- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，已配置 `LLMTIER_ADMIN_TOKEN=dev-admin`/`LLMTIER_DATA_TOKEN=dev-data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查（含 §2.1.6 必需 provider 已注册，供"存在 id"对照），由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier（含 `provider_local`）。本 case 使用独立 `httpx.Client`（无默认头）并显式设置 `Authorization: Bearer dev-data`（或复用 `api_client`）；**不得**使用 `admin_client`。
- **输入与构造**：两组固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers/provider_local HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  ```http
  GET /v1/providers/provider_does_not_exist_auth09 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  构造点：**存在 id** = m5air 基线 `provider_local`（§2.1.6 保证注册）；**不存在 id** = 明确未注册的字面量 `provider_does_not_exist_auth09`（不得使用真实 prefix 冒充，避免歧义）。两者都携带 **data 凭据** `dev-data`。二者响应必须同为 403 `permission_denied`——存在性差异不得体现在 status/code/body。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，`headers={"Authorization": "Bearer dev-data"}`。
  3. `r_exist = client.get("/v1/providers/provider_local")`；`r_missing = client.get("/v1/providers/provider_does_not_exist_auth09")`；分别记录 status、headers、body。
  4. 断言**两者** `status_code == 403`（授权先于存在性；不存在的 id 也**不**得 404）。
  5. 对两个 body 分别解析 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  6. 断言不存在的 id **不返回** `not_found`/404，且两响应在 status 与 `error.code` 上**无法区分**（无存在性泄露）。
  7. 断言两个 body 均**不含** `ProviderView` 字段（`id`/`name`/`kind`/`secret_ref`）——拒绝路径不得泄露资源内容。
- **重点关注步骤**：① **必须用不存在的 id 才能证明"优先"**——若只用存在 id，403 也可以由"handler 内部再次校验"产生，无法排除存在性泄露；本 case 的核心就是 `provider_does_not_exist_auth09` → 403（而非 404）；② **认证在 `get_provider()` 之前**（`app.py:239` 早于 `app.py:283-286`）——断言应确认没有 registry 查询副作用（无账本义务）；③ **两响应不可区分**——status 与 `code` 必须一致，任何差异即 INV-3 违反；④ **不能误用 `admin`**——admin 对不存在 id 会得到 404 `not_found`（ADM-PROV-04），本 case 的输入必须是 data token；⑤ **不得把 401 当成功**（属 AUTH-10）；⑥ **信封恰 5 键**（无 `category`）。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的 INV-3 本身——"未授权（admin 面 + data 角色）⇒ 403 `permission_denied`，与目标资源是否存在无关，且响应不泄露存在性"。
  - HTTP：**两者均** `403`；响应头含 `X-Request-ID`。
  - body（两者）：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无 `not_found`：不存在的 id **不得**返回 404 或 `error.code=="not_found"`。
  - 无业务载荷：不出现 `ProviderView` 字段。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：存在 id 与不存在 id **均** `status==403` 且 `error.code=="permission_denied"`，且两条响应在 status/`code` 上不可区分。
  - **FAIL**：任一返回 200/401/404/其它 status，或不存在 id 落为 `not_found`（存在性泄露），或两条响应可区分、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据、不存在 id 构造错、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（如 m5air 缺少 `provider_local` 基线）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充本 case——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（**当前自动化入口 `MISSING`，默认即 NOT_RUN，直至补 `at_auth_09.py`**）。
- **证据与 Run**：保存两条原始命令、发送 headers 快照（证明 `Bearer dev-data`）、两组 HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider 列表）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，`manifest.json` 必含 `{git_commit, db_schema_version, openapi_version}` 与 `redactions`（`Bearer dev-data` 属测试凭据可保留）。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`（不存在 id 亦不产生副作用），无状态，不创建/修改 provider/deployment/service-level，不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 §2.1.6 `provider_local` 注册）；独立 `httpx` 客户端或 `api_client`（带 `dev-data`）；m5air `GET /v1/providers/{id}` 可用；**自动化入口 `MISSING`**（需新建 `tests/system/api_test_v03/at_auth_09.py`）。**不依赖**其它 Case；与 AUTH-03/AUTH-08 共享 admin 面角色隔离，与 ADM-PROV-04（admin 正向 not_found）互补但独立执行、互不关闭。
