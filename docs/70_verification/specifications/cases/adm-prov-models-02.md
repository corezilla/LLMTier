# ADM-PROV-MODELS-02 — 不存在 provider

- **Case ID**：`ADM-PROV-MODELS-02`（与 §3.2 权威清单一致；本文件名 `adm-prov-models-02.md`，唯一对应）。
- **标题**：`GET /v1/providers/{id}/models` 读取不存在 provider 的上游模型目录：HTTP 404 + `error.code=="not_found"`，统一错误信封，无副作用。
- **目的（被测契约）**：验证 provider 上游模型目录的**未知 provider 负向契约**。被测端点/规则：`GET /v1/providers/{provider_id}/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviderModels`，`security=AdminBearerAuth`），认证角色 `admin`；未知 id 由 [`registry.get_provider`](../../../../src/management/registry.py)（`raise ApiError(404,"not_found",…)`，经 [`admin.list_provider_models`](../../../../src/management/admin.py) 先行解析）返回统一错误信封的 `404` + `code=not_found`；`type=request_error`（<500）、`param=null`、`retryable=false`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-NOTFOUND`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-SECRET`、`CT-ADMIN-001`。**不证明什么**：不证明既存 provider 的正常目录（ADM-PROV-MODELS-01）、不证明 provider 详情/usage 子路径的 404（ADM-PROV-04、ADM-PROV-USAGE-04）、不证明鉴权优先于存在性（AUTH-09）、不证明上游不可用路径（不在本负向 case 范围）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[§4.4](../llmtier-api-test-specification.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier。**自动化入口 `at_adm_prov_models_02.py` 当前 `MISSING`（§3.2）**。
- **输入与构造**：固定请求（无请求体；`{id}` 取保证不存在的字面量）：
  ```http
  GET /v1/providers/provider_does_not_exist_xyz/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{provider_id}` 取 `provider_does_not_exist_xyz`（不在 §2.1 基线，也不在上游目录）；无 body；不注入故障。**关键顺序**：该端点先经 `get_provider` 解析存在性，未知 id 在触上游 `/models` **之前**即 404（不得让上游请求先发生）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_does_not_exist_xyz/models")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 404`。
  4. `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`；`err["code"] == "not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`。
  5. （交叉核对，不改变判定）`GET /v1/providers/provider_does_not_exist_xyz` 断言同为 `404 not_found`，佐证根因是 provider 不存在而非 `/models` 子路径特例。
- **重点关注步骤**：① **状态与 code 双断言**——必须同时 `404` 且 `code==not_found`，只看到 404 不能通过（路由不命中也是 404）；② **信封 identity**——恰 5 键，`type` 由状态导出（404<500 ⇒ `request_error`），无 `category` 键，`param=null`、`retryable=false`；③ **触上游前拒绝**——未知 id 不得触发 `endpoint + /models`（避免把 404 变成上游错误）；④ **零副作用**——只读失败不写任何资源；⑤ **不依赖 message 文本**——Oracle 只约束 code/type/param/retryable；⑥ **不得硬编码其它 404**——不得把鉴权失败/上游失败混入本 case。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-NOTFOUND` 目录（不依赖实现文案）。
  - HTTP：`404`；`Content-Type: application/json`。
  - body：`{"error":{"code":"not_found","type":"request_error","param":null,"retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
  - 无资源变化，且未触碰上游目录端点。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 `error.code=="not_found"` 且信封 5 键、`type=="request_error"`、`param is None`、`retryable is False`，且无副作用。
  - **FAIL**：status 非 404（如 200/500）、`code` 不符、信封缺/多键、`type` 错，或未知 id 却触发了上游请求。
  - **BLOCKED**：测试代码/契约本身问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用替代路径/伪造 404 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9（MISSING ≠ NOT_RUN）。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`inputs` 为未知 `provider_id`。
- **清理与复位**：**无需 teardown**——负向读失败无写副作用。第/各步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。 退出前确认 `/readyz` 7 tier、provider 列表未变、无未清空注入。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` / `src/management/admin.py`；自动化入口 `at_adm_prov_models_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 ADM-PROV-MODELS-01 成对但各自独立。
