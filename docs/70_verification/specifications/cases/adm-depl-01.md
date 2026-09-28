# ADM-DEPL-01 — 列出 deployments

- **Case ID**：`ADM-DEPL-01`（与 §3.2 权威清单一致；本文件名 `adm-depl-01.md`，唯一对应）。
- **标题**：`GET /v1/deployments` 列出 deployment 分页页：HTTP 200 + `DeploymentPage`（`data[]` 含 m5air 已知 4 个 deployment，`page.has_more` 为 JSON 布尔）。
- **目的（被测契约）**：验证 Management Deployment CRUD 的**列表读契约**。被测端点/规则：`GET /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listDeployments`，`security=AdminBearerAuth`），认证角色 `admin`；成功返回 `DeploymentPage`（`data: DeploymentView[]`，`page: AdminPageMeta{has_more:boolean, next_cursor:string|null}`，`additionalProperties:false`）；失败走统一错误信封（401 `authentication_required` / 403 `permission_denied`）。列表按 `name,id` 排序，允许 `cursor`/`limit`（默认 `limit=100`，`_int_param`）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明创建/详情/更新/删除（ADM-DEPL-02..09）、不证明 capabilities 校验（ADM-DEPL-06/07）、不证明 `provider_id` 引用校验（ADM-DEPL-08/09）、不证明分页 `limit=1` cursor 推进（本 case 只观察 `page` 结构与存在性）；不证明 data/admin 角色隔离（AUTH-03）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项就绪检查**（§2.1.1–§2.1.6），由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`（`Bearer dev-admin`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier，其中 `dep_local_gemma`/`dep_local_bge_m3`/`dep_omlx_qwen36`/`dep_minimax_m27` 必在（§2.1.6）。**注意**：m5air 经多轮历史测试后 deployment 可能多于 4 个，故本 case **只断言包含关系**，不断言总数。
- **输入与构造**：固定请求（无请求体；本 case 不带 `cursor`/`limit`，走默认分页）：
  ```http
  GET /v1/deployments HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：固定 admin 角色；无 body；不注入故障；不构造非法输入（非法/缺凭据属 AUTH-*）。`page.has_more`/`next_cursor` 的**值不固定**（取决于 deployment 总数与 `limit=100`），只断言类型与结构。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/deployments")`；记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言 `data` 为数组、`page` 为对象；`page` 键集恰为 `{has_more, next_cursor}`（`additionalProperties:false`）。
  5. 断言 `isinstance(page["has_more"], bool)`；`next_cursor` 为字符串或 `null`。
  6. 计算 `ids = {d["id"] for d in data}`，断言基线集合 `{dep_local_gemma, dep_local_bge_m3, dep_omlx_qwen36, dep_minimax_m27}` ⊆ `ids`；抽查每个 `DeploymentView` 必填键 `{id,name,provider_id,backend_model,capabilities,enabled,health,version}` 齐备，且 `capabilities` 键集恰为 12 键。
- **重点关注步骤**：① **`page` 是嵌套对象**——不是顶层 `has_more`，读错层级即漏判；② **`has_more` 类型**——必须 JSON 布尔，不能是 `0/1`/字符串；③ **包含而非相等**——只断言 4 个基线 deployment 必在，不硬编码总数（A 类历史可能更多）；④ **每个 `DeploymentView.capabilities` 为 12 键全集**——列表元素也须满足 `ModelCapabilities`；⑤ **不得把错误信封当列表**——非 200 需先确认是可解释的 `ERR-AUTH-*`；⑥ **服务端读路径副作用**——[`admin.page()`](../../../../src/management/admin.py) 每次列表调用会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`），报告须登记该写入，**不得声称"零写入"**。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentPage`/`DeploymentView`/`AdminPageMeta` wire 形态（不依赖 m5air 具体数量）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：`data` 为 `DeploymentView[]`（元素含全部必填键、`capabilities` 12 键、`health ∈ {unknown,healthy,degraded,unhealthy}`）；`page` 键集恰为 `{has_more,next_cursor}`。
  - 基线：`{dep_local_gemma, dep_local_bge_m3, dep_omlx_qwen36, dep_minimax_m27}` ⊆ `data[].id`。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 `data` 合法 `DeploymentView[]` 且含 4 个基线 deployment 且 `page` 键集恰为 `{has_more,next_cursor}`、`has_more` 为 JSON 布尔。
  - **FAIL**：status 非 200 且存储/鉴权健康，或 body 非合法 `DeploymentPage`（缺 `page`/键集不符/`has_more` 非布尔/基线 deployment 缺失/`capabilities` 非 12 键）。
  - **BLOCKED**：测试代码/契约本身问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、基线 deployment 未注册）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 HTTP status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；`manifest.json` 必含 `target_artifact{git_commit,db_schema_version,openapi_version}`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`（`Authorization`）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需资源 teardown**——本 case 不改 deployment/provider/service-level、不写注入。第 6 步的服务端分页快照写入（`query_snapshots`，10 分钟 TTL）由服务端自身产生，A 类不手工删除系统表行，等待过期即可；退出前确认 `/readyz` 仍显示 7 tier、deployment 列表未变、无未清空注入项。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 §2.1.6 必需 deployment）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`DeploymentPage` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；自动化入口 [`at_adm_depl_01.py`](../../../../tests/system/api_test_v03/at_adm_depl_01.py)。**不依赖**其它 Case；与 ADM-DEPL-03（详情）共享读路径但各自独立执行。
