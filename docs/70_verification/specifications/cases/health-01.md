# HEALTH-01 — healthz 始终存活

- **Case ID**：`HEALTH-01`（与 §3.2 权威清单一致；本文件名 `health-01.md`，唯一对应）。
- **标题**：`GET /healthz` 公开存活探针：HTTP 200 + `HealthView{status:"ok", version:<string>}`，无凭据、无副作用；即使 bootstrap/schema 失败也保持 200。
- **目的（被测契约）**：验证 IF-HEALTH 的**进程存活探针**契约。端点 `GET /healthz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getHealth`，`security:[]`），实现 [`src/http_api/app.py:187`](../../../../src/http_api/app.py) 在 `_dispatch()` 最前短路返回 `_json(200, health_view(__version__))`；[`health_view`](../../../../src/http_api/health.py) 返回 `{"status":"ok","version":<__version__>}`（`__version__="0.3.0-dev"`，[`src/http_api/__init__.py`](../../../../src/http_api/__init__.py)）。设计验证项 `VRC-API-002`；机制 `T-TRUST-ENDPOINTS`（需求 `R-TRUST-04`；见 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明就绪（`/readyz` 见 HEALTH-02/03/04/05）；不证明 healthz 也经鉴权（该端点 `security:[]`，鉴权属 AUTH-*）；不证明 `version` 的语义（只断言其为非空字符串）；不触发任何 provider 计费调用（`LT-OPS-001`）。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `none`，见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。**客户端**：本 case 的零凭据契约点必须用裸客户端（**不用** `api_client`，其注入 `Authorization`）；具体 fixture/客户端构造见 §4.4。关键实现约束：[`app.py:187`](../../../../src/http_api/app.py) 的 `/healthz` 分支位于 `if app.bootstrap_error`（[`app.py:192`](../../../../src/http_api/app.py)）之前，故**即使 bootstrap 失败仍返回 200**——它只代表进程存活。
- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /healthz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```

  边界/构造点：**零凭据契约点必须用裸客户端构造**——**带 `Authorization` 头即非零凭据**；本 case 的 `security:[]` 判定必须用不带任何头的裸请求（`httpx.get(base + "/healthz")` 或新建 `httpx.Client(base_url=base)`），并显式断言该请求**未附 `Authorization`**。不构造非法输入（非法 query/body 不在本 case 范围）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = httpx.get(base + "/healthz")` —— **裸客户端、不携带任何头**（**不得**用 `api_client`：它注入 `Authorization`，与零凭据契约点矛盾）；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 200`。
  4. 断言 `content-type` 含 `application/json`。
  5. 解析 body：断言键集**恰为** `{status, version}`（`HealthView` `additionalProperties:false`），`status == "ok"`，`version` 为**非空字符串**。
  6. （交叉核对，不改变本 case 判定）在环境快照中同时记录同一时刻 `/readyz` 的 status，用于说明存活与就绪的语义分离；本 case 不对 `/readyz` 做契约断言。
- **重点关注步骤**：① **`version` 是字符串**——§3.2 契约要求 `version:str`；现有 [`at_obs_01.py`](../../../../tests/system/api_test_v03/at_obs_01.py) 已断言 200 + `status=="ok"` + `version` 为非空字符串（脚本已补齐），本 case 与该断言一致。② **200 的真实含义**——`/healthz` 只证明进程存活，**不是**就绪；不得把 200 当作可接流量。③ **零凭据（`security:[]`）**——本 case 的凭据点必须由**裸客户端**（无 `Authorization`）发出；`api_client` 固定注入凭据，用它即失去零凭据语义（只有 AUTH-05 覆盖无 token，本 case 也不得冒充）。④ **不得被错误信封冒充**——若返回非 200，需确认是可解释环境问题（§9），而非把 `{"error":...}` 当 `HealthView` 读。⑤ 不在此 case 断言 `/readyz` 的 tier 状态（属 HEALTH-02..05）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `HealthView`（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），不依赖实现内部状态。
  - HTTP：`200`；响应头 `Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：JSON 对象，键集**恰为** `{status, version}`；`status=="ok"`；`version` 为非空字符串。
  - 无错误信封：不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 `{status,version}` 且 `status=="ok"` 且 `version` 为非空字符串。
  - **FAIL**：status ≠ 200，或 body 非合法 `HealthView`（键集/类型不符），或 `status ≠ "ok"`；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如断言不可实现、fixture 不可用）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 `127.0.0.1`/mock/替代路径冒充 m5air 真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：Case 有实现（§3.2 `RUN`）但本轮未执行——见[测试设计 §9](../llmtier-api-test-specification.md)；不得补造为 PASS。
- **证据与 Run**：保存发命令、exit code、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——纯读、无副作用、无凭据；不创建/修改 provider/deployment/service-level、不写注入、不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；**裸 `httpx` 客户端**（`M5AIR_BASE` 直连、无 `Authorization`；**不用** `api_client`）；`HealthView` 机器契约（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；自动化入口 [`at_obs_01.py`](../../../../tests/system/api_test_v03/at_obs_01.py)。**不依赖**其它 Case；与 HEALTH-02 共享同一探测入口但语义独立（存活 vs 就绪）。
