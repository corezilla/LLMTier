# ADM-PROV-11 — kind 枚举校验

- **Case ID**：`ADM-PROV-11`（与 §3.2 权威清单一致；本文件名 `adm-prov-11.md`，唯一对应）。
- **标题**：`POST /v1/providers` 提交非法 `kind`：HTTP 400 + `error.code=="invalid_request"`（`param=="kind"`），不创建资源。
- **目的（被测契约）**：验证 Management Provider CRUD 的**枚举校验（写前置校验）契约**。被测端点/规则：`POST /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createProvider`，`ProviderWrite.kind` enum `{cloud,local}`）；[`registry.create_provider`](../../../../src/management/registry.py) `require(body["kind"] in {"cloud","local"}, 400, "invalid_request", "Invalid provider kind", "kind")`；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（400 `invalid_request`、`param=="kind"`）。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[测试设计 §11.1](../llmtier-api-test-specification.md)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功创建（ADM-PROV-02）、不证明 `secret_ref` 格式（ADM-PROV-12）、不证明 `name`/`enabled`/`usage` 校验；本 case 只锁定单一非法 `kind`。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。**TS-003**：请求中的 `endpoint` 仍用 LAN 常量，即便本 case 期望被拒，也不得写 `127.0.0.1`。
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
  5. 交叉核对：`GET /v1/providers` 列表与步骤 2 记的集合一致（**对 provider 资源拒绝零副作用**，无新 provider）。**注**：第 2/5 步列表 GET 各自会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（`admin.page()`，即使无 `cursor`），属服务端读路径副作用、非用户资源，报告须登记，**不得笼统声称"零写入"**。
- **重点关注步骤**：① **400 而非 201**——非法枚举必须在写库前被拒；② **`param=="kind"`**——定位到出错字段（实现显式设置 `param="kind"`），便于调用方修复；③ **信封 identity**——恰 5 键、`type=="request_error"`（400<500）、`retryable=false`、`param` 为字符串；④ **对 provider 资源零副作用**——第 5 步确认无新 provider、无 audit 成功记录、无 usage profile 孤儿行；但第 2/5 步列表 GET 会在 `query_snapshots` 落 10 分钟 TTL 分页快照（`admin.page()`），须登记该写入、**不得声称"零写入"**；⑤ **与 `resource_conflict` 区分**——本 case 是 400 校验错，不是重名 409；⑥ **不依赖 message 文案**。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderWrite.kind` enum + `ErrorEnvelope`/`ErrorDetail` + `ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
   - body：`{"error":{"code":"invalid_request","type":"request_error","param":"kind","retryable":false,"message":"<nonempty>"}}`。
   - 无 provider 资源变化：provider 集合与请求前一致（第 2/5 步列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="invalid_request"`（且 `param=="kind"`）、`type=="request_error"`、`retryable is False`，provider 集合无新增（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 400（如 201 误建）、`code` 不符、缺/多键、`type` 错，或出现 provider 资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以替代路径/伪造 400 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：请求与 400 原始响应、请求前后 provider 列表。
- **清理与复位**：**无需 teardown**——写入被拒，无创建物；不改 `prov_b`/`depl_b`、不写注入。第 2/5 步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）随 B 类整班 `rm -rf` 消失。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ProviderWrite`/`ErrorEnvelope` 机器契约；`registry.create_provider` 枚举校验；错误目录 `ERR-REQ-VALIDATION`；自动化入口 [`at_adm_prov_11.py`](../../../../tests/system/api_test_v03/at_adm_prov_11.py)。**不依赖**其它 Case；与 ADM-PROV-12 同属写校验负向但各自独立。
