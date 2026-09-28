# ADM-PROV-02 — 创建 provider

- **Case ID**：`ADM-PROV-02`（与 §3.2 权威清单一致；本文件名 `adm-prov-02.md`，唯一对应）。
- **标题**：`POST /v1/providers` 创建 provider：HTTP 201 + 自动 `id` + `has_secret`/`version` + `ETag` 响应头，且可经 `GET /v1/providers/{id}` 回读。
- **目的（被测契约）**：验证 Management Provider CRUD 的**创建写契约**。被测端点/规则：`POST /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createProvider`，`security=AdminBearerAuth`），请求体契约为 `ProviderWrite{name,kind,endpoint,secret_ref,enabled(,usage?)}`；成功 `201 Created` + body `ProviderView` + 响应头 `ETag: "<id>.v<N>"`；`id` 由服务端自动生成（`_id("provider")` → `provider_<hex>`），`has_secret = (secret_ref is not None)`，初始 `version=1`；失败走统一错误信封（400 `invalid_request` / 409 `resource_conflict`）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明更新/删除/If-Match（ADM-PROV-05..10）、不证明 `kind`/`secret_ref` 负向（ADM-PROV-11/12）、不证明 `usage` 子对象更新（ADM-PROV-13）、不证明重名 409（本 case 用随机名避开）、不证明响应不含 secret 的强断言（ADM-PROV-14）；创建不触上游，故不证明 provider 可达性。
- **前置与环境**：**环境 B**（临时 LLMTier 实例：`127.0.0.1:<随机空闲端口>` + 临时 SQLite，同机第二个进程；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动且 `GET /healthz` 200；初始状态 = `_BASELINE_SETTINGS`（1 provider `prov_b` + 1 deployment `depl_b` + 7 fixed tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`httpx.Client`，`Authorization: Bearer dev-admin`，base_url=`llmtier_b.base_url`）。**TS-003**：新建 provider 的 `endpoint` 必须为 LAN IP（测试常量 `LAN_PROVIDER_ENDPOINT`，默认 `http://192.168.1.9:9000/v1`，可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1` 作为上游 endpoint**。创建不触上游，endpoint 仅在后续使用时可解析即可。
- **输入与构造**：固定请求（随机名避免与既有 provider 重名）：
  ```http
  POST /v1/providers HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Test Provider <uuid8>",
    "kind": "local",
    "endpoint": "http://192.168.1.9:9000/v1",
    "secret_ref": null,
    "enabled": true
  }
  ```
  构造点：`kind` ∈ `{cloud,local}`（本 case 取 `local`）；`secret_ref` 为 `null`（→ `has_secret=false`）；`enabled=true`；`name` 取 `Test Provider <uuid4 前 8 位>` 保证唯一；请求体键集 ⊆ `{name,kind,endpoint,secret_ref,enabled,usage}`。不注入故障；不构造非法输入（负向属 ADM-PROV-11/12）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `resp = admin_client_b.post("/v1/providers", json=body)`；断言 `status_code == 201`。
  3. 解析 body（`ProviderView`）：断言 `name`/`kind`/`endpoint`/`enabled` 回显与请求一致；`id` 存在且为非空字符串；`version == 1`；`has_secret is False`；`usage`/`request_usage` 为对象。
  4. 断言响应头含 `ETag`，值等于 `"<id>.v1"`（格式 `"<resource_id>.v<N>"`，含双引号，[`registry._etag`](../../../../src/management/registry.py)）。
  5. `get_resp = admin_client_b.get(f"/v1/providers/{rid}")`；断言 `200`、`name` 一致、`get_resp.headers["ETag"] == create` 的 ETag（版本未推进）。
  6. （teardown，`finally` 内）以最新 `GET` 的 `ETag` 发 `DELETE /v1/providers/{rid}`，断言 `204`；再 `GET` 断言 `404`。
- **重点关注步骤**：① **201 而非 200**——创建成功必须是 `201`，`ETag` 头必须存在；② **自动 id 与 version 初值**——`id` 由服务端生成、`version==1`，不得回显客户端未提供的字段为随机值；③ **ETag 格式与版本一致性**——`"<id>.v1"` 含双引号，回读 ETag 与创建一致；④ **`has_secret` 语义**——`secret_ref=null` ⇒ `has_secret=false`，且响应体**不含** `secret_ref` 键（ADM-PROV-14 的强断言）；⑤ **拒绝零副作用**——若收到 400/409，须确认账本/资源无新建（本 case 用唯一名，不应命中 409）；⑥ **teardown 必达**——创建的 provider 无 deployment 引用，可安全 `DELETE`；若 `DELETE` 412，先重新 `GET` 取新 ETag 再删。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderView` + `ProviderWrite` + ETag 规则（不依赖实现细节）。
  - 创建：`201`；body `{id:"provider_<hex>",name,kind:"local",endpoint,has_secret:false,enabled:true,usage:…,request_usage:{calls:0,input_tokens:null,output_tokens:null,total_tokens:null},version:1}`；响应头 `ETag: "<id>.v1"`。
  - 回读：`GET /v1/providers/{id}` → `200`，同 `name`、同 `ETag`。
  - teardown：`DELETE`（正确 If-Match）→ `204`；随后 `GET` → `404 not_found`。
  - 无错误信封：成功路径不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：创建 `201` + 自动 id + `version==1` + `has_secret==false` + ETag `"<id>.v1"`；回读 `200` 且 ETag 一致；teardown `DELETE 204` 且随后 `GET 404`。
  - **FAIL**：任一断言不符（status 非 201、缺 ETag、字段错、回读失败、teardown 未删净）——按[测试设计 §9](../llmtier-api-test-specification.md) 给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture 写不出、断言逻辑错、语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用、依赖 fixture 未满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 `127.0.0.1` 作为新建 provider 的 `endpoint`（违反 TS-003）、或以 mock/替代路径冒充真实实例——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存创建请求/响应（status/headers 含 `ETag`/body）、回读响应、teardown 的 DELETE 与后续 GET、发出命令、exit code、`elapsed`、环境快照（`/healthz` + provider 列表脱敏）；`manifest.json` 必含 `{run_id,case_id,target_artifact{git_commit,db_schema_version,openapi_version},environment:"b",inputs(含 endpoint 为 LAN IP),oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 创建的 provider（`DELETE`，必要时先 `GET` 取新 ETag）；不修改 `prov_b`/`depl_b`、不写注入。B 类实例整班结束由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `rm -rf` 临时目录销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。离开前确认无本次创建物残留。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ProviderWrite`/`ProviderView` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；ETag 规则 `registry._etag`；自动化入口 [`at_adm_prov_02.py`](../../../../tests/system/api_test_v03/at_adm_prov_02.py)。**不依赖**其它 Case；与 ADM-PROV-05..13 共享同一写路径但各自独立执行（每个 B 类写 case 自建/自清）。
