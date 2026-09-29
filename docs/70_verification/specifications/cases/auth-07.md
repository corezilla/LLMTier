# AUTH-07 — 未配置鉴权

- **Case ID**：`AUTH-07`（与 §3.2 权威清单一致；本文件名 `auth-07.md`，唯一对应）。
- **标题**：受保护端点 `GET /v1/models` 在**未配置任何 token**的实例上、携带未配置的 bearer 时返回 503 + `auth_not_configured`（运行期无凭据可用，拒绝而非放行）。
- **目的（被测契约）**：验证 access-trust 机制的 **未配置鉴权运行期语义**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，securityScheme `BearerAuth`）；入口 [`_auth()`](../../../../src/http_api/app.py) 先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py)（因请求带 `Authorization` 头而返回 `None`），再落入 [`authenticate()`](../../../../src/http_api/auth.py)：`_configured_token("data")` 在无 `LLMTIER_DATA_TOKEN` 且 `LLMTIER_DEV_MODE≠1` 时返回 `None`，于是抛 `ApiError(503, "auth_not_configured")`（`auth.py:49-51`）。设计验证项 `VRC-MGMT-003`；机制 `T-TRUST-NOCFG`（机制需求 `R-TRUST-04`：env token 存在性、503 `auth_not_configured` 语义；见 [access-trust 机制 §12.2/§14.4 R-TRUST-04](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`，`type` 由状态导出（503 ≥ 500 ⇒ `server_error`）。**不证明什么**：不证明 **错误 bearer** 在**已配置**实例上被拒（AUTH-02）、**空 bearer** 被拒（AUTH-06）、**data token 访问 admin 面**被拒（AUTH-03）、**缺/非法凭据→401**（AUTH-10）、**无 token 的 LAN trust** 免登录（AUTH-01/04）。特别地，本 case **不**证明"未配置鉴权时公共端点也 503"——`/healthz`/`/readyz` 永不进入鉴权（AUTH-05/HEALTH-06）。

  > **构造诚实性（如何触发）**：B 类临时实例监听 `127.0.0.1`（loopback，`auth.py:33`），若请求**不带** `Authorization` 头，`unauthenticated_principal()` 会授予 loopback 共享主体而返回 200——**无法**用"完全无头"触发 503。因此本 case 通过 `admin_client_b_no_auth` fixture 特意携带一个**未配置**的 `Authorization: Bearer dev-admin`，使 `unauthenticated_principal()` 返回 `None` 从而进入 `authenticate()`，再由"无配置 token"抛 503。该 bearer 字面量为测试占位符，与 503 的成立无关（无任何 token 被配置）。

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；使用 `llmtier_b_no_auth` fixture：`LLMTierInstance(_NO_AUTH_SETTINGS, dev_mode=False)`，启动时清除全部 `LLMTIER_*` 环境变量（`conftest.py`），且 `dev_mode=False` **不**写 token/`LLMTIER_DEV_MODE`，故 `_configured_token()` 必返回 `None`。初始状态=空库（`_NO_AUTH_SETTINGS`：无 provider/deployment/service-level）；本 case 使用 `admin_client_b_no_auth` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 127.0.0.1:<临时端口>
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：实例**未配置任何 token**（`dev_mode=False`：清除 `LLMTIER_*` 后不写 token/DEV_MODE；`LLMTIER_TRUSTED_LAN_MODE=1` 被重设但不参与鉴权）；请求**特意携带一个 bearer**（`dev-admin`）以绕开 loopback LAN trust、强制走 `authenticate()`；bearer 字面量不重要（无 token 可匹配）。不注入故障；不构造非法输入。**不得**把本 case 跑在 A 类 m5air（其已配置 token，会得 403 而非 503）。
- **执行过程（逐步调用）**：
  1. 启动/复用 `llmtier_b_no_auth`（fixture session-scope；`start()` 轮询 `/healthz` 至 200）。记录临时实例端口。
  2. （可选前置确认）断言该实例上 `X` 环境不含 token（fixture 语义保证）；不重复 A 类就绪检查。
  3. `resp = admin_client_b_no_auth.get("/v1/models")`；记录 status、headers、body。
  4. 断言 `resp.status_code == 503`（无可用凭据 ⇒ 503；**不是** 200/401/403）。
  5. 解析 body 的 `error` 信封，断言 `error.code == "auth_not_configured"`、`error.type == "server_error"`（503 ≥ 500）、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  6. 断言 body **不含** `object=="list"`/`data` 等 `ModelList` 字段（拒绝路径不得返回业务载荷）。
- **重点关注步骤**：① **必须携带 bearer**——loopback 无头请求会命中 LAN trust 得 200，只有头存在才能进入 `authenticate()` 观察 503；这是本 case 最易误判处；② **`dev_mode` 必须为 False**——若 `LLMTIER_DEV_MODE=1`，`_configured_token()` 会回退到 `dev-data`/`dev-admin` 而不再 503；fixture 已保证；③ **不得跑于 A 类**——m5air 已配置 token，本 case 的 503 前提是其**未配置**，误跑会得 403（AUTH-02 行为）而误判；④ **503 的 `type` 是 `server_error`**（不是 `request_error`），且信封恰 5 键；⑤ **拒绝先于 dispatch**——503 在路由体之前，无上游调用、无账本义务；⑥ 不在此 case 断言 401/403 或公共端点行为。
- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的未配置语义本身——"受保护端点 + 无配置 token ⇒ 503 `auth_not_configured`（不静默放行、不 401/403）"。
  - HTTP：`503`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"server_error","code":"auth_not_configured","param":null,"retryable":false}}`，恰 5 键。
  - 无业务载荷：本 case 不应出现 `object=="list"` 或 `data`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==503` 且 `error.code=="auth_not_configured"` 且 `error.type=="server_error"` 且信封恰 5 键。
  - **FAIL**：返回 200（未配置却放行）/401/403/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：B 类临时实例无法启动/无法判定（fixture 写不出、断言逻辑错）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类附加前置不满足（临时实例不可用）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 A 类 m5air、`127.0.0.1` mock 或已配置 token 的实例冒充"未配置鉴权"——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 已定义但本轮未执行（含实现缺失）。
- **证据与 Run**：保存启动参数快照（证明 `dev_mode=False` 且无 `LLMTIER_*` token）、原始命令、发送 headers 快照（证明携带 bearer）、HTTP status/headers/body、临时实例端口、exit code、`elapsed`、`/healthz` 快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**由 fixture 负责**——`llmtier_b_no_auth` session-scope，测试结束 `stop()`（`terminate`→等待→必要时 `kill`）并 `shutil.rmtree` 临时目录（[测试设计 §4.7](../llmtier-api-test-specification.md)）。本 case 为只读 `GET`，不创建/修改资源。确认临时端口无遗留监听（`lsof`）。若 B 类进程无法终止，保留证据并判 BLOCKED（[测试设计 §11](../llmtier-api-test-specification.md)）。
- **依赖**：B 类临时实例可启动（[测试设计 §2.1 附加](../llmtier-api-test-specification.md)）；fixture `llmtier_b_no_auth` 与 `admin_client_b_no_auth`（[§4.4](../llmtier-api-test-specification.md)，[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py)）；自动化入口 [`at_auth_07.py`](../../../../tests/system/api_test_v03/at_auth_07.py)。**不依赖**其它 Case；与 AUTH-02/AUTH-03/AUTH-10 构成"凭据状态→状态码"矩阵但各自独立执行、互不关闭。
