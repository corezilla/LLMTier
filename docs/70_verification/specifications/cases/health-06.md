# HEALTH-06 — 健康端点无需鉴权

- **Case ID**：`HEALTH-06`（与 §3.2 权威清单一致；本文件名 `health-06.md`，唯一对应）。
- **标题**：在**未配置任何鉴权凭据**的临时实例上，`GET /healthz` 与 `GET /readyz` 在不带 `Authorization` 头时仍返回各自视图（200/503），不返回 401/403/`auth_not_configured`。
- **目的（被测契约）**：验证 IF-HEALTH 的**免鉴权**契约。端点 `GET /healthz`、`GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) 均为 `security:[]`）。实现 [`app.py`](../../../../src/http_api/app.py) 在 `_dispatch()` 中于任何 `_auth()` 调用（[`app.py:193`](../../../../src/http_api/app.py) 起）**之前**处理两个端点（[`app.py:187-190`](../../../../src/http_api/app.py)），故健康路径完全不查询凭据配置。设计验证项 `VRC-API-002`/`VRC-MGMT-003`；机制 `T-TRUST-NOCFG`（未配置凭据时受保护端点的 503 语义）与 `T-TRUST-SHARED`（需求 `R-TRUST-04`；见 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明受保护端点在未配置鉴权时的 503 `auth_not_configured`（AUTH-07）；不证明 A 类公共端点无 token 200（AUTH-05）；不证明 LAN trust 免登录路径（AUTH-01/04）；不证明 `readyz` 的 ready/degraded（HEALTH-02/03）；不触发 provider 计费调用（`LT-OPS-001`）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。执行前必须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动且 `GET /healthz` 200。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b_no_auth`（[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `LLMTierInstance(_NO_AUTH_SETTINGS, dev_mode=False)`）——`dev_mode=False` 时**不设** `LLMTIER_DEV_MODE`/`LLMTIER_ADMIN_TOKEN`/`LLMTIER_DATA_TOKEN`，`_NO_AUTH_SETTINGS` 为三个空 section。**关键客户端约束**：必须使用**不携带 `Authorization` 的裸 `httpx.Client`**（如 `httpx.Client(base_url=llmtier_b_no_auth.base_url, timeout=...)`）；**不得复用 `admin_client_b_no_auth`**——该 fixture 由 `_make_client` 注入 `Authorization: Bearer dev-admin`（[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `_make_client`），在未配置 token 的实例上会走 [`authenticate`](../../../../src/http_api/auth.py) → 503 `auth_not_configured`，与本 case 契约无关。初始状态 = 无 provider/deployment（`_NO_AUTH_SETTINGS` 合法 bootstrap）+ 7 个空 fixed tier；故 `not_ready`。
- **输入与构造**：固定请求（均无 body、无查询参数、**无 `Authorization`**）：

  ```http
  GET /healthz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  边界/构造点：**完全缺省 `Authorization` 头**（不是空串、不是 `Bearer `）；实例**未配置任何 token**（`dev_mode=False` 且无 `LLMTIER_*_TOKEN`）；不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b_no_auth` 启动并轮询 `/healthz` 200。
  2. 建立**无凭据**客户端：`client = httpx.Client(base_url=llmtier_b_no_auth.base_url, timeout=...)`，不设 `Authorization`。
  3. `r1 = client.get("/healthz")`：断言 `r1.status_code == 200`，body 键集 `{status, version}` 且 `status=="ok"`、`version` 非空字符串。
  4. `r2 = client.get("/readyz")`：断言 `r2.status_code in (200, 503)`（本实例为 503），body 键集 `{status, models}`，`status ∈ {ready,degraded,not_ready}`。
  5. 断言两个响应**均不是鉴权错误**：`status` 不为 401、不为 403；若为 503，其 body 不得是 `{"error":{"code":"auth_not_configured",...}}`——必须是 `HealthView`/`ReadinessView` 视图。
  6. （可选交叉核对，不改变本 case 判定）同一无凭据客户端请求一个**受保护**端点（如 `GET /v1/models`）以揭示本实例的鉴权配置状态；该行为归 AUTH-07/AUTH-*，本 case 不据其判定。
  7. （清理）整班结束时由 fixture `stop()` 销毁实例。
- **重点关注步骤**：① **裸客户端而非带 token 的 fixture**——`admin_client_b_no_auth` 带 `Bearer dev-admin` 会得到 503 `auth_not_configured`；用它会把"未配置鉴权"误判成"健康端点需鉴权"，必须用无头客户端。② **不把 503 当失败**——`/readyz` 在无 deployment 的实例上是**合法 503**（`not_ready`）；契约是"免鉴权"，不是"必 200"。③ **区分鉴权错误与就绪错误**——503 时必须检查 body 形态：`ReadinessView`（本 case PASS）vs `{"error":{"code":"auth_not_configured"}}`（AUTH-07 语义，本 case FAIL/构造错误）。④ **`/healthz` 始终 200**——它位于 bootstrap 检查与鉴权之前，是免鉴权的最强证据。⑤ **实现事实**——`unauthenticated_principal` 对 loopback/RFC1918 无头请求会无条件授予共享角色（[`auth.py`](../../../../src/http_api/auth.py)），但健康端点根本不调用它；本 case 的契约点在于**端点本身 `security:[]`、handler 不查凭据**，而非"共享角色恰好生效"。⑥ **不得声称 env 门控**——`LLMTIER_TRUSTED_LAN_MODE` 不被源码读取（[测试设计 §4.2](../llmtier-api-test-specification.md)）。
- **期望结果与独立 Oracle**：独立 Oracle = `security:[]` 的公开端点语义 + 实现 [`app.py:187-190`](../../../../src/http_api/app.py)（健康路径先于 `_auth()`）+ [`src/http_api/health.py`](../../../../src/http_api/health.py) 的 `HealthView`/`ReadinessView` + 系统设计 §8.1 `/healthz` 与 `/readyz` 契约（`/readyz` 503 = `ReadinessView`，**不是** `ErrorEnvelope`）（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；`openapi` 的 `/readyz` 503 schema 已修正为 `ReadinessView`（`NotReady`），与代码/§8.1 一致（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）；端点公开语义见[测试设计 §4.6](../llmtier-api-test-specification.md)，不依赖实现内部状态。
  - `GET /healthz`（无凭据）：`200`；body `{status:"ok", version:<非空字符串>}`。
  - `GET /readyz`（无凭据）：`200` 或 `503`；body 为合法 `ReadinessView`（键集恰为 `{status, models}`），`status ∈ {ready,degraded,not_ready}`；本实例为 `503 + {status:"not_ready", models:[7×unavailable]}`。
  - 两者均**不得**为 401 `authentication_required`、403 `permission_denied`，也不得为带 `code=auth_not_configured` 的错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：无凭据下 `/healthz` 200 + 合法 `HealthView`，且 `/readyz` 返回合法 `ReadinessView`（本实例 503 `not_ready`），两者均非鉴权错误信封。
  - **FAIL**：任一健康端点返回 401/403，或返回带 `auth_not_configured` 的错误信封，或返回体不是合法视图；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：**无法构造未配置鉴权的实例**——例如 `llmtier_b_no_auth` fixture 缺失/无法启动、无法在无 token 条件下保持健康端点可达；或测试代码/断言不可实现（见[测试设计 §9](../llmtier-api-test-specification.md)）。本 case 当前 `自动化入口 = MISSING`（§3.2），无脚本时应按 §9 记为缺口而非 PASS。
  - **SKIP**：B 类临时实例不可用等 §2 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用带 token 的请求冒充"无凭据"判定，或以 mock/替代路径冒充真实实例——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case `自动化入口 = MISSING`（§3.2），本轮未执行；缺口引用见[测试设计 §9/§8.5](../llmtier-api-test-specification.md)（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
- **证据与 Run**：保存裸客户端的发送 headers 快照（证明**无** `Authorization`）、两请求的原始 HTTP status/headers/body、实例环境证据（确认未设 token / `dev_mode=False`）、`elapsed`。`manifest.json` 含 `target_artifact{git_commit,db_schema_version,openapi_version}`、`environment:"b"` 与 `redactions`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，失败现场不截断。契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：B 类实例由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `shutil.rmtree` 临时目录销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）；本 case 只读健康端点，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。
- **依赖**：`llmtier_b_no_auth` fixture 与 `_NO_AUTH_SETTINGS`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；独立无头 `httpx.Client`（不复用 `admin_client_b_no_auth`）；`HealthView`/`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`app.py:187-190`](../../../../src/http_api/app.py) 与 [`auth.py`](../../../../src/http_api/auth.py)；自动化入口 **`MISSING`**（§3.2，尚无脚本；落位按[测试设计 §4.9/§8.5](../llmtier-api-test-specification.md)）。**不依赖**其它 Case；与 AUTH-05（A 类公共端点无 token 200）、AUTH-07（未配置鉴权下受保护端点 503）语义相邻但各自独立执行、互不关闭。
