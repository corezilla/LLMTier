# ADM-PROV-MODELS-01 — provider 上游模型目录

- **Case ID**：`ADM-PROV-MODELS-01`（与 §3.2 权威清单一致；本文件名 `adm-prov-models-01.md`，唯一对应）。
- **标题**：`GET /v1/providers/{id}/models` 读取 provider 上游模型目录：HTTP 200 + `ProviderModelsView`（`data: string[]`），同步只读且不改任何本地资源。
- **目的（被测契约）**：验证 Management **provider 上游模型目录读契约**。被测端点/规则：`GET /v1/providers/{provider_id}/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviderModels`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + `ProviderModelsView`（`data: string[]`，`additionalProperties:false`，`required=[data]`）；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（401 `authentication_required` / 403 `permission_denied` / 404 `not_found`）。实现见 [`admin.list_provider_models`](../../../../src/management/admin.py) → [`registry.get_provider`](../../../../src/management/registry.py) → [`OpenAIProvider.list_models`](../../../../src/inference/providers/openai.py)（`[m["id"] for m in payload.get("data", []) if isinstance(m.get("id"), str)]`——即 `data` 缺省按空数组处理，且仅保留 `id` 为字符串的元素）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-SECRET`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明未知 provider 的 404（ADM-PROV-MODELS-02）、不证明 provider 读取不回显 secret（ADM-PROV-14）、不证明 deployment/provider CRUD（ADM-PROV-*/ADM-DEPL-*）、不证明上游目录**内容正确**（上游模型 ID 由上游决定，本 case 只断言 `data` 为字符串数组，**不把具体模型名当 oracle**）；本 case 为注册表（A 类）上的只读目录查询，允许触上游 `/models`（只读），不产生费用类副作用。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[§4.4](../llmtier-api-test-specification.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 §2.1.6 必需的 `provider_local`（必在，避免依赖历史 provider）。**自动化入口 `at_adm_prov_models_01.py` 当前 `MISSING`（§3.2）**，尚无实现，落位与命名按 §4.9/§8.5。
- **输入与构造**：固定请求（无请求体、无查询参数；`{provider_id}` 取 `provider_local`）：
  ```http
  GET /v1/providers/provider_local/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`provider_id` 固定为注册表内既存 provider（`provider_local`）；**无 body**（GET 不携带）；**无 query**（该端点不接受参数）；不注入故障；不构造非法输入（非法/缺凭据属 AUTH-*，未知 id 属 ADM-PROV-MODELS-02）。`data` 的**元素值不固定**（上游决定），只断言 `data` 为字符串数组。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_local/models")`；记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言其为对象且键集**恰为** `{data}`（`additionalProperties:false`，多一个键即违反）。
  5. 断言 `isinstance(body["data"], list)` 且 `all(isinstance(x, str) for x in body["data"])`；允许空数组（上游无模型），但**不得**出现对象/数字元素。
  6. （交叉核对，不改变本 case 判定）`GET /v1/providers/provider_local` 断言 `200`，佐证该 provider 存在（200 是"既存 provider 的目录读取"，不是未知 id 的兜底）。
- **重点关注步骤**：① **键集精确性**——不是"含 `data`"，而是"键集恰为 `{data}`"，防止 provider 视图字段误并入；② **元素类型**——必须是字符串（上游 `/models` 返回对象，网关按 `id` 投影），把对象当元素即违反 `ProviderModelsView`；③ **不硬编码模型名**——上游目录随环境变化，Oracle 只约束 `string[]`；④ **允许触上游**——该端点会调 `provider.endpoint + /models`（只读目录，[测试设计 §11/§4.10](../llmtier-api-test-specification.md)），执行者需授权并登记；`confirm_external_call` **不**是此只读路由的参数（对比 ADM-PROV-USAGE/PROBE）；⑤ **admin 面**——data/none 凭据的 401/403 由 AUTH 家族承接，本 case 不重测；⑥ **不得把错误信封当目录**——非 200 必须先确认是可解释的 `ERR-*`，而非把 `{error:...}` 当 `data` 读。
  > **实现 vs 契约偏差（登记，不在本 case 失败面）**：系统设计 §`GET /v1/providers/{provider_id}/models` 与 `openapi` 声明"上游不可用 → `ERR-PROVIDER-UNAVAIL`（503）"，但 [`admin.list_provider_models`](../../../../src/management/admin.py) / [`OpenAIProvider.list_models`](../../../../src/inference/providers/openai.py) 未捕获 `urllib` 异常；上游故障会落 `_run` 的兜底分支返回 **500 `internal_error`**（`sqlite3.Error` 才映射 503 `usage_store_unavailable`）。本 case 只走 happy path，不据此判 FAIL；偏差在运行报告登记。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderModelsView` wire 形态（不依赖上游具体模型名）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：JSON 对象，键集**恰为** `{data}`；`data` 为数组，元素均为 JSON 字符串。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 `{data}` 且 `data` 为字符串数组（含空数组）。
  - **FAIL**：status 非 200 且实例/上游健康；或 body 键集不符/`data` 非数组/含非字符串元素；或以错误信封冒充目录。
  - **BLOCKED**：无法执行/无法判定且可重试（测试代码/契约问题、上游目录端点在窗口内不可达而无法建立 Oracle）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线、`provider_local` 未注册）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或伪造目录列表——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：上游目录端点被调用的事实记录；`inputs` 含 `provider_id`。
- **清理与复位**：**无需资源 teardown**——本 case 为只读 `GET`，不改 provider/deployment/service-level、不写注入、不写快照（仅查询上游目录）。退出前确认 `/readyz` 仍显示 7 tier、provider 列表未变、无未清空注入项；若被误跑于 B 类临时实例，则按[§4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 §2.1.6 必需 provider/deployment）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；既存 provider `provider_local`；`ProviderModelsView` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；实现 `src/management/admin.py` / `src/inference/providers/openai.py`；自动化入口 `at_adm_prov_models_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 ADM-PROV-MODELS-02（未知 provider → 404）成对但各自独立执行。
