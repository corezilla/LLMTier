# ADM-PROV-11 — kind 枚举校验

- **Case ID**：`ADM-PROV-11`（与 §3.2 权威清单一致；本文件名 `adm-prov-11.md`，唯一对应）。
- **标题**：`POST /v1/providers` 提交非法 `kind`：HTTP 400 + `error.code=="invalid_request"`（`param=="kind"`），不创建资源。
- **目的（被测契约）**：验证 Management Provider CRUD 的**枚举校验（写前置校验）契约**。被测端点/规则：`POST /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createProvider`，`ProviderWrite.kind` enum `{cloud,local}`）；[`registry.create_provider`](../../../../src/management/registry.py) `require(body["kind"] in {"cloud","local"}, 400, "invalid_request", "Invalid provider kind", "kind")`；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（400 `invalid_request`、`param=="kind"`）。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功创建（ADM-PROV-02）、不证明 `secret_ref` 格式（ADM-PROV-12）、不证明 `name`/`enabled`/`usage` 校验；本 case 只锁定单一非法 `kind`。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足 §2.1 **附加（B 类）**（实例 `/healthz` 200；`_BASELINE_SETTINGS` 1 provider `prov_b` + 1 deployment `depl_b` + 7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`Bearer dev-admin`）。**TS-003**：请求中的 `endpoint` 仍用 LAN 常量（即便本 case 期望被拒，也不得写 `127.0.0.1`）。
- **输入与构造**：固定请求（`kind` 取枚举外值）：
  ```http
  POST /v1/providers HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Test Provider <uuid8>",
    "kind": "invalid_kind",
    "endpoint": "http://192.168.1.9:9000/v1",
    "secret_ref": null,
    "enabled": true
  }
  ```
  构造点：`kind="invalid_kind"`（不在 `{cloud,local}`）；其余字段均合法，确保 400 由 `kind` 触发而非别的字段；`name` 唯一。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. 记 `before = {p["id"] for p in admin_client_b.get("/v1/providers").json()["data"]}`（可选基线）。
  3. `resp = admin_client_b.post("/v1/providers", json=body_illegal_kind)`；断言 `status_code == 400`。
  4. `err = resp.json()["error"]`：`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["retryable"] is False`；若断言严格，`err["param"] == "kind"`。
  5. 交叉核对：`GET /v1/providers` 列表与步骤 2 记的集合一致（**拒绝零副作用**，无新 provider）。
- **重点关注步骤**：① **400 而非 201**——非法枚举必须在写库前被拒；② **`param=="kind"`**——定位到出错字段（实现显式设置 `param="kind"`），便于调用方修复；③ **信封 identity**——恰 5 键、`type=="request_error"`（400<500）、`retryable=false`、`param` 为字符串；④ **零副作用**——第 5 步确认无新 provider、无 audit 成功记录、无 usage profile 孤儿行；⑤ **与 `resource_conflict` 区分**——本 case 是 400 校验错，不是重名 409；⑥ **不依赖 message 文案**。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderWrite.kind` enum + `ErrorEnvelope`/`ErrorDetail` + `ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"code":"invalid_request","type":"request_error","param":"kind","retryable":false,"message":"<nonempty>"}}`。
  - 无资源变化：provider 列表与请求前一致。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="invalid_request"`（且 `param=="kind"`）、`type=="request_error"`、`retryable is False`，列表无新增。
  - **FAIL**：status 非 400（如 201 误建）、`code` 不符、缺/多键、`type` 错，或出现资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以替代路径/伪造 400 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求与 400 原始响应（脱敏后）、请求前后 provider 列表、发出命令、exit code、`elapsed`；`manifest.json` 必含 `environment:"b"`、`inputs`、`oracle`、`actual`、`verdict`、`evidence_files`、`redactions`、`reproduction_cmd`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——写入被拒，无创建物；不改 `prov_b`/`depl_b`、不写注入。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ProviderWrite`/`ErrorEnvelope` 机器契约；`registry.create_provider` 枚举校验；错误目录 `ERR-REQ-VALIDATION`；自动化入口 [`at_adm_prov_11.py`](../../../../tests/system/api_test_v03/at_adm_prov_11.py)。**不依赖**其它 Case；与 ADM-PROV-12 同属写校验负向但各自独立。
