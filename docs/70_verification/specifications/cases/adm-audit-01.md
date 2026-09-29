# ADM-AUDIT-01 — 审计事件 + 脱敏

- **Case ID**：`ADM-AUDIT-01`（与 §3.2 权威清单一致；本文件名 `adm-audit-01.md`，唯一对应）。
- **标题**：`GET /v1/audit` 返回字段齐全（含 `request_id`）且脱敏的审计事件：HTTP 200 + `AuditPage`，默认 `limit=50`。
- **目的（被测契约）**：验证审计读取的**字段完整性、默认条数与脱敏契约**。被测端点/规则：`GET /v1/audit`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listAuditEvents`，query `limit` 默认 `50`、`minimum:1`/`maximum:200`，`security=AdminBearerAuth`）；[`AuditLog.page`](../../../../src/management/audit.py) `ORDER BY created_at DESC,id DESC LIMIT min(limit,200)`，返回 `{data:[AuditEvent],page:{has_more,next_cursor}}`；[`AuditEvent`](../../../../interfaces/openapi/llmtier.openapi.json) 必填 7 键 `{id,actor,action,target,result,created_at,request_id}`（`request_id` 可 null）。设计验证项 `VRC-MGMT-003`；机制 `R-OBS-01`、`T-TRUST-LEAK`；需求/机制链 `LT-FUN-006`、`LT-SEC-004`、`CT-ADMIN-001`、`CT-LOG-001`。**不证明什么**：不证明 `limit=1` 分页（ADM-AUDIT-02）、不证明非法 `limit` 400（ADM-AUDIT-03）、不证明 operational logs 脱敏（ADM-LOGS-01）、不证明 provider 读取不回显 secret（ADM-PROV-14）。本 case 锁定"字段齐全 + 无 secret 泄露 + 默认 limit"。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态：m5air 审计表非空（bootstrap 及既往管理操作已写 `audit_events`）。本 case 只读。
- **输入与构造**：
  ```http
  GET /v1/audit HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：**不传 `limit`**（用默认 50，验证默认值）；无 body；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/audit")`；记录 status、body 原文（`resp.text` 用于脱敏扫描）。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言含 `data`（数组）与 `page`；`page` 键集恰 `{has_more,next_cursor}`。
  5. 断言 `len(data) <= 50`（默认 `limit=50`）；进一步断言 `data` 每条键集**恰为** `{id,actor,action,target,result,created_at,request_id}`——**特别断言 `request_id` 键存在**（可 null）。
  6. 脱敏断言：`resp.text` **不含**上游 secret 字面 `"9832"`、key 文件名 `"omlx-secret-key.txt"`、`"mnm_api_key"`、`"Bearer "` 后的真实凭据、`"secret"` 明文值。
- **重点关注步骤**：① **`request_id` 键必须存在**——`AuditEvent.required` 含 `request_id`（可 null），仅断"data 是数组"不足（现有 [`at_adm_audit_01.py`](../../../../tests/system/api_test_v03/at_adm_audit_01.py) 只断数组与脱敏，**未断 7 字段**，须补齐）；② **默认 `limit=50`**——无参请求 `len(data) ≤ 50`（`AuditLog.page` 默认 50、上限 200）；③ **脱敏**——审计 `target`/`action` 等不得回显 secret；注意 `AuditLog.record` 存的是 `actor/action/target/result`，本身不含 header/凭据，但仍须显式断言（防未来字段泄漏）；④ **`type` 字段非本 case**——`AuditEvent` 无 `type` 键，不得按错误信封 5 键预期；⑤ **纯读**——`GET /v1/audit` 不写审计（读操作不产生审计行）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `AuditPage`/`AuditEvent` + 默认 `limit=50` + `T-TRUST-LEAK` 脱敏规则。
  - HTTP：`200`；body `{"data":[...≤50...],"page":{"has_more":false,"next_cursor":null}}`。
  - 每条含 7 键 `{id,actor,action,target,result,created_at,request_id}`。
  - 响应文本不含 `9832`/`omlx-secret-key.txt`/`mnm_api_key`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `data` 数组 + 每条 7 键齐全（含 `request_id`）+ `len(data)≤50` + 无敏感字面。
  - **FAIL**：status 非 200、`page`/`data` 形状错、缺 `request_id` 或任一 `AuditEvent` 键、`len(data)>50`、或含敏感字面。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air，或把脱敏扫描当作"注入命中"——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 HTTP status/headers/body（入库前将 Authorization、`9832`、key 文件内容脱敏）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读，不改审计/配置/注入。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`AuditPage`/`AuditEvent` 机器契约；`AuditLog.page`；机制 `R-OBS-01`/`T-TRUST-LEAK`。自动化入口 [`at_adm_audit_01.py`](../../../../tests/system/api_test_v03/at_adm_audit_01.py)（**须补齐 7 字段断言后方可判 PASS**）。**不依赖**其它 Case；与 ADM-AUDIT-02/03、ADM-LOGS-01 互补。
