# ADM-DEPL-03 — 获取 deployment

- **Case ID**：`ADM-DEPL-03`（与 §3.2 权威清单一致；本文件名 `adm-depl-03.md`，唯一对应）。
- **标题**：`GET /v1/deployments/{id}` 读取既存 deployment：HTTP 200 + `DeploymentView` + `ETag`，纯读、无副作用。
- **目的（被测契约）**：验证 Management Deployment CRUD 的**详情读契约**。被测端点/规则：`GET /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getDeployment`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + `DeploymentView`（`id,name,provider_id,backend_model,capabilities,enabled,health,version`，`additionalProperties:false`）+ 响应头 `ETag: "<id>.v<N>"`（[`registry.get_deployment`](../../../../src/management/registry.py)）；未知 id → 404 `not_found`；失败走统一错误信封（401/403）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明列表（ADM-DEPL-01）、不证明创建/更新/删除（ADM-DEPL-02/04/05）、不证明未知 id 的 404（本 case 只读既存 `dep_local_gemma`）、不证明 `capabilities` 校验（ADM-DEPL-06/07）；本 case 只读、不触上游。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[§4.4](../llmtier-api-test-specification.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 deployment 取 §2.1.6 必需的 `dep_local_gemma`（必在）。
- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/deployments/dep_local_gemma HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{deployment_id}` 固定为既存 `dep_local_gemma`；无 body、无 query；不注入故障；不构造非法输入（未知 id 属其它负向 case）。`version`/`health` 值与运行状态有关，只断言字段存在与类型。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/deployments/dep_local_gemma")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言键集恰为 `DeploymentView` 的 8 键；`body["id"] == "dep_local_gemma"`、`name/provider_id/backend_model` 为字符串、`enabled` 为布尔、`version` 为正整数、`health ∈ {unknown,healthy,degraded,unhealthy}`。
  5. 断言 `body["capabilities"]` 键集恰为 12 键（`ModelCapabilities`）。
  6. 断言响应头含 `ETag` 且匹配 `^"[A-Za-z0-9._:-]+"$`，且等于 `f'"{body["id"]}.v{body["version"]}"'`。
- **重点关注步骤**：① **字段集精确性**——键集恰为 8 键，多/少一键违反 `additionalProperties:false`；② **`capabilities` 12 键**——详情元素也须满足全集；③ **ETag 与 version 一致**——`ETag == "<id>.v<version>"`（含双引号），这是后续 PATCH/DELETE 的前置；④ **纯读**——GET 不写任何资源（`get_deployment` 只 SELECT）；⑤ **不硬编码 version/health**——随运行变化，只断言类型/枚举与 ETag 一致性；⑥ **不得把错误信封当详情**——非 200 需先确认是可解释的 `ERR-AUTH-*`/`ERR-NOTFOUND`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentView` + ETag 格式（不依赖 m5air 运行态）。
  - HTTP：`200`；`Content-Type: application/json`；响应头 `ETag=="<id>.v<version>"`。
  - body：键集恰 8 键；`id=="dep_local_gemma"`；`capabilities` 12 键；`health` 属枚举。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` + 8 键 `DeploymentView` + `capabilities` 12 键 + `id` 匹配 + `ETag` 与 version 一致。
  - **FAIL**：status 非 200 且资源存在/鉴权健康，或键集/类型/`capabilities`/ETag 不符。
  - **BLOCKED**：测试代码/契约本身问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（`dep_local_gemma` 未注册等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用替代路径/伪造详情冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`inputs` 含 `deployment_id`。
- **清理与复位**：**无需 teardown**——本 case 为纯读，不改 deployment/provider/service-level、不写注入。退出前确认 `/readyz` 7 tier、deployment 列表未变、无未清空注入；若误跑于 B 类实例，则整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 §2.1.6 必需 deployment）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；既存 deployment `dep_local_gemma`；`DeploymentView` 机器契约；实现 `src/management/registry.py` `get_deployment`；自动化入口 [`at_adm_depl_03.py`](../../../../tests/system/api_test_v03/at_adm_depl_03.py)。**不依赖**其它 Case；与 ADM-DEPL-01 共享读路径但各自独立执行。
