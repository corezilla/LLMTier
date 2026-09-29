# DP-USAGE-06 — 主体隔离：data ⊆ admin

- **Case ID**：`DP-USAGE-06`（与 §3.2 权威清单一致；本文件名 `dp-usage-06.md`，唯一对应）。
- **标题**：`GET /v1/usage` 的主体隔离：`data` 凭据只见到本主体（`consumer`）的 record，`admin` 凭据见到全局，`data` 结果集 ⊆ `admin` 结果集；data 产生的 cursor 以 admin 重放被拒 `403 permission_denied`。
- **目的（被测契约）**：验证 **Usage 读取的主体隔离与 cursor 绑定契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`）：openapi description 明确 "With a data credential the caller sees only its own records; with the admin credential the response includes all principals"；实现 `src/http_api/app.py` 经 `_auth_either()`→`authenticate_any()` 得 `is_admin`，`src/inference/usage.py::_page` 在 `not admin` 时追加 `h.principal_id=?` 过滤，admin 不加；cursor 的 `authorization_digest = sha256("admin"|principal)` 与 `principal_id` 绑定，跨主体重放 → `403 permission_denied`（**openapi↔code 差异须登记**：`openapi` 旧描述/响应曾把"过期/未授权/不匹配 cursor"一律归入 `400 invalid_request`，而实现区分——过期→`400 cursor_expired`、跨主体重放→`403 permission_denied`、filter 不匹配→`400 invalid_request`；本 case 以 **code 为准**取 `403 permission_denied`，openapi 已修正以对齐）。设计验证项 `VRC-MGMT-006`；机制 `T-TRUST-SHARED`、`R-MET-02`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.6/§4.7 与 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明 LAN 无 token 的免登录解析（`AUTH-01`/`§4.2`，且注意无 `Authorization` 会被解析为 **admin** 角色而非 data）、不证明分页内容（DP-USAGE-03）、过期 cursor（DP-USAGE-04）、同主体 cursor 重放幂等（DP-USAGE-07）、`DELETE /v1/usage` 的 admin 校验（ADM-USAGE-03）、store 不可用（DP-USAGE-08）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data` + `admin`，只读/无状态；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP。fixture（[§4.4](../llmtier-api-test-specification.md)）：api_client（data 主体 principal_id=`consumer`）、admin_client（admin 主体 principal_id=`operator`，见 §4.4）。初始状态：m5air 现有基线；embeddings tier `Embedding-v1`/`dep_local_bge_m3`（§2.1.6）可路由。**关键**：必须用**显式** `Authorization` 头区分角色；**不得**用无头 LAN trust 请求——`src/http_api/auth.py::unauthenticated_principal` 对无头发起者按 `role="admin"` 授予共享 admin 主体（`authenticate_any` 传入 `"admin"`），会使 data 侧隔离无从体现。窗口由 `constants.recent_window()` 动态生成。
- **输入与构造**：分别以两个主体各发一次 embeddings，再按 `request_id` 过滤查询（把窗口噪声排除）：
  ```http
  POST /v1/embeddings  (api_client,  Bearer dev-data)   → 捕获 X-Request-ID = rid_d
  POST /v1/embeddings  (admin_client, Bearer dev-admin) → 捕获 X-Request-ID = rid_a
  ```
  ```http
  GET /v1/usage?from=<w>&to=<w>&request_id=<rid_d>   (Bearer dev-data)   → 期望 1 条
  GET /v1/usage?from=<w>&to=<w>&request_id=<rid_a>   (Bearer dev-data)   → 期望 0 条
  GET /v1/usage?from=<w>&to=<w>&request_id=<rid_a>   (Bearer dev-admin)  → 期望 1 条
  ```
  跨主体 cursor：先 `GET /v1/usage?from&to&limit=1`（dev-data）取 `next_cursor=c_d`，再以 dev-admin 重放 `?from&to&limit=1&cursor=c_d`。
  构造点：embeddings body 固定（`model="Embedding-v1"`、固定输入）；`request_id` 用响应头 `X-Request-ID` 实际值；`from`/`to` 为同一动态窗口。
