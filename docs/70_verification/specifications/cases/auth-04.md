# AUTH-04 — Admin 端点 LAN trust 无 token

- **Case ID**：`AUTH-04`（与 §3.2 权威清单一致；本文件名 `auth-04.md`，唯一对应）。
- **标题**：`GET /v1/providers` 在受信 LAN 来源且**不带** `Authorization` 头时被无条件受理，返回 200 + 合法 provider 清单（LAN trust 对 admin 面同样生效）。
- **目的（被测契约）**：验证 access-trust 机制的 **LAN trust 免登录路径同样覆盖 admin 端点**。被测端点/规则：`GET /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviders`，securityScheme `AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 在 `principal = self._auth("admin")`（`app.py:239`）内先调 [`unauthenticated_principal()`](../../../../src/http_api/auth.py)：请求**无 `Authorization` 头**且 `client_address` 属 loopback 或 RFC1918（`10/8`、`172.16/12`、`192.168/16`、`fc00::/7`）时返回 `Principal("trusted-lan-operator","admin")`，端点因而在**零凭据**下返回 200。**角色澄清**：§3.2 把本 Case 角色记为 `none`（LAN-trust 免 token）；wire 契约是"无 token + 受信 LAN → 200"，不据此断言任何凭据路径。设计验证项 `VRC-API-002`；机制 `T-TRUST-LAN`（机制需求 `R-TRUST-01`/`R-TRUST-02`；见 [access-trust 机制 §5.1/§8 INV-5](../../../20_system_design/mechanisms/access-trust.md)）。**不证明什么**：不证明任何 **凭据** 路径——不证明 data token 在 admin 面被拒（AUTH-03）、错误 bearer 被拒（AUTH-02）、空 bearer 被拒（AUTH-06）、管理面未授权优先于资源存在性（AUTH-09）、别名命名空间需 admin（AUTH-08）、公共端点无需 token（AUTH-05）、未配置鉴权→503（AUTH-07）、缺/非法凭据→401（AUTH-10）。特别地，本 case **不**证明存在 `LLMTIER_TRUSTED_LAN_MODE` 环境门控：源码 [auth.py](../../../../src/http_api/auth.py) **不读取**该变量，LAN 免登录在 `auth.py:33-34` 是**无条件**的（测试设计 §4.2）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `none`（§3.2）；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。**关键环境约束（TS-003）**：测试执行机必须位于 `192.168.x.x` RFC1918 LAN（如 m5mac `192.168.1.8`），其到 m5air 的源地址必须命中 `192.168.0.0/16`；若执行机处于非受信网段，本 case 会得到 401，**不可判 PASS**，须先修复网络前置。本 case **不复用** `admin_client`（其已注入 `dev-admin`，会走凭据路径），使用独立 `httpx.Client`（无默认头）。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```
  构造点：**`Authorization` 头完全缺省**——既不是空串也不是 `Bearer `；任何存在值都会使 `unauthenticated_principal()` 立即返回 `None`（`auth.py:25` `if headers.get("Authorization"): return None`）并转入 `authenticate()` 凭据路径。源地址固定为执行机到 m5air 可达的 LAN IP（`192.168.x.x`）。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设 `Authorization`**。
  3. `resp = client.get("/v1/providers")`；记录 status、headers、body。
  4. 断言 `resp.status_code == 200`（LAN trust 命中 ⇒ 未被 401/403）。
  5. 解析 body：断言为 `ProviderPage`，即含 `data` 数组（可能为空数组，但 m5air 基线非空），抽查元素关键字段（`id:str`、`name`、`kind`、`enabled`、`has_secret`、`secret_ref`）；若响应含 `has_more`，断言为布尔。
  6. （可选交叉核对）对同一 `GET /v1/providers` 注入 `Authorization: Bearer dev-admin` 再发一次，确认除请求头外 body 语义一致——佐证 LAN trust 与 admin token 落到同一 handler（该次请求的通过不由本 case 断言）。
- **重点关注步骤**：① **头缺省而非空值**——必须完全不发送 `Authorization`；`Bearer `（空 bearer）会因 `compare_digest` 失败而 403（AUTH-06），从而把本 case 误判 FAIL；② **来源受信**——200 成立的前提是 `client_address` 命中 loopback/RFC1918；断言前应确认执行机 LAN IP，非受信来源的 401 属环境前置不满足（SKIP），不是 AUTH-04 的行为错误；③ **Oracle 是"trusted-LAN 规则"而非"admin 凭据可用"**——只断言 200 不够，必须同时验证合法 `ProviderPage` body，排除把其它 200 当成功；④ **不得用带 token 的 fixture**——`admin_client` 已带 header，误用会把"admin token 生效"当成"LAN trust 生效"；⑤ **不要声称 env 门控**——`LLMTIER_TRUSTED_LAN_MODE` 不被源码读取，本 case 不得断言"门控开启才 200"（现有 [`at_auth_04.py`](../../../../tests/system/api_test_v03/at_auth_04.py) 文件头注释称该 env "默认开启"属不准确表述，设计以源码行为为准）；⑥ 不在此 case 断言 401/403 负向（属 AUTH-02/03/06/09/10）。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 规则本身——"无 `Authorization` + 来源 ∈ 受信私网 ⇒ 共享 `operator`/admin 主体 ⇒ `GET /v1/providers` 受理"，与 m5air 具体数据无关。
  - HTTP：`200`；响应头含 `X-Request-ID`。
  - body：`ProviderPage`（含 `data` 数组；m5air 基线 3 个 provider：`provider_local`/`provider_minimax`/`provider_omlx_m5mac`）。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 为合法 `ProviderPage`（`data` 数组 + 元素关键字段）且覆盖 m5air 基线 provider。
  - **FAIL**：返回 401/403/其它 status，或 body 非合法 `ProviderPage`（LAN trust 规则或 provider 清单契约不成立）；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如独立无头客户端构造错、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足，或执行机不在 `192.168.x` LAN 而无法制造受信来源——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以**带 token** 的请求冒充 LAN trust——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。
- **证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明**无** `Authorization`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider 列表）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，`manifest.json` 必含 `{git_commit, db_schema_version, openapi_version}` 与 `redactions`（本 case 主请求无凭据；若执行可选交叉核对，`Bearer dev-admin` 属测试凭据可保留）。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改 provider/deployment/service-level，不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；执行机位于 `192.168.x` LAN（TS-003）；独立 `httpx` 无头客户端（不复用 `admin_client`）；m5air `GET /v1/providers` 可用；自动化入口 [`at_auth_04.py`](../../../../tests/system/api_test_v03/at_auth_04.py)。**不依赖**其它 Case；与 AUTH-01/AUTH-03/AUTH-08/AUTH-09 共享 admin/data 面鉴权但各自独立执行、互不关闭。
