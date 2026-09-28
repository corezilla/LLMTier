# ADM-SL-05 — 删除 fixed tier

- **Case ID**：`ADM-SL-05`（与 §3.2 权威清单一致；本文件名 `adm-sl-05.md`，唯一对应）。
- **标题**：`DELETE /v1/service-levels/{id}` 删除固定 Tier：HTTP 409 `fixed_service_level`（"cannot be deleted"）。
- **目的（被测契约）**：验证固定 Tier 的**不可删除契约**。被测端点/规则：`DELETE /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteServiceLevel`，header `If-Match`）；[`registry.delete_service_level`](../../../../src/management/registry.py) **无条件** `raise ApiError(409, "fixed_service_level", "Fixed Tier service levels cannot be deleted")`（不存在可删除分支）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-FIXED-LEVEL` → wire `code=fixed_service_level`；机制 `T-CFG-DELREF` 的固定 Tier 特例；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明 `If-Match` 的 412（本实现对该路由先返回 409、不校验 ETag）、不证明其它资源删除（provider/deployment 引用 409 见 ADM-PROV-10）、不证明 PATCH/创建（ADM-SL-04/02/02b）。本 case **只**锁 409 `fixed_service_level`。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（`/healthz` 200；`_baseline_settings` = `prov_b`+`depl_b`+7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`。本 case 选 `Engineer`。
- **输入与构造**：
  ```http
  DELETE /v1/service-levels/Engineer HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  ```
  构造点：先 `GET` 取真实 `ETag`（实现不校验，但按 openapi 契约提供，使失败点确为固定 Tier 规则）；不传 body；不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Engineer")`；断言 200；记 `etag = get.headers["ETag"]`、`version_before = body["version"]`。
  3. `resp = admin_client_b.delete("/v1/service-levels/Engineer", headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 409`；`err = resp.json()["error"]`：断言 `err["code"]=="fixed_service_level"`、`"cannot be deleted" in err["message"]`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels/Engineer` 仍 200，`version` 不变；`GET /v1/service-levels` 仍含全部 7 tier。
- **重点关注步骤**：① **不可删除而非未找到**——必须是 409 `fixed_service_level`，不是 404/400/412；② **零副作用**——`Engineer` 行与其 `service_level_deployments` 必须保留（409 抛在 `txn` 内、回滚）；③ **ETag 不参与判定**——本实现删除前不校验 `If-Match`（`delete_service_level` 直接抛 409），因此传任意/缺省 `If-Match` 也应 409；不得因"实现忽略了 ETag"而判 FAIL（这属实现注记，见下）；④ **错误信封 identity**——恰 5 键、`type=request_error`；⑤ **审计**——失败经 `mutate` 记 `action="service_level.delete"`、`result="failed"`。
  > **实现注记**：`delete_service_level` 对所有 `service-levels/{id}` 删除都返回 409 `fixed_service_level`（当前系统只存在固定 Tier，无自定义 Tier 删除路径）。OpenAPI 声明 DELETE 需 `If-Match`/可 412，但实现不校验 ETag —— 与本 case 的 409 断言一致；若未来引入可变 Tier，本 case 需按新契约复核。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 固定 Tier 不可删除规则（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）。
  - HTTP：`409`；body `{"error":{"message":"Fixed Tier service levels cannot be deleted","type":"request_error","code":"fixed_service_level","param":null,"retryable":false}}`。
  - 资源：`Engineer` 仍存在，`version` 不变，7 tier 齐全。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`409` + `code=="fixed_service_level"` + `type=="request_error"`，且 `Engineer` 未被删除。
  - **FAIL**：status 非 409（含 204 删除成功）、`code` 错、或 `Engineer` 被删。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实固定 Tier 规则——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 GET/DELETE 请求与原始 409 响应（脱敏后）、DELETE 后 `GET` 的 `version`、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——删除被拒未改库。退出前确认 7 tier 齐全、`Engineer.version` 未变、无注入残留。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`registry.delete_service_level`；错误目录 `ERR-FIXED-LEVEL`。自动化入口 [`at_adm_sl_05.py`](../../../../tests/system/api_test_v03/at_adm_sl_05.py)。**不依赖**其它 Case；与 ADM-SL-06/07 同走 PATCH 冲突语义但独立执行。