- **执行过程（逐步调用）**：
  1. `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复）。
  2. 以 `api_client` `POST /v1/embeddings`，断言 200，取 `rid_d`；以 `admin_client` 同法取 `rid_a`；断言两者非空且不同。
  3. `data_d = api_client.get("/v1/usage", params={"from":w0,"to":w1,"request_id":rid_d})`：断言 200 且 `data` 恰 1 条、`request_id==rid_d`。
  4. `data_a = api_client.get(..., request_id=rid_a)`：断言 200 且 `data == []`（data 不见 admin 主体记录）。
  5. `admin_a = admin_client.get(..., request_id=rid_a)`：断言 200 且 `data` 恰 1 条、`request_id==rid_a`。
  6. `admin_d = admin_client.get(..., request_id=rid_d)`：断言 200 且含 `rid_d`。
  7. **子集核对**：取一较宽窗口 `data_wide = api_client.get("?from&to&limit=200")`、`admin_wide = admin_client.get("?from&to&limit=200")`；断言 `{r.request_id for r in data_wide.data} ⊆ {r.request_id for r in admin_wide.data}`。
  8. **跨主体 cursor**：`first = api_client.get("?from&to&limit=1")`；设 `c_d = first.next_cursor`（若为 null，改用 `f"{first.snapshot_id}:0"`）；`resp = admin_client.get("?from&to&limit=1&cursor=c_d")`：断言 `status_code==403`、`error.code=="permission_denied"`、`error.type=="request_error"`。
- **重点关注步骤**：① **必须用显式 token**——无头请求被解析为 admin（`§4.2`），会破坏 data 侧断言；② **principal 名不固定写死**——`consumer`/`operator` 是当前实现默认（无 `X-Principal-ID` 时）；断言应基于"同主体可见、异主体不可见"，避免硬编码 `consumer`；③ **用 `request_id` 过滤**——A 类有全局历史，按 id 过滤是唯一确定构造；`rid_a` 在 data 侧应为**空数组**（200 而非 403/404），这是隔离语义；④ **子集而非相等**——admin 全局含其它主体，只断言 `data ⊆ admin`；⑤ **cursor 绑主体**——跨主体重放期望 `403 permission_denied`（`authorization_digest` 不匹配；注意 admin 分支先跳过 principal 比对，再由 digest 拒绝），不要与过期/不匹配混判；⑥ **cursor 为 null 的兜底**——若窗口内 `limit=1` 无更多记录，`next_cursor=null`，可用 `<snapshot_id>:0` 构同一快照的 cursor；⑦ **MISSING 语义**——无实现是缺口（NOT_RUN），不是跳过。
- **期望结果与独立 Oracle**：独立 Oracle = openapi `listUsage` description 的隔离语义 + 机制 cursor 绑定（`R-MET-02`：cursor 绑定 principal + 当前授权 + 原 filter）；跨主体 cursor 的拒绝码以**实现 code 为准**取 `403 permission_denied`（openapi 已修正对齐，见"目的"的 openapi↔code 差异注），不依赖实现返回顺序/内容。
  - `rid_d`：data 见 1 条、admin 见 ≥1 条。
  - `rid_a`：data 见 0 条（`data==[]`）、admin 见 1 条。
  - 宽窗口：data 的 `request_id` 集合 ⊆ admin 的 `request_id` 集合。
  - 跨主体 cursor：HTTP `403`，`error.code=="permission_denied"`，`error.type=="request_error"`，信封恰 5 键。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：步骤 3–8 全部 match（同主体可见、异主体在 data 侧不可见、子集成立、跨主体 cursor 403）。
  - **FAIL**：data 侧见到 admin 主体记录、或 admin 侧看不到自身记录、或子集不成立、或跨主体 cursor 未被拒（返回 200/其它码）。
  - **BLOCKED**：断言逻辑/契约问题、双主体前置无法命中——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用无头/带 token 混淆冒充角色、mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存两次前置 embeddings（含 `X-Request-ID`）、各主体查询的请求/响应（`request_id`、`data` 长度、cursor 值）、宽窗口集合、跨主体重放的原始响应、动态窗口值、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。
- **清理与复位**：**无需额外 teardown**——两次 embeddings 属被测行为，不删用户 usage（§2.8）；查询只创建 10 分钟 TTL 快照；不改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按[测试设计 §4.7](../llmtier-api-test-specification.md) 销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查与 [§4.2](../llmtier-api-test-specification.md) 鉴权模型；`api_client`/`admin_client`（[§4.4](../llmtier-api-test-specification.md)）；embeddings tier `Embedding-v1`；机制 [`usage-metering` §4.6/§4.7](../../../20_system_design/mechanisms/usage-metering.md)、[`access-trust`](../../../20_system_design/mechanisms/access-trust.md)；`listUsage` 机器契约。自动化入口 `at_dp_usage_06.py`（**当前 `MISSING`**）。**不依赖**其它 Case；与 AUTH-01（LAN 免登录）、AUTH-03（data 访问 admin 面 403）区分但机制相邻；与 DP-USAGE-07（同主体重放）互补。
