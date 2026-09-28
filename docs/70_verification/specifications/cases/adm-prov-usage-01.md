# ADM-PROV-USAGE-01 — 读取 provider usage 快照

- **Case ID**：`ADM-PROV-USAGE-01`（与 §3.2 权威清单一致；本文件名 `adm-prov-usage-01.md`，唯一对应）。
- **标题**：`GET /v1/providers/{id}/usage` 读取 provider 账号用量快照：HTTP 200 + 精确 `ProviderAccountUsageSnapshot`（12 个必填键），纯读、无副作用。
- **目的（被测契约）**：验证 Management **provider 账号用量快照读契约**。被测端点/规则：`GET /v1/providers/{provider_id}/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProviderAccountUsage`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + `ProviderAccountUsageSnapshot`（`additionalProperties:false`，`required` 恰 12 键：`provider,source,status,used,quota,remaining,percent,reset_at,window,windows,checked_at,error`；`status ∈ {ok,unavailable,unsupported,unlimited,not_refreshed}`）；失败走统一错误信封（401 `authentication_required` / 403 `permission_denied` / 404 `not_found`）。实现见 [`AccountUsageService.latest`](../../../../src/management/account_usage.py)（先查 `provider_usage_snapshots`，无快照则按 usage profile 合成 `not_refreshed`/credentials 快照）。设计验证项 `VRC-MGMT-006`；需求/机制链 `LT-FUN-005/006`、`LT-OPS-002`、`R-CFG-01`、`R-OBS-01`、`T-CFG-SECRET`、`CT-ADMIN-001`/`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明刷新（ADM-PROV-USAGE-02/03）、不证明未知 provider 的 404（ADM-PROV-USAGE-04）、不证明上游用量 API 的真实数值正确性（上游决定，本 case 只断言 wire 形状与枚举）、不证明 provider 详情/secret 不泄露（ADM-PROV-14）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项就绪检查**（§2.1.1–§2.1.6），由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`（`Bearer dev-admin`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 §2.1.6 必需的 `provider_local`。**注意状态依赖**：若同轮更早执行了 ADM-PROV-USAGE-03（刷新），则 `provider_usage_snapshots` 已存在该 provider 的快照，GET 返回刷新后的快照（`provider_local` 为 local，`status="unlimited"`、`source="quota_config"`）；否则返回合成快照（`status="not_refreshed"`、`source="store"`）。两者均 PASS，**不得**对具体 `status`/`source`/时间值做硬断言。
- **输入与构造**：固定请求（无请求体、无查询参数；`{id}` 取 `provider_local`）：
  ```http
  GET /v1/providers/provider_local/usage HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`provider_id` 固定为既存 `provider_local`；**无 body**、**无 query**（该端点不接受参数，不触上游——`GET` 只读已持久化/合成的快照）；不注入故障；不构造非法输入。**时间/窗口值动态**：`checked_at`/`reset_at`/`windows` 为运行时或上游值，Oracle 只约束结构与类型。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_local/usage")`；记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body，断言其为对象且键集**恰为** `ProviderAccountUsageSnapshot` 的 12 键（不多不少）。
  5. 断言 `status` 属于枚举 `{ok,unavailable,unsupported,unlimited,not_refreshed}`；`provider`/`source`/`window`/`reset_at`/`checked_at`/`error` 为字符串；`used`/`quota`/`remaining`/`percent` 为 number 或 `null`；`windows` 为数组（元素为对象）。
  6. （交叉核对，不改变判定）`GET /v1/providers/provider_local` 断言 `200` 且 `id=="provider_local"`，佐证快照归属的 provider 存在。
- **重点关注步骤**：① **字段集精确性**——不是"含 provider/status"，而是"键集恰为 12 键"，多/少一键即违反 `additionalProperties:false`；② **枚举约束**——`status` 只允许 5 个值之一，不能是任意字符串；③ **纯读、无副作用**——GET 不刷新、不触上游、不写 `provider_usage_snapshots`（刷新仅在 ADM-PROV-USAGE-03 的 POST）；④ **禁止硬编码动态值**——`checked_at`/`reset_at`/`windows`/`status` 随运行与上游变化，不得写成固定时间或固定 `ok`；⑤ **不得被错误信封冒充**——非 200 需确认是可解释的 `ERR-AUTH-*`/`ERR-NOTFOUND`，而非把 `{error:...}` 当快照读。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_prov_usage_01.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_01.py) 仅断言 `{provider,source,status,checked_at}` 四个键存在，**未断言 12 键全集与 `status` 枚举**；按本设计需补齐"键集恰等于 `ProviderAccountUsageSnapshot`"与枚举断言后方可判本 case PASS。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderAccountUsageSnapshot` wire 形态（不依赖 m5air 具体快照值）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：JSON 对象，键集**恰为** 12 键；`status` ∈ 枚举；数字字段为 number/`null`；`windows` 为数组（元素对象）。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 12 键、`status` 属枚举、各字段类型符合 schema（`provider_local` 既不要求特定 `status` 也允许 `not_refreshed`/`unlimited`）。
  - **FAIL**：status 非 200 且存储健康；或键集不符、`status` 非枚举、字段类型错；或以错误信封冒充快照。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`provider_local` 未注册等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或伪造快照——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；`manifest.json` 必含 `target_artifact{git_commit,db_schema_version,openapi_version}`、`inputs`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`（`Authorization`）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为纯读，不刷新快照、不改 provider/deployment/service-level、不写注入。退出前确认 `/readyz` 仍显示 7 tier、provider 列表未变、无未清空注入项；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 §2.1.6 必需 provider）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；既存 provider `provider_local`；`ProviderAccountUsageSnapshot` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；实现 `src/management/account_usage.py`；自动化入口 [`at_adm_prov_usage_01.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_01.py)。**不依赖**其它 Case；与 ADM-PROV-USAGE-02/03（POST 确认路径）、ADM-PROV-USAGE-04（未知 provider 404）语义相邻但各自独立执行。
