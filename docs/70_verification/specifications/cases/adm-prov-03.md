# ADM-PROV-03 — 获取 provider 详情

- **Case ID**：`ADM-PROV-03`（与 §3.2 权威清单一致；本文件名 `adm-prov-03.md`，唯一对应）。
- **标题**：`GET /v1/providers/{id}` 读取已存在 provider 详情：HTTP 200 + `ProviderView` 全字段 + `ETag` 响应头，纯读。
- **目的（被测契约）**：验证 Management Provider CRUD 的**详情读契约**。被测端点/规则：`GET /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProvider`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + body `ProviderView{id,name,kind,endpoint,has_secret,enabled,usage,request_usage,version}` + 响应头 `ETag: "<id>.v<N>"`；失败走统一错误信封（404 `not_found`）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明列表（ADM-PROV-01）、不证明创建/更新/删除（ADM-PROV-02/05..10）、不证明不存在 404 的完整负向（ADM-PROV-04）、不证明 `usage` 子对象可写（ADM-PROV-13）、不证明响应不含 secret 的强断言（ADM-PROV-14）；`request_usage` 的具体计数依赖历史 usage，本 case 只断言字段存在与类型。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项就绪检查**（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX、m5mac OMLX、`provider_omlx_m5mac.secret_ref` 为 `file:`、必需 provider/deployment 已注册），由 `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`（`httpx.Client`，`Bearer dev-admin`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 tier；本 case 固定读取 `provider_local`（§2.1.6 保证存在）。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers/provider_local HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{id}` 固定为就绪检查保证存在的 `provider_local`；无 body；不注入故障；不构造非法输入（不存在 id 属 ADM-PROV-04）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_local")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言必填字段全在 `{id,name,kind,endpoint,has_secret,enabled,usage,request_usage,version}`；`id == "provider_local"`；`kind ∈ {cloud,local}`；`has_secret`/`enabled` 为 JSON 布尔；`version` 为正整数；`usage` 为 `ProviderUsageProfileView`（含 `usage_provider`、`max_concurrent_requests` 等）；`request_usage` 为 `{calls,input_tokens,output_tokens,total_tokens}`。
  5. 断言响应头含 `ETag`，格式匹配 `"provider_local.v<N>"`（含双引号）。
  6. 断言 body 不含顶层 `secret_ref` 键、不含解析后的 secret 值（与 ADM-PROV-14 一致的读路径，此处为旁证）。
- **重点关注步骤**：① **字段完整性**——`ProviderView` 为 `additionalProperties:false` 且必填 9 键，缺键/多键即 FAIL；② **类型精确性**——`has_secret`/`enabled` 为布尔、`version` 为整数；③ **ETag 格式**——必须 `"<id>.v<N>"` 含双引号（`_etag`），不是裸 `id.vN`；④ **纯读、无副作用**——详情路径不写库、不铸分页快照（与列表 ADM-PROV-01 不同）；⑤ **不依赖 usage 数值**——`request_usage` 计数随历史变化，只断言结构与类型；⑥ **不得把错误信封当详情**——非 200 需先确认是可解释的 `ERR-AUTH-*`/`ERR-NOTFOUND`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderView` wire 形态 + ETag 规则（不依赖 m5air 数据）。
  - HTTP：`200`；`Content-Type: application/json`；响应头 `ETag: "provider_local.v<N>"`。
  - body：`ProviderView` 9 必填键齐备且类型正确；`id=="provider_local"`；无 `secret_ref` 键、无 secret 值。
  - 无错误信封：成功路径不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 9 必填键齐备、类型正确、`id=="provider_local"`、ETag 格式匹配。
  - **FAIL**：status 非 200 且资源健康，或字段缺失/类型错/ETag 不符，或响应回显 `secret_ref`/secret 值。
  - **BLOCKED**：测试代码/契约本身问题（断言不可实现、语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（含 `provider_local` 未注册）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必含 `target_artifact` 与 `redactions`（`Authorization`）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——纯读，不改 provider/deployment、不写注入、不铸分页快照。退出前确认 `/readyz` 仍 7 tier、`provider_local` 列表未变、无未清空注入项。若被误跑于 B 类实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 `provider_local` 注册）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ProviderView` 机器契约；自动化入口 [`at_adm_prov_03.py`](../../../../tests/system/api_test_v03/at_adm_prov_03.py)。**不依赖**其它 Case；与 ADM-PROV-04（不存在 → 404）成对但各自独立。
