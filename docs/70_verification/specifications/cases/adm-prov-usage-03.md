# ADM-PROV-USAGE-03 — 刷新带确认

- **Case ID**：`ADM-PROV-USAGE-03`（与 §3.2 权威清单一致；本文件名 `adm-prov-usage-03.md`，唯一对应）。
- **标题**：`POST /v1/providers/{id}/usage` 携带 `{"confirm_external_call": true}` 刷新账号用量：HTTP 200 + 新 `ProviderAccountUsageSnapshot`；`provider_local`（local 类型）返回 `status="unlimited"`、`source="quota_config"`，并持久化快照。
- **目的（被测契约）**：验证 provider 账号用量**显式刷新成功契约**。被测端点/规则：`POST /v1/providers/{provider_id}/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `refreshProviderAccountUsage`，`security=AdminBearerAuth`），请求体 `{confirm_external_call: true}`（键集必须恰为 `{confirm_external_call}`）；成功 `200` + `ProviderAccountUsageSnapshot`，并按 `usage_provider` 分流：`local` → `_snapshot("local","quota_config","unlimited")`（[`AccountUsageService.refresh`](../../../../src/management/account_usage.py)），写 `provider_usage_snapshots`（`ON CONFLICT DO UPDATE`）；失败 400 `invalid_request`/`confirmation_required`、404 `not_found`。设计验证项 `VRC-MGMT-006`、`VRC-DIAG-004`；需求/机制链 `LT-FUN-005/006`、`LT-OPS-002`、`R-CFG-01`、`R-OBS-01`、`T-CFG-SECRET`、`CT-ADMIN-001`/`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明缺确认拒绝（ADM-PROV-USAGE-02）、不证明只读快照（ADM-PROV-USAGE-01）、不证明未知 provider 的 404（ADM-PROV-USAGE-04）、不证明 minimax/volc 的真实上游用量数值（本 case 用 `provider_local`，其刷新为本地合成、不触外部用量 API，故**不产生费用**）；不证明并发刷新。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[§4.4](../llmtier-api-test-specification.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 §2.1.6 必需的 `provider_local`（local 类型 → 刷新为本地 `unlimited` 快照，不触费用）。执行前记录 `GET /v1/providers/provider_local/usage` 的原快照（`checked_at`），用于复位核对。
- **输入与构造**：带确认刷新请求：
  ```http
  POST /v1/providers/provider_local/usage HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"confirm_external_call": true}
  ```
  构造点：body 键集**恰为** `{confirm_external_call}`、值为布尔 `true`；provider_id 固定为既存 `provider_local`；不注入故障；不构造非法输入。**值动态**：`checked_at` 为刷新时刻（动态），`windows`/`reset_at` 为实例/上游值，Oracle 只约束结构与 local 臂的枚举值。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 记录原快照：`before = admin_client.get("/v1/providers/provider_local/usage")`；记 `before.json()`（用于复位核对与证据）。
  3. `resp = admin_client.post("/v1/providers/provider_local/usage", json={"confirm_external_call": True})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  5. 解析 body：断言键集**恰为** `ProviderAccountUsageSnapshot` 的 12 键；`status ∈ {ok,unavailable,unsupported,unlimited,not_refreshed}`。
  6. 对 `provider_local`（local 类型）断言强值：`body["status"] == "unlimited"` 且 `body["source"] == "quota_config"`（`_snapshot("local","quota_config","unlimited")` 的确定输出）；若环境实际 kind 非 local，则退化为只断言 12 键 + 枚举（并在证据中记录 kind，作为偏差）。
  7. 回读：`after = admin_client.get("/v1/providers/provider_local/usage")`；断言 `200` 且 `after.json()["checked_at"] == resp.json()["checked_at"]`（刷新已持久化、GET 返回同一快照）。
- **重点关注步骤**：① **确认是成功前提**——只有 body 键集恰 `{confirm_external_call}` 且值为 `true` 才到刷新分支（缺键/值非真属 ADM-PROV-USAGE-02）；② **local 臂的确定输出**——`provider_local` 为 local，刷新不触外部 API，`status="unlimited"`、`source="quota_config"` 可强断言；③ **持久化副作用**——刷新写 `provider_usage_snapshots`（`ON CONFLICT DO UPDATE`），第 7 步回读同 `checked_at` 证明落库，**必须登记该写入**；④ **值动态**——`checked_at` 动态，不得硬编码；⑤ **无费用**——local 臂不产生外部调用（与 minimax/volc 臂不同），报告须写明未触费用；⑥ **不把错误信封当快照**——非 200 需先确认是可解释的 `ERR-*`（缺键→`invalid_request`、值非真→`confirmation_required`、未知 provider→`not_found`）。
  > **脚本覆盖缺口（登记，不在本 case 失败面）**：现有 [`at_adm_prov_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_03.py) 仅断言 `{provider,source,status,checked_at}` 四键存在，**未断言 12 键全集、`status` 枚举与 local 臂 `unlimited`/`quota_config` 强值**；按本设计需补齐后方可判本 case PASS。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderAccountUsageSnapshot` + `account_usage.refresh` 的 local 分流（不依赖上游）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：12 键全集；`provider_local` → `status=="unlimited"`、`source=="quota_config"`。
  - 回读：`GET .../usage` 返回相同 `checked_at` 的快照（持久化）。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 12 键快照 + local 臂 `status=="unlimited"`/`source=="quota_config"` + 回读 `checked_at` 一致。
  - **FAIL**：status 非 200、键集/枚举不符、local 臂值不符，或回读未持久化。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：伪造刷新响应、绕过真实确认键集，或替代路径冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：刷新请求/响应、刷新前/后 `GET .../usage`（含 `checked_at`，证明持久化）。
- **清理与复位**：**一次性写，尽力复位**——本 case 刷新 `provider_local` 的 `provider_usage_snapshots` 行（替换旧快照）。该端点**没有** DELETE 接口，且按[§2.8](../llmtier-api-test-specification.md) 不得删除 m5air 既有 provider/用户 usage；因此复位方式为：(a) 在 manifest 记录刷新前的原快照（第 2 步 `before`）作为基线对照；(b) 若需严格回滚到原 `checked_at`，由 operator 在授权下按运维手册对 SQLite 单行恢复（超出 HTTP 测试范围）；否则以"刷新后的快照"为新的合法状态。退出前确认 `/readyz` 7 tier、provider/deployment 列表未变、无未清空注入；不得因本 case 删除任何 provider/deployment/service-level。B 类整班结束由 fixture `stop()` + `rm -rf`（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；既存 provider `provider_local`（local 类型）；`ProviderAccountUsageSnapshot` 机器契约；实现 `src/management/account_usage.py`；自动化入口 [`at_adm_prov_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_03.py)。**不依赖**其它 Case；与 ADM-PROV-USAGE-02（缺确认拒绝）互补，各自独立执行。
