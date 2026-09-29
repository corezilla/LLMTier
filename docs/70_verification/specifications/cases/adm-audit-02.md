# ADM-AUDIT-02 — 审计分页

- **Case ID**：`ADM-AUDIT-02`（与 §3.2 权威清单一致；本文件名 `adm-audit-02.md`，唯一对应）。
- **标题**：`GET /v1/audit?limit=1` 有界分页：HTTP 200 + `data.length ≤ 1` + `page.has_more`/`next_cursor` 一致。
- **目的（被测契约）**：验证审计的**有界页契约**。被测端点/规则：`GET /v1/audit`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listAuditEvents`，query `limit` 默认 50/上限 200）；[`AuditLog.page`](../../../../src/management/audit.py) `LIMIT max(1,min(limit,200))`，固定返回 `page={has_more:false,next_cursor:null}`（当前实现**不提供** cursor 翻页）。设计验证项 `VRC-MGMT-006`；机制 `T-MET-PAGE`；需求/机制链 `LT-FUN-006`、`R-OBS-01`、`CT-ADMIN-001`、`CT-LOG-001`。**不证明什么**：不证明 cursor 跨页去重/重放（审计当前无 cursor；`/v1/usage` 的 cursor 语义见 DP-USAGE-03/07）、不证明非法 `limit` 400（ADM-AUDIT-03）、不证明字段脱敏（ADM-AUDIT-01）、不证明稳定排序的全部语义（本 case 只断 `limit=1` 边界）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态：审计表非空；只读。
- **输入与构造**：
  ```http
  GET /v1/audit?limit=1 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`limit=1`（下界边界，`minimum:1`）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/audit?limit=1")`。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `len(data) <= 1`；`page` 键集恰 `{has_more,next_cursor}`；`isinstance(page["has_more"], bool)`。
  5. 断言一致性：`page["has_more"] is True ⇒ page["next_cursor"]` 为非空字符串；`page["has_more"] is False ⇒ page["next_cursor"] is None`。
  6. （可选对照）`GET /v1/audit`（默认 50）的 `data` 长度 ≥ `limit=1` 时的长度（不强制，避免空表误判）。
- **重点关注步骤**：① **边界 `limit=1`**——返回条数必须 ≤1（不是必须 ==1；空表时 0 亦合法）；② **`has_more`/`next_cursor` 一致**——本实现恒 `has_more=false`、`next_cursor=null`，因此断言其一致即可，**不得**因 `has_more=false` 误判"分页失效"（审计当前无 cursor 分页是已知契约）；③ **布尔类型**——`has_more` 必须 JSON bool，不能是 0/1；④ **不得当 cursor 端点**——审计不接受 `cursor` query（无 cursor 语义），不得构造 cursor 断言；⑤ **纯读**——不写审计。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `AdminPageMeta`/`AuditPage` + `limit` 边界规则。
  - HTTP：`200`；body `{"data":[...≤1...],"page":{"has_more":false,"next_cursor":null}}`。
  - `has_more` 为 bool 且与 `next_cursor` 一致。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `len(data)≤1` + `page` 键集正确 + `has_more` 为 bool 且与 `next_cursor` 一致。
  - **FAIL**：status 非 200、`len(data)>1`、`page` 形状错、`has_more` 非 bool、或一致性违反。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL（含 `limit=1`）、原始 HTTP status/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`AdminPageMeta`/`AuditPage` 机器契约；`AuditLog.page`；机制 `T-MET-PAGE`。自动化入口 [`at_adm_audit_02.py`](../../../../tests/system/api_test_v03/at_adm_audit_02.py)。**不依赖**其它 Case；与 ADM-AUDIT-01/03 互补。
