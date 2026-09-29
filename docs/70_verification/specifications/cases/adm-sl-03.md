# ADM-SL-03 — 获取 service-level

- **Case ID**：`ADM-SL-03`（与 §3.2 权威清单一致；本文件名 `adm-sl-03.md`，唯一对应）。
- **标题**：`GET /v1/service-levels/{id}` 精确返回单个固定 Tier：HTTP 200 + `ServiceLevelView` + `ETag`。
- **目的（被测契约）**：验证 Service Level **单条详情读契约**。被测端点/规则：`GET /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getServiceLevel`，路径参数 `service_level_id`，`security=AdminBearerAuth`），成功 `200` + `ServiceLevelView`（`{id,deployment_ids,enabled,capabilities,version}`，`additionalProperties:false`）+ 响应头 `ETag: "<id>.v<N>"`（[`registry.get_service_level`](../../../../src/management/registry.py) 返回 `_etag`）。设计验证项 `VRC-MGMT-002`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明列表（ADM-SL-01）、不证明更新/删除（ADM-SL-04/04b/05/06/07/08）、不证明不存在 id 的 404（未单独构 case；由 `registry.get_service_level` 的 `not_found` 语义承载）、不证明 If-Match/CAS（ADM-SL-04）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线（7 fixed tier）。本 case 选 `Worker`（responses-capable 固定 Tier，A 类必在）。
- **输入与构造**：固定请求：
  ```http
  GET /v1/service-levels/Worker HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{id}="Worker"` 精确大小写匹配 `FIXED_TIERS`（大小写敏感）；无 body、无 query；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/service-levels/Worker")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言键集**恰为** `{id,deployment_ids,enabled,capabilities,version}`（`additionalProperties:false`）；`id=="Worker"`、`deployment_ids` 为数组、`enabled` 为 bool、`version` 为 int ≥1、`capabilities` 为 12 键 `ModelCapabilities`。
  5. 断言响应头含 `ETag`，且匹配强 ETag 形态 `^"[A-Za-z0-9._:-]+"$`（期望 `"Worker.v<N>"`，`N==body.version`）。
- **重点关注步骤**：① **精确 id 匹配**——`Worker` 区分大小写；`worker`/`WORKER` 应 404（未在本 case 构造，但不得把大小写不匹配当 PASS）；② **字段集精确**——`ServiceLevelView.additionalProperties:false`，多/少键即 FAIL；③ **ETag identity**——ETag 必为 `"<id>.v<version>"` 且与 body `version` 一致（含双引号），是把详情读与后续 CAS 绑定的关键；④ **capabilities 12 键**——必须为完整 `ModelCapabilities`，不是子集；⑤ **读无副作用**——`GET` 不写 `query_snapshots`（非分页 `page`）、不改 version。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelView` + ETag 规则。
  - HTTP：`200`；响应头 `ETag == "Worker.v<N>"`（`N` 与 body `version` 同）。
  - body：`{"id":"Worker","deployment_ids":[...],"enabled":<bool>,"capabilities":{…12…},"version":N}`。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `ServiceLevelView` 键集/类型正确 + `id=="Worker"` + `ETag=="Worker.v<N>"` 且与 `version` 一致。
  - **FAIL**：status 非 200、键集不符、`id` 错、ETag 缺失/格式错/与 version 不一致。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 HTTP status/headers（含 `ETag`）/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——只读 `GET`，不改 `service_levels`/`service_level_deployments`、不写注入。退出前确认 `/readyz` 仍 7 tier、`GET /v1/service-levels/Worker` 的 `version` 未变。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ServiceLevelView` 机器契约；`registry.get_service_level`/`_etag`。自动化入口 [`at_adm_sl_03.py`](../../../../tests/system/api_test_v03/at_adm_sl_03.py)。**不依赖**其它 Case；其 ETag 语义被 ADM-SL-04/04b/05 复用但各自独立执行。
