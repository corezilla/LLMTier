# ADM-PROV-12 — secret_ref 格式

- **Case ID**：`ADM-PROV-12`（与 §3.2 权威清单一致；本文件名 `adm-prov-12.md`，唯一对应）。
- **标题**：`POST /v1/providers` 提交非法格式 `secret_ref`：HTTP 400 + `error.code=="invalid_request"` + `error.param=="secret_ref"`，不创建资源。
- **目的（被测契约）**：验证 Management Provider CRUD 的**凭据引用格式校验契约**。被测端点/规则：`POST /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createProvider`，`ProviderWrite.secret_ref` 为 write-only 引用）；[`registry._validate_secret_ref`](../../../../src/management/registry.py) `require(ref is None or (isinstance(ref,str) and ref.startswith(("env:","file:"))), 400, "invalid_request", "Unsupported provider secret reference", "secret_ref")`；失败走统一错误信封（400 `invalid_request`、`param=="secret_ref"`）。设计验证项 `VRC-MGMT-001`；机制 `T-CFG-SECRET` / `T-CFG-BADREF`；需求/机制链 `LT-FUN-005`、`LT-SEC-001`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明合法 `env:`/`file:` 引用被接受（ADM-PROV-02 用 `null`）、不证明 `secret_ref` 值不被回显（ADM-PROV-14）、不证明 `kind` 枚举（ADM-PROV-11）、不证明 `usage.*_key_ref` 校验（`registry._usage_values`，未单列 case）；本 case 只锁定单一非法格式。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足 §2.1 **附加（B 类）**（实例 `/healthz` 200；`_baseline_settings` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`Bearer dev-admin`）。**TS-003**：请求中的 `endpoint` 用 LAN 常量，**禁止 `127.0.0.1`**。
- **输入与构造**：固定请求（`secret_ref` 非 `env:`/`file:` 前缀）：
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
    "secret_ref": "not-a-ref-format",
    "enabled": true
  }
  ```
  构造点：`secret_ref="not-a-ref-format"`（既非 `env:` 也非 `file:`，且非 `null`）；其余字段合法，确保 400 由 `secret_ref` 触发；`name` 唯一。不注入故障。**不在证据中写入任何真实 key 值**（本 case 用无效字面量，天然无秘密）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. 记 `before = {p["id"] for p in admin_client_b.get("/v1/providers").json()["data"]}`（可选）。
  3. `resp = admin_client_b.post("/v1/providers", json=body_illegal_ref)`；断言 `status_code == 400`。
  4. `err = resp.json()["error"]`：`err["code"] == "invalid_request"`、`err["param"] == "secret_ref"`、`err["type"] == "request_error"`、`err["retryable"] is False`。
  5. 交叉核对：`GET /v1/providers` 列表与步骤 2 一致（**对 provider 资源拒绝零副作用**）。**注**：第 2/5 步列表 GET 各自会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（`admin.page()`，即使无 `cursor`），属服务端读路径副作用、非用户资源，报告须登记，**不得笼统声称"零写入"**。
- **重点关注步骤**：① **400 + `param=="secret_ref"`**——必须同时定位到 `secret_ref`（实现显式 `param`），不能只给笼统 400；② **前缀白名单**——只有 `env:`/`file:`（或 `null`）合法；`not-a-ref-format` 必须在写库前被拒；③ **信封 identity**——恰 5 键、`type=="request_error"`、`retryable=false`；④ **对 provider 资源零副作用**——无新 provider、无 usage profile 孤儿行、无 audit 成功；但第 2/5 步列表 GET 会在 `query_snapshots` 落 10 分钟 TTL 分页快照（`admin.page()`），须登记该写入、**不得声称"零写入"**；⑤ **秘密卫生**——证据/日志中不得出现任何真实 secret 值；本 case 使用无效字面量，无需脱敏但 `redactions` 仍须列 `Authorization`；⑥ **不依赖 message 文案**。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderWrite.secret_ref` 描述 + `ErrorEnvelope`/`ErrorDetail` + `registry._validate_secret_ref` 白名单。
  - HTTP：`400`；`Content-Type: application/json`。
   - body：`{"error":{"code":"invalid_request","type":"request_error","param":"secret_ref","retryable":false,"message":"<nonempty>"}}`。
   - 无 provider 资源变化（第 2/5 步列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="invalid_request"` 且 `error.param=="secret_ref"`、`type=="request_error"`、`retryable is False`，provider 集合无新增（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 400（如 201 误建）、`code` 或 `param` 不符、缺/多键，或出现 provider 资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以替代路径/伪造 400 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求与 400 原始响应（脱敏后）、请求前后 provider 列表、发出命令、exit code、`elapsed`；`manifest.json` 必含 `environment:"b"`、`inputs`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`（`Authorization`）、`reproduction_cmd`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——写入被拒，无创建物；不改 `prov_b`/`depl_b`、不写注入。第 2/5 步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ProviderWrite`/`ErrorEnvelope` 机器契约；`registry._validate_secret_ref`；机制 `T-CFG-SECRET`/`T-CFG-BADREF`；自动化入口 [`at_adm_prov_12.py`](../../../../tests/system/api_test_v03/at_adm_prov_12.py)。**不依赖**其它 Case；与 ADM-PROV-11 同属写校验负向但各自独立。
