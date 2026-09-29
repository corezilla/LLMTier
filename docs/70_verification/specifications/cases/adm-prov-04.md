# ADM-PROV-04 — 不存在 provider

- **Case ID**：`ADM-PROV-04`（与 §3.2 权威清单一致；本文件名 `adm-prov-04.md`，唯一对应）。
- **标题**：`GET /v1/providers/{id}` 读取不存在 provider：HTTP 404 + `error.code=="not_found"`，统一错误信封，无副作用。
- **目的（被测契约）**：验证 Management Provider CRUD 的**不存在负向契约**。被测端点/规则：`GET /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProvider`，`security=AdminBearerAuth`），认证角色 `admin`；未知 id 走统一错误信封 `{error:{message,type,code,param,retryable}}` 的 `404` + `code=not_found`（[`registry.get_provider`](../../../../src/management/registry.py) `raise ApiError(404,"not_found",…)`）；`type=request_error`（<500）、`param=null`、`retryable=false`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-NOTFOUND`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明存在（ADM-PROV-03）、不证明 update/delete 的 404（更新/删除未知 id 同属 `not_found`，但本 case 只发 GET）、不证明 `/usage`、`/models` 子路径的 404（ADM-PROV-MODELS-02、ADM-PROV-USAGE-04）、不证明鉴权优先于存在性（AUTH-09）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[§4.4](../llmtier-api-test-specification.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 tier。
- **输入与构造**：固定请求（无请求体）：
  ```http
  GET /v1/providers/provider_does_not_exist_xyz HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{id}` 取一个保证不存在的字面量 `provider_does_not_exist_xyz`；无 body；不注入故障；不构造其它非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_does_not_exist_xyz")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 404`。
  4. `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`；`err["code"] == "not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`。
  5. 交叉核对：再次 `GET /v1/providers`，确认 provider 集合未因本次请求变化（**provider 列表无新增/删除**；注意该列表 GET 自身会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照，见 `admin.page()`，此为服务端读路径副作用、非 provider 资源变化，不得据此判 FAIL）。
- **重点关注步骤**：① **状态与 code 双断言**——必须同时 `404` 且 `code==not_found`，不能只看到 404 就通过（404 也可能来自路由不命中）；② **信封 identity**——恰 5 键，`type` 由状态导出（404<500 ⇒ `request_error`），无 `category` 键，`param=null`、`retryable=false`；③ **对 provider 资源零副作用**——校验/读取失败在 dispatch 前完成，不改任何资源；第 5 步确认 provider 集合不变；但 **第 5 步的列表 GET 会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照**（`admin.page()`），这是服务端实现行为、非用户资源，报告须登记该写入，**不得笼统声称"零写入"**；④ **错误源可解释**——不得把鉴权失败（401/403）或路由 404 混入本 case（凭据固定 admin 且路径存在）；⑤ **不依赖 message 文本**——Oracle 只约束 code/type/param/retryable，不对 `message` 语义断言。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-NOTFOUND` 目录（不依赖实现文案）。
  - HTTP：`404`；`Content-Type: application/json`。
   - body：`{"error":{"code":"not_found","type":"request_error","param":null,"retryable":false, "message":"<nonempty>"}}`（恰 5 键）。
   - 无 provider 资源变化：provider 集合与请求前一致（列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 `error.code=="not_found"` 且信封 5 键、`type=="request_error"`、`param is None`、`retryable is False`，且 provider 集合无变化（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 404（如 200/500）、`code` 不符、信封缺/多键、`type` 错，或出现 provider 资源副作用。
  - **BLOCKED**：测试代码/契约本身问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用替代路径/伪造 404 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：请求前后 provider 列表快照。
- **清理与复位**：**无需 teardown**——负向读失败对 provider 资源无写副作用；第 5 步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，等待过期即可，不手工删除。退出前确认 `/readyz` 仍 7 tier、无未清空注入项；若误跑于 B 类实例，则按[§4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ErrorEnvelope` 机器契约；自动化入口 [`at_adm_prov_04.py`](../../../../tests/system/api_test_v03/at_adm_prov_04.py)。**不依赖**其它 Case；与 ADM-PROV-03 成对但各自独立。
